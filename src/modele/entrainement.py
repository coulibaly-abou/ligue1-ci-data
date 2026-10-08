"""Entraînement et comparaison des modèles de prédiction (D / N / E).

    python -m src.modele.entrainement        # ou : make train

Protocole (aucun découpage aléatoire) :
- 2016-2017 sert seulement à « chauffer » l'Elo et la forme (pas d'apprentissage dessus) ;
- entraînement 2017-2018 → 2023-2024, validation 2024-2025 (choix des hyperparamètres) ;
- test final sur la dernière saison complète, 2025-2026, jamais vue avant ;
- validation glissante : chaque saison 2021 → 2025 prédite avec les saisons précédentes.
Le modèle retenu est le plus simple parmi ceux dont la log-loss moyenne sur les saisons
glissantes 2021 → 2024 est à moins de 0,002 de la meilleure (jamais sur le test : une
seule saison de 240 matchs est trop bruitée pour choisir), puis il est ré-entraîné sur toutes les saisons jouées pour prédire 2026-2027.
"""
import json
import time

import joblib
import numpy as np
import pandas as pd

from config.settings import RACINE
from src.modele import baselines
from src.modele.evaluation import (
    calibration,
    importance_permutation,
    matrice_confusion,
    metriques,
)
from src.modele.features import (
    CLASSES,
    ParamsElo,
    charger_matchs,
    cible,
    construire_jeu,
    matrice,
)
from src.modele.reseau import ClassifieurMLP
from src.utils.logs import get_logger

log = get_logger("modele")

SAISON_CHAUFFE, SAISON_VALIDATION, SAISON_TEST = 2016, 2024, 2025
SAISONS_GLISSANTES = [2021, 2022, 2023, 2024, 2025]
COMPLEXITE = ["elo", "logreg", "foret", "boosting", "mlp"]  # du plus simple au plus complexe
TOLERANCE = 0.002  # écart de log-loss jugé négligeable
DOSSIER_MODELES = RACINE / "models"
DOSSIER_RESULTATS = RACINE / "docs" / "resultats"
NOMS = {"naif": "Référence naïve", "elo": "Elo", "logreg": "Régression logistique",
        "foret": "Forêt aléatoire", "boosting": "Gradient boosting", "mlp": "Réseau de neurones"}


# ------------------------------------------------------------------ réglages
def regler_elo(matchs: pd.DataFrame) -> ParamsElo:
    """K et avantage du terrain choisis sur la saison de validation."""
    meilleur = (np.inf, None)
    for k in (10, 15, 20, 30):
        for avantage in (40, 70, 100, 130, 160):
            params = ParamsElo(k=k, avantage_terrain=avantage)
            df, _ = construire_jeu(matchs, params)
            a, v = _decoupe(df, SAISON_VALIDATION)
            proba = baselines.ModeleElo().fit(matrice(a), cible(a)).predict_proba(matrice(v))
            perte = metriques(cible(v), proba)["log_loss"]
            meilleur = min(meilleur, (perte, params), key=lambda t: t[0])
    log.info("Elo retenu : K=%s, avantage terrain=%s (log-loss validation %.4f)",
             meilleur[1].k, meilleur[1].avantage_terrain, meilleur[0])
    return meilleur[1]


def _decoupe(df: pd.DataFrame, saison_test: int):
    """Entraînement = saisons strictement antérieures (hors saison de chauffe)."""
    a = df[(df["id_saison"] > SAISON_CHAUFFE) & (df["id_saison"] < saison_test)]
    return a, df[df["id_saison"] == saison_test]


def _score_validation(fabrique, df) -> float:
    a, v = _decoupe(df, SAISON_VALIDATION)
    proba = fabrique().fit(matrice(a), cible(a)).predict_proba(matrice(v))
    return metriques(cible(v), proba)["log_loss"]


def regler_hyperparametres(df: pd.DataFrame) -> dict:
    """Une fabrique (fonction sans argument -> modèle neuf) par modèle, réglée sur la validation."""
    C = min((0.003, 0.01, 0.03, 0.1, 0.3, 1.0),
            key=lambda c: _score_validation(lambda: baselines.regression_logistique(c), df))
    log.info("Régression logistique : C=%s", C)

    grille = [{"couches": c, "dropout": d, "weight_decay": w}
              for c in ((16,), (32, 16), (64, 32))
              for d in (0.2, 0.4) for w in (1e-3, 1e-2)]
    scores = [(_score_validation(lambda g=g: ClassifieurMLP(**g), df), g) for g in grille]
    perte, mlp = min(scores, key=lambda t: t[0])
    log.info("MLP : %s (log-loss validation %.4f)", mlp, perte)

    return {"naif": baselines.ModeleNaif, "elo": baselines.ModeleElo,
            "logreg": lambda: baselines.regression_logistique(C),
            "foret": baselines.foret_aleatoire, "boosting": baselines.gradient_boosting,
            "mlp": lambda: ClassifieurMLP(**mlp)}, {"logreg_C": C, "mlp": mlp}


# ---------------------------------------------------------------- évaluation
def bootstrap_ecart(y, proba_a, proba_b, n=2000, seed=0) -> dict:
    """IC à 95 % de l'écart de log-loss (b - a) par rééchantillonnage des matchs."""
    rng = np.random.default_rng(seed)
    pa = -np.log(np.clip(proba_a[np.arange(len(y)), y], 1e-15, 1))
    pb = -np.log(np.clip(proba_b[np.arange(len(y)), y], 1e-15, 1))
    ecarts = [np.mean((pb - pa)[i]) for i in rng.integers(0, len(y), (n, len(y)))]
    return {"ecart_moyen": float(np.mean(pb - pa)),
            "ic95": [float(np.percentile(ecarts, 2.5)), float(np.percentile(ecarts, 97.5))],
            "part_ecarts_negatifs": float(np.mean(np.array(ecarts) < 0))}


def validation_glissante(df, fabriques) -> tuple[pd.DataFrame, np.ndarray, dict]:
    """Métriques par saison + probabilités de tous les matchs prédits (pour le bootstrap)."""
    lignes, y_tout, probas = [], [], {nom: [] for nom in fabriques}
    for saison in SAISONS_GLISSANTES:
        a, t = _decoupe(df, saison)
        y_tout.append(cible(t))
        for nom, fabrique in fabriques.items():
            proba = fabrique().fit(matrice(a), cible(a)).predict_proba(matrice(t))
            probas[nom].append(proba)
            lignes.append({"saison_test": saison, "modele": nom, **metriques(cible(t), proba)})
        log.info("Validation glissante %s terminée", saison)
    return (pd.DataFrame(lignes), np.concatenate(y_tout),
            {nom: np.vstack(p) for nom, p in probas.items()})


# ------------------------------------------------------------- prédictions
def predire_a_venir(modele, cf, matchs: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Probabilités des matchs à jouer + matrice de tous les duels de la saison en cours."""
    saison = int(matchs["id_saison"].max())
    a_jouer = matchs[(matchs["statut"] == "a_jouer") & (matchs["id_saison"] == saison)]
    clubs = sorted(set(matchs.loc[matchs["id_saison"] == saison, "dom"]))

    def probas(paires):
        X = matrice(pd.DataFrame([cf.features(d, e, saison=saison) for d, e in paires]))
        return modele.predict_proba(X)

    prochains = a_jouer[["id_match", "date_match", "dom", "ext"]].copy()
    if len(prochains):
        p = probas(list(zip(prochains["dom"], prochains["ext"])))
        prochains[["p_dom", "p_nul", "p_ext"]] = p
    paires = [(d, e) for d in clubs for e in clubs if d != e]
    duels = pd.DataFrame(paires, columns=["dom", "ext"])
    duels[["p_dom", "p_nul", "p_ext"]] = probas(paires)
    return prochains, duels


# --------------------------------------------------------------------- main
def main() -> None:
    debut = time.monotonic()
    DOSSIER_MODELES.mkdir(exist_ok=True)
    DOSSIER_RESULTATS.mkdir(parents=True, exist_ok=True)

    matchs = charger_matchs()
    params_elo = regler_elo(matchs)
    df, _ = construire_jeu(matchs, params_elo)
    fabriques, hyper = regler_hyperparametres(df)

    # Validation glissante : choix du modèle retenu (saisons antérieures au test)
    glissante, y_glis, probas_glis = validation_glissante(df, fabriques)
    avant_test = glissante[glissante["saison_test"] < SAISON_TEST]
    score_val = avant_test.groupby("modele")["log_loss"].mean().to_dict()
    # Règle du plus simple : parmi les modèles à moins de TOLERANCE du meilleur
    # (écart bien inférieur à l'incertitude d'une saison), on garde le moins complexe.
    meilleur_score = min(v for n, v in score_val.items() if n != "naif")
    retenu = next(n for n in COMPLEXITE if score_val[n] <= meilleur_score + TOLERANCE)
    log.info("Validation glissante 2021-2024 (log-loss) : %s -> modèle retenu : %s",
             score_val, retenu)

    # Test final sur la dernière saison complète
    a, t = _decoupe(df, SAISON_TEST)
    Xa, ya, Xt, yt = matrice(a), cible(a), matrice(t), cible(t)
    modeles, probas_test, resultats = {}, {}, []
    for nom, fabrique in fabriques.items():
        modeles[nom] = fabrique().fit(Xa, ya)
        probas_test[nom] = modeles[nom].predict_proba(Xt)
        resultats.append({"modele": nom, "libelle": NOMS[nom],
                          "log_loss_validation_glissante": score_val[nom],
                          **metriques(yt, probas_test[nom])})
        log.info("Test %-12s %s", nom, resultats[-1])
    resultats = pd.DataFrame(resultats).sort_values("log_loss")

    # Importance des variables : modèles multivariés (Elo n'utilise qu'une variable)
    importance = pd.concat([importance_permutation(modeles[n], Xt, yt, 30).assign(modele=n)
                            for n in ("logreg", "foret", "mlp")])
    coefficients = pd.DataFrame(modeles["logreg"][-1].coef_.T, index=Xt.columns,
                                columns=[f"coef_{c}" for c in CLASSES])
    # Écart de log-loss vs naïf : sur le test, puis sur tous les matchs de la validation
    # glissante (≈ 1 100 matchs : intervalle beaucoup plus étroit)
    comparaisons = {nom: {"test": bootstrap_ecart(yt, probas_test["naif"], probas_test[nom]),
                          "glissante": bootstrap_ecart(y_glis, probas_glis["naif"],
                                                       probas_glis[nom])}
                    for nom in fabriques if nom != "naif"}

    # Sauvegardes : résultats
    resultats.to_csv(DOSSIER_RESULTATS / "comparaison_modeles.csv", index=False)
    glissante.to_csv(DOSSIER_RESULTATS / "validation_glissante.csv", index=False)
    importance.to_csv(DOSSIER_RESULTATS / "importance_variables.csv", index=False)
    coefficients.to_csv(DOSSIER_RESULTATS / "coefficients_logreg.csv", index_label="variable")
    # Calibration sur les ≈ 1 100 matchs de la validation glissante (plus stable qu'une saison)
    calib = pd.concat([calibration(y_glis, probas_glis[n]).assign(modele=n)
                       for n in fabriques])
    calib.to_csv(DOSSIER_RESULTATS / "calibration.csv", index=False)
    confusions = {n: matrice_confusion(yt, p).to_dict() for n, p in probas_test.items()}
    pred_test = t[["id_match", "date_match", "dom", "ext", "buts_dom", "buts_ext",
                   "resultat"]].copy()
    for nom, p in probas_test.items():
        pred_test[[f"{nom}_p_{c}" for c in CLASSES]] = p
    pred_test.to_csv(DOSSIER_RESULTATS / "predictions_test.csv", index=False)
    if hasattr(modeles["mlp"], "courbes_"):
        pd.DataFrame(modeles["mlp"].courbes_[0], columns=["perte_entrainement",
                                                         "perte_validation"]) \
            .to_csv(DOSSIER_RESULTATS / "courbe_apprentissage_mlp.csv", index_label="epoque")

    # Modèle final : toutes les saisons jouées, pour les matchs à venir
    finale = df[df["id_saison"] > SAISON_CHAUFFE]
    modele_final = fabriques[retenu]().fit(matrice(finale), cible(finale))
    _, cf = construire_jeu(matchs, params_elo)
    prochains, duels = predire_a_venir(modele_final, cf, matchs)
    prochains.to_csv(DOSSIER_RESULTATS / "predictions_a_venir.csv", index=False)
    duels.to_csv(DOSSIER_RESULTATS / "predictions_duels.csv", index=False)
    elo_actuel = pd.Series(cf.notes, name="elo").sort_values(ascending=False)
    elo_actuel.to_csv(DOSSIER_RESULTATS / "elo_actuel.csv", index_label="club")
    df.to_csv(DOSSIER_RESULTATS / "jeu_features.csv", index=False)
    joblib.dump({"modele": modele_final, "nom": retenu, "params_elo": params_elo,
                 "variables": list(matrice(finale).columns)},
                DOSSIER_MODELES / "modele_final.joblib")

    repartition = t["resultat"].value_counts(normalize=True).reindex(CLASSES).round(4)
    synthese = {
        "date": pd.Timestamp.now().isoformat(timespec="seconds"),
        "protocole": {"chauffe": SAISON_CHAUFFE, "validation": SAISON_VALIDATION,
                      "test": SAISON_TEST, "saisons_glissantes": SAISONS_GLISSANTES,
                      "n_glissante": len(y_glis), "n_entrainement": len(a),
                      "n_test": len(t), "n_variables": int(Xt.shape[1])},
        "params_elo": {"k": params_elo.k, "avantage_terrain": params_elo.avantage_terrain},
        "hyperparametres": hyper,
        "modele_retenu": retenu,
        "regle_selection": {"tolerance": TOLERANCE, "complexite": COMPLEXITE,
                            "log_loss_2021_2024": score_val},
        "repartition_test": repartition.to_dict(),
        "resultats_test": resultats.to_dict(orient="records"),
        "bootstrap_vs_naif": comparaisons,
        "confusions": confusions,
        "validation_glissante_moyenne": glissante.groupby("modele")[
            ["accuracy", "log_loss", "rps"]].mean().to_dict(orient="index"),
    }
    (DOSSIER_RESULTATS / "metriques.json").write_text(
        json.dumps(synthese, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    log.info("Entraînement terminé en %.0f s — modèle retenu : %s", time.monotonic() - debut,
             retenu)


if __name__ == "__main__":
    main()

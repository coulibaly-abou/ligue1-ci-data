"""Tests du module de modélisation : absence de fuite, Elo, métriques, réseau."""
import numpy as np
import pandas as pd
import pytest

from src.modele.baselines import ModeleElo, ModeleNaif
from src.modele.evaluation import brier, metriques, rps
from src.modele.features import CLASSES, ParamsElo, cible, construire_jeu, matrice


def _matchs(scores, saison=2020):
    """Petit championnat fictif : liste de (dom, ext, buts_dom, buts_ext)."""
    lignes = []
    for i, (dom, ext, bd, be) in enumerate(scores):
        resultat = "D" if bd > be else "N" if bd == be else "E"
        lignes.append({"id_match": i, "id_saison": saison, "saison": f"{saison}-{saison + 1}",
                       "phase": "x", "date_match": pd.Timestamp("2020-09-01")
                       + pd.Timedelta(days=7 * i), "statut": "joue", "dom": dom, "ext": ext,
                       "buts_dom": bd, "buts_ext": be, "resultat": resultat})
    return pd.DataFrame(lignes)


def test_premier_match_sans_information():
    df, _ = construire_jeu(_matchs([("A", "B", 5, 0)]))
    ligne = df.iloc[0]
    assert ligne["elo_dom"] == ligne["elo_ext"] == 1500
    assert ligne["ppm_saison_dom"] == 1.35  # valeur neutre, pas le résultat du match


def test_pas_de_fuite_du_resultat():
    """Changer le score d'un match ne modifie pas ses propres variables."""
    base = [("A", "B", 1, 0), ("B", "C", 0, 0), ("C", "A", 2, 1)]
    autre = [("A", "B", 1, 0), ("B", "C", 0, 0), ("C", "A", 0, 4)]
    v1 = matrice(construire_jeu(_matchs(base))[0]).iloc[2]
    v2 = matrice(construire_jeu(_matchs(autre))[0]).iloc[2]
    pd.testing.assert_series_equal(v1, v2)


def test_elo_somme_nulle_et_vainqueur_monte():
    _, cf = construire_jeu(_matchs([("A", "B", 3, 0)]), ParamsElo(k=20))
    assert cf.notes["A"] > 1500 > cf.notes["B"]
    assert cf.notes["A"] + cf.notes["B"] == pytest.approx(3000)


def test_forme_mise_a_jour_apres_le_match():
    df, cf = construire_jeu(_matchs([("A", "B", 1, 0), ("A", "C", 0, 0)]))
    assert df.iloc[1]["forme5_dom"] == 3  # A a gagné son premier match
    assert cf.table["A"] == [4, 1, 2]     # 3 + 1 points, +1 de différence, 2 matchs


def test_metriques_prediction_parfaite():
    y = np.array([0, 1, 2])
    parfait = np.eye(3)
    assert rps(y, parfait) == 0
    assert brier(y, parfait) == 0
    assert metriques(y, parfait)["accuracy"] == 1


def test_rps_tient_compte_de_l_ordre():
    """Prédire « nul » pour une victoire domicile coûte moins que prédire « extérieur »."""
    y = np.array([0])
    assert rps(y, np.array([[0, 1, 0]])) < rps(y, np.array([[0, 0, 1]]))


def test_baselines():
    X = pd.DataFrame({"elo_diff": [-200, -100, 0, 100, 200] * 20})
    y = np.array([2, 2, 1, 0, 0] * 20)
    naif = ModeleNaif().fit(X, y)
    assert naif.predict_proba(X)[0] == pytest.approx([0.4, 0.2, 0.4])
    elo = ModeleElo().fit(X, y)
    p = elo.predict_proba(pd.DataFrame({"elo_diff": [300]}))[0]
    assert p.argmax() == 0 and p.sum() == pytest.approx(1)


def test_cible():
    df = pd.DataFrame({"resultat": ["E", "D", "N"]})
    assert list(cible(df)) == [2, 0, 1]
    assert CLASSES == ["D", "N", "E"]


def test_reseau_de_neurones_apprend():
    torch = pytest.importorskip("torch")  # noqa: F841
    from src.modele.reseau import ClassifieurMLP

    rng = np.random.default_rng(0)
    X = pd.DataFrame({"x": rng.normal(size=600), "bruit": rng.normal(size=600)})
    y = np.where(X["x"] > 0.5, 0, np.where(X["x"] < -0.5, 2, 1))
    mlp = ClassifieurMLP(couches=(8,), epoques=60, n_graines=1).fit(X, y)
    assert (mlp.predict(X) == y).mean() > 0.8
    assert mlp.predict_proba(X).sum(axis=1) == pytest.approx(np.ones(600))

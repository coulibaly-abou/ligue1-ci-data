"""Métriques : accuracy, log-loss, Brier, RPS, matrice de confusion, calibration.

Le RPS (ranked probability score) est la métrique de référence en football :
il tient compte de l'ordre D > N > E (prédire « nul » pour une victoire domicile
est moins grave que prédire « extérieur »).
"""
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, log_loss

from src.modele.features import CLASSES


def rps(y: np.ndarray, proba: np.ndarray) -> float:
    reel = np.eye(3)[y]
    ecart = np.cumsum(proba, axis=1) - np.cumsum(reel, axis=1)
    return float(np.mean(np.sum(ecart[:, :-1] ** 2, axis=1) / 2))


def brier(y: np.ndarray, proba: np.ndarray) -> float:
    return float(np.mean(np.sum((proba - np.eye(3)[y]) ** 2, axis=1)))


def metriques(y: np.ndarray, proba: np.ndarray) -> dict:
    return {"accuracy": float(accuracy_score(y, proba.argmax(axis=1))),
            "log_loss": float(log_loss(y, proba, labels=[0, 1, 2])),
            "brier": brier(y, proba),
            "rps": rps(y, proba)}


def matrice_confusion(y: np.ndarray, proba: np.ndarray) -> pd.DataFrame:
    m = confusion_matrix(y, proba.argmax(axis=1), labels=[0, 1, 2])
    return pd.DataFrame(m, index=[f"réel {c}" for c in CLASSES],
                        columns=[f"prédit {c}" for c in CLASSES])


def calibration(y: np.ndarray, proba: np.ndarray, n_bins: int = 5) -> pd.DataFrame:
    """Probabilité moyenne prédite vs fréquence observée, par classe et par tranche."""
    lignes = []
    for k, classe in enumerate(CLASSES):
        p, obs = proba[:, k], (y == k).astype(float)
        bornes = np.quantile(p, np.linspace(0, 1, n_bins + 1))
        tranche = np.clip(np.searchsorted(bornes, p, side="right") - 1, 0, n_bins - 1)
        for t in range(n_bins):
            masque = tranche == t
            if masque.sum():
                lignes.append({"classe": classe, "proba_moyenne": p[masque].mean(),
                               "frequence_observee": obs[masque].mean(),
                               "effectif": int(masque.sum())})
    return pd.DataFrame(lignes)


def importance_permutation(modele, X: pd.DataFrame, y: np.ndarray, n_repetitions: int = 20,
                           seed: int = 0) -> pd.DataFrame:
    """Hausse de la log-loss quand on mélange une variable (plus c'est haut, plus elle compte)."""
    rng = np.random.default_rng(seed)
    reference = log_loss(y, modele.predict_proba(X), labels=[0, 1, 2])
    lignes = []
    for col in X.columns:
        hausses = []
        for _ in range(n_repetitions):
            Xp = X.copy()
            Xp[col] = rng.permutation(Xp[col].to_numpy())
            hausses.append(log_loss(y, modele.predict_proba(Xp), labels=[0, 1, 2]) - reference)
        lignes.append({"variable": col, "hausse_log_loss": float(np.mean(hausses)),
                       "ecart_type": float(np.std(hausses))})
    return pd.DataFrame(lignes).sort_values("hausse_log_loss", ascending=False)

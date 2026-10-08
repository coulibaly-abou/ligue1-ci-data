"""Modèles de référence, tous avec l'interface scikit-learn (fit / predict_proba).

- naïf : prédit toujours « domicile », probabilités = fréquences de l'entraînement ;
- Elo : régression logistique sur le seul écart Elo (l'intercept porte l'avantage du terrain) ;
- régression logistique multinomiale sur toutes les variables ;
- forêt aléatoire et gradient boosting : modèles non linéaires classiques.
"""
import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


class ModeleNaif(BaseEstimator, ClassifierMixin):
    """Toujours « victoire domicile » ; probabilités constantes."""

    def fit(self, X, y):
        self.classes_ = np.arange(3)
        self.frequences_ = np.bincount(y, minlength=3) / len(y)
        return self

    def predict_proba(self, X):
        return np.tile(self.frequences_, (len(X), 1))

    def predict(self, X):
        return np.zeros(len(X), dtype=int)


class ModeleElo(BaseEstimator, ClassifierMixin):
    """Probabilités tirées du seul écart de score Elo."""

    def fit(self, X, y):
        self.lr_ = LogisticRegression(max_iter=1000).fit(self._x(X), y)
        self.classes_ = self.lr_.classes_
        return self

    @staticmethod
    def _x(X):
        return np.asarray(X["elo_diff"], dtype=float).reshape(-1, 1) / 100

    def predict_proba(self, X):
        return self.lr_.predict_proba(self._x(X))

    def predict(self, X):
        return self.predict_proba(X).argmax(axis=1)


def regression_logistique(C: float = 0.1):
    return make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=2000))


def foret_aleatoire(seed: int = 0):
    return RandomForestClassifier(n_estimators=400, min_samples_leaf=25, max_features="sqrt",
                                  random_state=seed, n_jobs=-1)


def gradient_boosting(seed: int = 0):
    return HistGradientBoostingClassifier(learning_rate=0.03, max_depth=3, max_iter=300,
                                          min_samples_leaf=40, l2_regularization=1.0,
                                          early_stopping=True, validation_fraction=0.15,
                                          random_state=seed)

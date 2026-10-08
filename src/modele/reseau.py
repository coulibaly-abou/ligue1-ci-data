"""Réseau de neurones (MLP PyTorch) pour prédire D / N / E.

Avec ~1 500 matchs d'entraînement, le réseau reste petit et fortement régularisé :
dropout, pénalité L2, arrêt anticipé sur les matchs les plus récents de l'entraînement,
et moyenne de plusieurs initialisations (graines) pour stabiliser les probabilités.
"""
import numpy as np
import torch
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.preprocessing import StandardScaler
from torch import nn


class MLP(nn.Module):
    def __init__(self, n_entrees: int, couches=(32, 16), dropout: float = 0.3):
        super().__init__()
        blocs, n = [], n_entrees
        for taille in couches:
            blocs += [nn.Linear(n, taille), nn.ReLU(), nn.Dropout(dropout)]
            n = taille
        blocs.append(nn.Linear(n, 3))
        self.reseau = nn.Sequential(*blocs)

    def forward(self, x):
        return self.reseau(x)


class ClassifieurMLP(BaseEstimator, ClassifierMixin):
    def __init__(self, couches=(32, 16), dropout=0.3, weight_decay=1e-3, lr=1e-3,
                 epoques=400, patience=30, part_validation=0.15, n_graines=5):
        self.couches = couches
        self.dropout = dropout
        self.weight_decay = weight_decay
        self.lr = lr
        self.epoques = epoques
        self.patience = patience
        self.part_validation = part_validation
        self.n_graines = n_graines

    def fit(self, X, y):
        self.classes_ = np.arange(3)
        self.scaler_ = StandardScaler().fit(X)
        Xs = torch.tensor(self.scaler_.transform(X), dtype=torch.float32)
        yt = torch.tensor(np.asarray(y), dtype=torch.long)
        # validation = fin chronologique de l'entraînement (les lignes sont triées par date)
        coupe = int(len(Xs) * (1 - self.part_validation))
        self.reseaux_, self.courbes_ = [], []
        for graine in range(self.n_graines):
            reseau, courbe = self._entrainer(Xs[:coupe], yt[:coupe], Xs[coupe:], yt[coupe:],
                                             graine)
            self.reseaux_.append(reseau)
            self.courbes_.append(courbe)
        return self

    def _entrainer(self, Xa, ya, Xv, yv, graine):
        torch.manual_seed(graine)
        reseau = MLP(Xa.shape[1], self.couches, self.dropout)
        opt = torch.optim.Adam(reseau.parameters(), lr=self.lr, weight_decay=self.weight_decay)
        perte = nn.CrossEntropyLoss()
        meilleur, etat, attente, courbe = np.inf, None, 0, []
        gen = torch.Generator().manual_seed(graine)
        for _ in range(self.epoques):
            reseau.train()
            for lot in torch.randperm(len(Xa), generator=gen).split(64):
                opt.zero_grad()
                perte(reseau(Xa[lot]), ya[lot]).backward()
                opt.step()
            reseau.eval()
            with torch.no_grad():
                pa = perte(reseau(Xa), ya).item()
                pv = perte(reseau(Xv), yv).item()
            courbe.append((pa, pv))
            if pv < meilleur - 1e-4:
                meilleur, attente = pv, 0
                etat = {k: v.clone() for k, v in reseau.state_dict().items()}
            else:
                attente += 1
                if attente >= self.patience:
                    break
        reseau.load_state_dict(etat)
        reseau.eval()
        return reseau, courbe

    def predict_proba(self, X):
        Xs = torch.tensor(self.scaler_.transform(X), dtype=torch.float32)
        with torch.no_grad():
            probas = [torch.softmax(r(Xs), dim=1).numpy() for r in self.reseaux_]
        return np.mean(probas, axis=0)

    def predict(self, X):
        return self.predict_proba(X).argmax(axis=1)

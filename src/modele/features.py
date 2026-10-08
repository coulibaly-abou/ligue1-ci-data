"""Variables connues AVANT chaque match (aucune fuite d'information).

Les matchs sont parcourus dans l'ordre chronologique : pour chaque match on lit
l'état courant des deux équipes (Elo, forme, classement...), puis on met cet état
à jour avec le résultat. Le même objet sert à calculer les variables des matchs
à venir (état après le dernier match joué).
"""
from collections import defaultdict, deque
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

CLASSES = ["D", "N", "E"]  # victoire domicile, nul, victoire extérieur
LIBELLES = {"D": "Victoire domicile", "N": "Nul", "E": "Victoire extérieur"}

SQL_MATCHS = """
SELECT m.id_match, m.id_saison, s.libelle AS saison, m.phase, m.date_match, m.statut,
       d.nom AS dom, x.nom AS ext, m.buts_dom, m.buts_ext, m.resultat
FROM ligue1.v_match m
JOIN ligue1.saison s USING (id_saison)
JOIN ligue1.club d ON d.id_club = m.id_club_dom
JOIN ligue1.club x ON x.id_club = m.id_club_ext
ORDER BY m.date_match NULLS LAST, m.id_match
"""


def charger_matchs() -> pd.DataFrame:
    """Tous les matchs (joués et à jouer) depuis PostgreSQL."""
    from src.stockage.postgres_client import lire

    df = lire(SQL_MATCHS)
    df["date_match"] = pd.to_datetime(df["date_match"])
    return df


@dataclass
class ParamsElo:
    k: float = 20.0
    avantage_terrain: float = 60.0  # points Elo ajoutés à l'équipe qui reçoit
    initial: float = 1500.0
    promu: float = 1450.0           # club qui apparaît après la 1re saison
    retour_moyenne: float = 0.25    # part de l'écart à 1500 effacée entre deux saisons


def _multiplicateur_ecart(ecart: int) -> float:
    """Pondération World Football Elo : une large victoire compte davantage."""
    if ecart <= 1:
        return 1.0
    if ecart == 2:
        return 1.5
    return (11 + ecart) / 8


@dataclass
class ConstructeurFeatures:
    elo: ParamsElo = field(default_factory=ParamsElo)

    def __post_init__(self):
        self.notes: dict[str, float] = {}
        self.historique = defaultdict(lambda: deque(maxlen=10))      # (pts, bp, bc)
        self.histo_dom = defaultdict(lambda: deque(maxlen=10))       # pts à domicile
        self.histo_ext = defaultdict(lambda: deque(maxlen=10))       # pts à l'extérieur
        self.dernier_match: dict[str, pd.Timestamp] = {}
        self.saison_courante = None
        self.nb_saisons = 0
        self.table = defaultdict(lambda: [0, 0, 0])                  # pts, diff, joués

    # ---------------------------------------------------------------- état
    def _nouvelle_saison(self, saison) -> None:
        if self.saison_courante is not None:
            r = self.elo.retour_moyenne
            self.notes = {c: n - r * (n - self.elo.initial) for c, n in self.notes.items()}
        self.saison_courante = saison
        self.nb_saisons += 1
        self.table = defaultdict(lambda: [0, 0, 0])

    def note(self, club: str) -> float:
        if club not in self.notes:
            self.notes[club] = self.elo.initial if self.nb_saisons <= 1 else self.elo.promu
        return self.notes[club]

    def _rang(self, club: str) -> float:
        """Rang dans la saison en cours, ramené entre 0 (1er) et 1 (dernier)."""
        if not self.table:
            return 0.5
        ordre = sorted(self.table, key=lambda c: (-self.table[c][0], -self.table[c][1]))
        if club not in self.table:
            return 0.5
        return ordre.index(club) / max(len(ordre) - 1, 1)

    def _forme(self, club: str, n: int) -> tuple[float, float, float]:
        h = list(self.historique[club])[-n:]
        if not h:
            return 1.35, 1.1, 1.1  # moyennes du championnat : valeur neutre
        pts, bp, bc = zip(*h)
        return float(np.mean(pts)), float(np.mean(bp)), float(np.mean(bc))

    # ------------------------------------------------------------ variables
    def features(self, dom: str, ext: str, date=None, saison=None) -> dict:
        if saison is not None and saison != self.saison_courante:
            self._nouvelle_saison(saison)
        elo_dom, elo_ext = self.note(dom), self.note(ext)
        f = {"elo_dom": elo_dom, "elo_ext": elo_ext, "elo_diff": elo_dom - elo_ext}
        for cote, club in (("dom", dom), ("ext", ext)):
            pts5, bp5, bc5 = self._forme(club, 5)
            pts10, _, _ = self._forme(club, 10)
            pts, diff, joues = self.table.get(club, (0, 0, 0))
            f[f"forme5_{cote}"] = pts5
            f[f"forme10_{cote}"] = pts10
            f[f"bp5_{cote}"] = bp5
            f[f"bc5_{cote}"] = bc5
            f[f"ppm_saison_{cote}"] = pts / joues if joues else 1.35
            f[f"diff_saison_{cote}"] = diff / joues if joues else 0.0
            f[f"rang_{cote}"] = self._rang(club)
            dernier = self.dernier_match.get(club)
            repos = (date - dernier).days if date is not None and dernier is not None \
                and pd.notna(date) else 7
            f[f"repos_{cote}"] = float(np.clip(repos, 2, 30))
        h_dom, h_ext = self.histo_dom[dom], self.histo_ext[ext]
        f["forme_domicile_dom"] = float(np.mean(h_dom)) if h_dom else 1.6
        f["forme_exterieur_ext"] = float(np.mean(h_ext)) if h_ext else 1.0
        f["matchs_saison"] = float(min(self.table.get(dom, (0, 0, 0))[2],
                                       self.table.get(ext, (0, 0, 0))[2]))
        return f

    def mettre_a_jour(self, dom: str, ext: str, buts_dom: int, buts_ext: int, date=None):
        # Elo
        attendu = 1 / (1 + 10 ** (-(self.note(dom) + self.elo.avantage_terrain
                                    - self.note(ext)) / 400))
        reel = 1.0 if buts_dom > buts_ext else 0.5 if buts_dom == buts_ext else 0.0
        delta = self.elo.k * _multiplicateur_ecart(abs(buts_dom - buts_ext)) * (reel - attendu)
        self.notes[dom] += delta
        self.notes[ext] -= delta
        # forme, classement, repos
        pts_dom = 3 if reel == 1 else 1 if reel == 0.5 else 0
        pts_ext = 3 if reel == 0 else 1 if reel == 0.5 else 0
        self.historique[dom].append((pts_dom, buts_dom, buts_ext))
        self.historique[ext].append((pts_ext, buts_ext, buts_dom))
        self.histo_dom[dom].append(pts_dom)
        self.histo_ext[ext].append(pts_ext)
        for club, pts, diff in ((dom, pts_dom, buts_dom - buts_ext),
                                (ext, pts_ext, buts_ext - buts_dom)):
            ligne = self.table[club]
            ligne[0] += pts
            ligne[1] += diff
            ligne[2] += 1
            if date is not None and pd.notna(date):
                self.dernier_match[club] = date


def construire_jeu(matchs: pd.DataFrame, params: ParamsElo | None = None
                   ) -> tuple[pd.DataFrame, ConstructeurFeatures]:
    """Une ligne par match joué : variables d'avant-match + résultat (cible).

    Renvoie aussi le constructeur, dans l'état qui suit le dernier match joué.
    """
    cf = ConstructeurFeatures(params or ParamsElo())
    joues = matchs[matchs["statut"] == "joue"].sort_values(["date_match", "id_match"])
    lignes = []
    for m in joues.itertuples():
        f = cf.features(m.dom, m.ext, m.date_match, m.id_saison)
        lignes.append({"id_match": m.id_match, "id_saison": m.id_saison, "saison": m.saison,
                       "date_match": m.date_match, "dom": m.dom, "ext": m.ext,
                       "buts_dom": m.buts_dom, "buts_ext": m.buts_ext,
                       "resultat": m.resultat, **f})
        cf.mettre_a_jour(m.dom, m.ext, int(m.buts_dom), int(m.buts_ext), m.date_match)
    return pd.DataFrame(lignes), cf


# Variables données aux modèles (les écarts dom - ext sont ajoutés)
VARIABLES_BASE = ["elo_dom", "elo_ext", "forme5_dom", "forme5_ext", "forme10_dom",
                  "forme10_ext", "bp5_dom", "bp5_ext", "bc5_dom", "bc5_ext",
                  "ppm_saison_dom", "ppm_saison_ext", "diff_saison_dom", "diff_saison_ext",
                  "rang_dom", "rang_ext", "repos_dom", "repos_ext",
                  "forme_domicile_dom", "forme_exterieur_ext", "matchs_saison"]


def matrice(df: pd.DataFrame) -> pd.DataFrame:
    """Variables explicatives, avec les écarts entre les deux équipes."""
    X = df[VARIABLES_BASE].copy()
    X["elo_diff"] = df["elo_dom"] - df["elo_ext"]
    X["forme5_diff"] = df["forme5_dom"] - df["forme5_ext"]
    X["ppm_diff"] = df["ppm_saison_dom"] - df["ppm_saison_ext"]
    X["rang_diff"] = df["rang_dom"] - df["rang_ext"]
    X["attaque_defense"] = df["bp5_dom"] - df["bc5_ext"] - (df["bp5_ext"] - df["bc5_dom"])
    return X


def cible(df: pd.DataFrame) -> np.ndarray:
    return df["resultat"].map({c: i for i, c in enumerate(CLASSES)}).to_numpy()

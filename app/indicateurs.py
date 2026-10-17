"""Indicateurs du tableau de bord : filtres et bilans, sans Streamlit (testés dans tests/).

Toutes les fonctions prennent les tables de app/data/ et renvoient des valeurs brutes ;
la mise en forme reste dans les pages. Définitions détaillées : docs/indicateurs.md.
"""
from dataclasses import dataclass

import pandas as pd

LIEUX = ("Tous", "Domicile", "Extérieur")
PHASES = {"Saison reguliere": "Saison régulière", "Regular Stage": "Saison régulière",
          "Group Stage": "Phase de groupes",
          "Championship Playoff (Super Division)": "Play-off"}
SEUIL_NOTE = 3  # en dessous de 3 buts, la note d'un joueur est indicative
# Copie des pondérations de src/restitution/joueurs.py (l'application déployée n'importe pas
# src/) ; tests/test_indicateurs.py vérifie que les deux restent identiques
POIDS = {"buts": 0.35, "buts_decisifs": 0.25, "part_buts_club": 0.20, "matchs_avec_but": 0.20}
MALUS_ROUGE = 0.5


def phase(libelle: str) -> str:
    """Libellé de phase harmonisé (les sources mélangent français et anglais)."""
    return PHASES.get(libelle, libelle)


def filtrer_resultats(resultats: pd.DataFrame, *, saison: str | None = None,
                      lieu: str = "Tous", journees: tuple[int, int] | None = None,
                      adversaire: str | None = None) -> pd.DataFrame:
    """Matchs d'un ou plusieurs clubs (une ligne par club et par match) selon les filtres.

    `journees` : bornes incluses sur le numéro de match du club dans la saison.
    """
    r = resultats
    if saison:
        r = r[r["saison"] == saison]
    if lieu == "Domicile":
        r = r[r["a_domicile"]]
    elif lieu == "Extérieur":
        r = r[~r["a_domicile"]]
    if journees:
        r = r[r["journee_club"].between(*journees)]
    if adversaire:
        r = r[r["adversaire"] == adversaire]
    return r


@dataclass(frozen=True)
class Bilan:
    matchs: int
    victoires: int
    nuls: int
    defaites: int
    buts_pour: int
    buts_contre: int
    points: int
    sans_encaisser: int
    sans_marquer: int

    @property
    def difference(self) -> int:
        return self.buts_pour - self.buts_contre

    def par_match(self, valeur: float) -> float | None:
        """Moyenne par match ; None (et non 0) quand il n'y a aucun match."""
        return valeur / self.matchs if self.matchs else None

    def taux(self, valeur: int) -> float | None:
        return valeur / self.matchs if self.matchs else None


def bilan(r: pd.DataFrame) -> Bilan:
    """Bilan d'un club sur des lignes de resultats_club (3 pts victoire, 1 pt nul)."""
    return Bilan(matchs=len(r), victoires=int((r["issue"] == "V").sum()),
                 nuls=int((r["issue"] == "N").sum()), defaites=int((r["issue"] == "D").sum()),
                 buts_pour=int(r["bp"].sum()), buts_contre=int(r["bc"].sum()),
                 points=int(r["points"].sum()), sans_encaisser=int((r["bc"] == 0).sum()),
                 sans_marquer=int((r["bp"] == 0).sum()))


def tendance(r: pd.DataFrame, n: int = 5) -> dict | None:
    """Points par match sur les n derniers matchs comparés au reste de la sélection.

    None si la sélection compte moins de 2n matchs : écart non interprétable.
    """
    r = r.sort_values("date_match")
    if len(r) < 2 * n:
        return None
    recents, avant = r.tail(n), r.iloc[:-n]
    return {"recent": recents["points"].mean(), "avant": avant["points"].mean(),
            "ecart": recents["points"].mean() - avant["points"].mean(), "n": n}


def classement(resultats: pd.DataFrame, saison: str, lieu: str = "Tous",
               journees: tuple[int, int] | None = None) -> pd.DataFrame:
    """Classement recalculé avec les mêmes filtres (points, puis différence, puis buts)."""
    r = filtrer_resultats(resultats, saison=saison, lieu=lieu, journees=journees)
    t = r.groupby("club").agg(J=("issue", "size"), V=("issue", lambda s: (s == "V").sum()),
                              N=("issue", lambda s: (s == "N").sum()),
                              D=("issue", lambda s: (s == "D").sum()),
                              BP=("bp", "sum"), BC=("bc", "sum"), Pts=("points", "sum"))
    t["Diff"] = t["BP"] - t["BC"]
    t = t.sort_values(["Pts", "Diff", "BP"], ascending=False)
    t.insert(0, "Rang", range(1, len(t) + 1))
    return t


def bilan_adversaires(r: pd.DataFrame) -> pd.DataFrame:
    """Bilan d'un club face à chaque adversaire (sur la sélection filtrée)."""
    t = r.groupby("adversaire").agg(
        matchs=("issue", "size"), V=("issue", lambda s: (s == "V").sum()),
        N=("issue", lambda s: (s == "N").sum()), D=("issue", lambda s: (s == "D").sum()),
        bp=("bp", "sum"), bc=("bc", "sum"), points=("points", "sum"))
    t["ppm"] = t["points"] / t["matchs"]
    return t.sort_values(["matchs", "ppm"], ascending=False)


def voisins(matchs: pd.DataFrame, id_match: int, club: str | None = None
            ) -> tuple[int | None, int | None]:
    """Match précédent et suivant (même saison ; du club s'il est précisé)."""
    m = matchs.set_index("id_match")
    saison = m.loc[id_match, "saison"]
    liste = matchs[(matchs["saison"] == saison) & (matchs["statut"] == "joue")]
    if club:
        liste = liste[(liste["dom"] == club) | (liste["ext"] == club)]
    liste = liste.sort_values(["date_match", "id_match"])
    ids = list(liste["id_match"])
    if id_match not in ids:
        return None, None
    i = ids.index(id_match)
    return (ids[i - 1] if i > 0 else None), (ids[i + 1] if i + 1 < len(ids) else None)


def prochains_matchs(matchs: pd.DataFrame, club: str, n: int = 5) -> pd.DataFrame:
    """Matchs à jouer du club, datés d'abord (les dates non confirmées à la fin)."""
    a_venir = matchs[(matchs["statut"] == "a_jouer")
                     & ((matchs["dom"] == club) | (matchs["ext"] == club))]
    return a_venir.sort_values("date_match", na_position="last").head(n)

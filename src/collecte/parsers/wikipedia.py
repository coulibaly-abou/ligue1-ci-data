"""Extraction des tableaux utiles d'un article Wikipédia de saison (fr ou en).

- participants : Club, Ville, Stade, Capacité                 -> raw_clubs
- buteurs : Buteur, Club, Buts                               -> raw_scorers
- classement : Rang, Équipe, Pts, J, G, N, P, Bp, Bc         -> raw_standings
- grille des résultats (domicile en ligne, extérieur en colonne)
      cases avec score -> raw_matches ; cases « - » -> raw_fixtures (à jouer)
Selon les saisons, un tableau peut manquer : on renvoie alors une liste vide.
"""
import io
import re

import pandas as pd

# Noms de colonnes possibles, en français et en anglais
COL_CLUB = ("Club", "Team", "Équipe")
COL_VILLE = ("Ville", "Location", "Home city")
COL_STADE = ("Stade", "Stadium")
COL_CAPACITE = ("Capacité", "Capacity")
COL_JOUEUR = ("Buteur", "Joueur", "Player")
COL_BUTS = ("Buts", "Goals", "Number of goals")
COL_CLASSEMENT = {"rang": "Rang", "equipe": "Équipe", "pts": "Pts", "j": "J", "g": "G",
                  "n": "N", "p": "P", "bp": "Bp", "bc": "Bc"}
RE_SCORE = re.compile(r"(\d+)\s*[-–]\s*(\d+)")


def _tableaux(html: str) -> list[pd.DataFrame]:
    try:
        tables = pd.read_html(io.StringIO(html), flavor="lxml")
    except ValueError:  # aucun <table> dans la page
        return []
    for t in tables:
        t.columns = [
            re.sub(r"\[\d+\]", "", str(c[-1] if isinstance(c, tuple) else c)).strip()
            for c in t.columns
        ]
    return tables


def _texte(valeur) -> str | None:
    if pd.isna(valeur):
        return None
    return re.sub(r"\[\d+\]", "", str(valeur)).strip() or None  # retire les renvois [1]


def _entier(valeur) -> int | None:
    chiffres = re.sub(r"\D", "", str(valeur)) if not pd.isna(valeur) else ""
    return int(chiffres) if chiffres else None


def _colonne(table: pd.DataFrame, noms: tuple[str, ...]) -> str | None:
    return next((c for c in noms if c in table.columns), None)


def _source(url: str) -> str:
    return "wikipedia_en" if "en.wikipedia" in url else "wikipedia"


def parse_clubs(html: str, saison: str, url: str) -> list[dict]:
    for t in _tableaux(html):
        club, stade = _colonne(t, COL_CLUB[:2]), _colonne(t, COL_STADE)
        if club and stade:
            ville, capacite = _colonne(t, COL_VILLE), _colonne(t, COL_CAPACITE)
            return [
                {
                    "saison": saison,
                    "club": _texte(ligne[club]),
                    "ville": _texte(ligne[ville]) if ville else None,
                    "stade": _texte(ligne[stade]),
                    "capacite": _entier(ligne[capacite]) if capacite else None,
                    "url_source": url,
                    "source": _source(url),
                }
                for _, ligne in t.iterrows()
                if _texte(ligne[club])
            ]
    return []


def parse_buteurs(html: str, saison: str, url: str) -> list[dict]:
    for t in _tableaux(html):
        joueur, buts = _colonne(t, COL_JOUEUR), _colonne(t, COL_BUTS)
        if joueur and buts:
            club, matchs = _colonne(t, COL_CLUB), _colonne(t, ("Match", "Matchs"))
            return [
                {
                    "saison": saison,
                    "joueur": _texte(ligne[joueur]),
                    "club": _texte(ligne[club]) if club else None,
                    "buts": _entier(ligne[buts]),
                    "matchs": _entier(ligne[matchs]) if matchs else None,
                    "url_source": url,
                    "source": _source(url),
                }
                for _, ligne in t.iterrows()
                if _texte(ligne[joueur])
            ]
    return []


def parse_classements(html: str, saison: str, url: str) -> list[dict]:
    """Tous les tableaux de classement (plusieurs en cas de poules)."""
    lignes = []
    tables = [t for t in _tableaux(html) if set(COL_CLASSEMENT.values()) <= set(t.columns)]
    for numero, t in enumerate(tables, start=1):
        for _, ligne in t.iterrows():
            rang = _entier(ligne["Rang"])
            if rang is None:
                continue
            lignes.append({
                "saison": saison,
                "phase": "Saison reguliere",
                "type_tableau": "wikipedia",
                "groupe": str(numero) if len(tables) > 1 else None,
                "rang": rang,
                "equipe": _texte(ligne["Équipe"]),  # peut finir par une lettre de note (T, P, C)
                **{k: _entier(ligne[c]) for k, c in COL_CLASSEMENT.items()
                   if k not in ("rang", "equipe")},
                "mention": None,
                "url_source": url,
                "source": _source(url),
            })
    return lignes


def _table_grille(html: str) -> pd.DataFrame | None:
    for t in _tableaux(html):
        if t.shape[0] > 2 and str(t.iloc[0, 0]).startswith(("Résultats", "Home")):
            return t
    return None


def parse_grille(html: str, saison: str, url: str) -> tuple[list[dict], list[dict]]:
    """Renvoie (matchs joués, matchs à jouer) lus dans la grille des résultats."""
    t = _table_grille(html)
    if t is None:
        return [], []
    equipes = [_texte(v) for v in t.iloc[1:, 0]]
    n = sum(1 for e in equipes if e and not e.startswith("Victoire"))  # ignore la légende
    equipes = equipes[:n]
    joues, a_jouer = [], []
    for i, dom in enumerate(equipes):
        for j, ext in enumerate(equipes):
            if i == j:
                continue
            case = _texte(t.iloc[i + 1, j + 1]) or ""
            base = {"saison": saison, "equipe_dom": dom, "equipe_ext": ext,
                    "url_source": url, "source": _source(url)}
            if m := RE_SCORE.search(case):
                joues.append({**base, "phase": "Saison reguliere", "journee": None,
                              "date": None, "buts_dom": int(m.group(1)),
                              "buts_ext": int(m.group(2)), "statut": "joue",
                              "note": None, "ligne_brute": case})
            else:
                a_jouer.append({**base, "case_brute": case})
    return joues, a_jouer

"""Nettoyage : normalisation des noms de clubs et de stades, contrôles de cohérence."""
import re
import unicodedata
from functools import cache

import yaml

from config.settings import FICHIER_ALIAS, FICHIER_ALIAS_STADES

# Lettres de note des classements Wikipédia (Tenant, Promu, Coupe) : « SOAT »,
# « ASEC Mimosas T C », « Bouaké FCP » (ici une seule lettre : FC + P)
RE_UNE_NOTE = re.compile(r"\s*[TPC]$")
CAPACITE_MAX = 60_000


def normaliser(texte: str | None) -> str:
    """Clé de comparaison : minuscules, sans accents, ponctuation ni parenthèses.

    « Stade (Abidjan) » -> « stade » ; « ES d’Agboville » -> « es d agboville ».
    """
    if not texte:
        return ""
    texte = re.sub(r"\(.*?\)", " ", texte)
    texte = unicodedata.normalize("NFKD", texte)
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    texte = re.sub(r"[^a-z0-9]+", " ", texte.lower())
    return texte.strip()


@cache
def _charger_alias(chemin) -> dict[str, str]:
    """Nom normalisé (officiel ou alias) -> nom officiel, lu dans un fichier YAML."""
    with open(chemin, encoding="utf-8") as f:
        alias = yaml.safe_load(f)
    table = {}
    for officiel, autres in alias.items():
        for nom in [officiel, *(autres or [])]:
            cle = normaliser(nom)
            if table.get(cle, officiel) != officiel:
                raise ValueError(f"Alias « {nom} » attribué à deux noms dans {chemin}")
            table[cle] = officiel
    return table


def table_alias() -> dict[str, str]:
    return _charger_alias(FICHIER_ALIAS)


def resoudre_stade(nom: str | None) -> str | None:
    """Nom retenu d'un stade (config/stades_alias.yml), ou le nom d'origine nettoyé."""
    if not nom or not normaliser(nom):
        return None
    return _charger_alias(FICHIER_ALIAS_STADES).get(normaliser(nom), nom.strip())


def capacite_plausible(capacite) -> int | None:
    """Capacité d'un stade ivoirien : le plus grand (Ebimpé) compte environ 60 000 places."""
    return int(capacite) if capacite and 0 < capacite <= CAPACITE_MAX else None


def resoudre_club(nom: str | None) -> str | None:
    """Nom officiel d'un club ivoirien, ou None s'il n'est pas reconnu."""
    if not nom:
        return None
    table = table_alias()
    candidat = nom.strip()
    for _ in range(3):  # nom tel quel, puis sans 1, puis sans 2 lettres de note
        officiel = table.get(normaliser(candidat))
        if officiel:
            return officiel
        candidat = RE_UNE_NOTE.sub("", candidat)
    return None


# --- Contrôles de cohérence -------------------------------------------------

def anomalies_match(match: dict) -> list[str]:
    """Problèmes détectés sur un match (liste vide si tout va bien)."""
    problemes = []
    if not match.get("club_dom") or not match.get("club_ext"):
        problemes.append("club non reconnu")
    elif match["club_dom"] == match["club_ext"]:
        problemes.append("un club joue contre lui-même")
    for cote in ("buts_dom", "buts_ext"):
        buts = match.get(cote)
        if buts is not None and not 0 <= buts <= 20:
            problemes.append(f"{cote} invraisemblable : {buts}")
    if match.get("statut") == "joue" and (match.get("buts_dom") is None
                                         or match.get("buts_ext") is None):
        problemes.append("match joué sans score")
    date, saison = match.get("date"), match.get("saison")
    if date and saison:
        debut, fin = (int(a) for a in saison.split("-"))
        if not f"{debut}-07-01" <= date <= f"{fin}-08-31":
            problemes.append(f"date {date} hors de la saison {saison}")
    return problemes


def resultat(buts_dom: int | None, buts_ext: int | None) -> str | None:
    """'D' victoire domicile, 'N' nul, 'E' victoire extérieur (cible du modèle)."""
    if buts_dom is None or buts_ext is None:
        return None
    return "D" if buts_dom > buts_ext else "E" if buts_dom < buts_ext else "N"

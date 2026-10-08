"""Wikipédia (fr) : coordonnées géographiques des villes des clubs, pour la carte.

Les coordonnées sont celles publiées par l'article de la ville (variable wgCoordinates
de la page, la même que le lien de carte de l'infobox). On essaie d'abord le titre
« Ville (Côte d'Ivoire) » pour éviter les homonymes (Touba existe aussi au Sénégal),
et on rejette tout point hors du territoire ivoirien.
"""
import re
from urllib.parse import quote

from src.collecte.scrapers.http import PageAbsente, telecharger_page

SOURCE = "wikipedia_fr"
BASE = "https://fr.wikipedia.org/wiki/"
# Emprise de la Côte d'Ivoire (avec une petite marge) : contrôle de cohérence
LAT_MIN, LAT_MAX, LON_MIN, LON_MAX = 4.2, 10.8, -8.7, -2.4
_COORDONNEES = re.compile(r'"wgCoordinates":\{"lat":(-?[\d.]+),"lon":(-?[\d.]+)\}')


def urls_candidates(ville: str) -> list[str]:
    titres = [f"{ville} (Côte d'Ivoire)", ville]
    return [BASE + quote(t.replace(" ", "_")) for t in titres]


def parse_coordonnees(html: str) -> tuple[float, float] | None:
    m = _COORDONNEES.search(html)
    return (float(m.group(1)), float(m.group(2))) if m else None


def en_cote_divoire(lat: float, lon: float) -> bool:
    return LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX


def chercher_ville(ville: str) -> tuple[dict, list[tuple[str, str]]]:
    """Document raw_villes + pages téléchargées [(url, html)] à archiver."""
    pages = []
    for url in urls_candidates(ville):
        try:
            html = telecharger_page(url)
        except PageAbsente:
            continue
        pages.append((url, html))
        coord = parse_coordonnees(html)
        if coord and en_cote_divoire(*coord):
            return ({"ville": ville, "latitude": coord[0], "longitude": coord[1],
                     "url_source": url, "statut": "ok", "source": SOURCE}, pages)
    return ({"ville": ville, "latitude": None, "longitude": None, "url_source": None,
             "statut": "introuvable", "source": SOURCE}, pages)

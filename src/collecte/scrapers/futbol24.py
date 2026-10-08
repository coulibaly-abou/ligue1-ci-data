"""Futbol24 : calendrier daté et résultats de la saison en cours (2 pages).

Utilisé uniquement pour la saison en cours, que RSSSF n'a pas encore publiée,
et pour les dates des prochains matchs. Les pages /api/ sont interdites par
le robots.txt : on ne lit que les pages publiques.
"""
from src.collecte.scrapers.http import telecharger_page

SOURCE = "futbol24"
BASE = "https://www.futbol24.com/fr/national/Ivory-Coast/Ligue-1/{saison}/{page}"


def telecharger_saison(saison: str) -> list[tuple[str, str]]:
    """Renvoie [(url, html)] des pages résultats et calendrier."""
    pages = []
    for page in ("resultats", "calendrier"):
        url = BASE.format(saison=saison, page=page)
        pages.append((url, telecharger_page(url)))
    return pages

"""RSSSF : résultats journée par journée et classements finaux.

Une page par saison : https://rsssf.org/tablesi/ivo2025.html pour 2024-2025
(le numéro est l'année de fin de saison).
"""
from src.collecte.scrapers.http import telecharger_page

SOURCE = "rsssf"


def url_saison(saison: str) -> str:
    annee_fin = saison.split("-")[1]
    return f"https://rsssf.org/tablesi/ivo{annee_fin}.html"


def telecharger_saison(saison: str) -> tuple[str, str]:
    """Renvoie (url, html) de la page RSSSF de la saison."""
    url = url_saison(saison)
    return url, telecharger_page(url)

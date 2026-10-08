"""Wikipédia : articles de saison (fr et en) — clubs, stades, buteurs, classement, grille."""
from src.collecte.scrapers.http import telecharger_page

SOURCE = "wikipedia"
SOURCE_EN = "wikipedia_en"
BASE = "https://fr.wikipedia.org/wiki/Championnat_de_C%C3%B4te_d%27Ivoire_de_football_"
BASE_EN = "https://en.wikipedia.org/wiki/{debut}%E2%80%93{fin}_Ligue_1_(Ivory_Coast)"


def url_saison(saison: str) -> str:
    return BASE + saison


def url_saison_en(saison: str) -> str:
    debut, fin = saison.split("-")
    return BASE_EN.format(debut=debut, fin=fin[2:])  # 2024-2025 -> 2024–25


def telecharger_saison(saison: str, langue: str = "fr") -> tuple[str, str]:
    """Renvoie (url, html) de l'article Wikipédia de la saison."""
    url = url_saison(saison) if langue == "fr" else url_saison_en(saison)
    return url, telecharger_page(url)

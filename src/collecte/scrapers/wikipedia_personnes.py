"""Wikipédia (en + fr) : joueurs et entraîneurs passés par un club ivoirien.

On part des catégories « joueurs par club en Côte d'Ivoire » (une sous-catégorie par
club), puis on liste les articles de chaque sous-catégorie.
"""
from src.collecte.parsers.wikipedia_personnes import parse_membres, parse_sous_categories
from src.collecte.scrapers.http import telecharger_page
from src.utils.logs import get_logger

log = get_logger("collecte")

# (langue, rôle, catégorie racine)
CATEGORIES = [
    ("en", "joueur",
     "https://en.wikipedia.org/wiki/Category:Men%27s_footballers_in_Ivory_Coast_by_club"),
    ("en", "entraineur",
     "https://en.wikipedia.org/wiki/Category:Football_managers_in_Ivory_Coast_by_club"),
    ("fr", "joueur",
     "https://fr.wikipedia.org/wiki/Cat%C3%A9gorie:Footballeur_par_club_en_C%C3%B4te_d%27Ivoire"),
]


def _membres_categorie(url: str) -> list[dict]:
    """Tous les articles d'une catégorie, en suivant la pagination."""
    membres = []
    while url:
        page, url = parse_membres(telecharger_page(url), url)
        membres += page
    return membres


def lister_personnes() -> dict[str, dict]:
    """URL d'article -> {langue, roles, categories} pour toutes les catégories de clubs."""
    personnes: dict[str, dict] = {}
    for langue, role, racine in CATEGORIES:
        for sous_cat in parse_sous_categories(telecharger_page(racine), racine):
            try:
                membres = _membres_categorie(sous_cat["url"])
            except Exception as exc:  # noqa: BLE001 — une catégorie en échec ne bloque pas
                log.error("catégorie %s | ÉCHEC : %r", sous_cat["url"], exc)
                continue
            for membre in membres:
                fiche = personnes.setdefault(
                    membre["url"], {"langue": langue, "roles": set(), "categories": set()}
                )
                fiche["roles"].add(role)
                fiche["categories"].add(sous_cat["categorie"])
    return personnes

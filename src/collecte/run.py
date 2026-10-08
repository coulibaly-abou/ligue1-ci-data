"""Point d'entrée de la collecte.

    python -m src.collecte.run                       # tout : saisons + joueurs/entraîneurs
    python -m src.collecte.run --saison 2024-2025    # une seule saison
    python -m src.collecte.run --sans-personnes      # saisons seulement (rapide)
    python -m src.collecte.run --sans-api            # sans API-Football (quota 100/jour)
    python -m src.collecte.run --villes              # coordonnées des villes seulement
"""
import argparse
import hashlib
import time
from datetime import datetime, timezone

from config.settings import API_FOOTBALL_KEY, SAISON_EN_COURS, SAISONS
from src.collecte.parsers import futbol24 as parser_futbol24
from src.collecte.parsers import rsssf as parser_rsssf
from src.collecte.parsers import wikipedia as parser_wiki
from src.collecte.parsers.wikipedia_personnes import parse_personne
from src.collecte.scrapers import (
    api_football,
    futbol24,
    rsssf,
    wikipedia,
    wikipedia_personnes,
    wikipedia_villes,
)
from src.collecte.scrapers.http import PageAbsente, telecharger_page
from src.stockage.mongo_client import creer_index, get_db, lire_page, sauver
from src.utils.logs import get_logger

log = get_logger("collecte")

# Une fiche joueur change rarement : on la re-télécharge au plus une fois par mois.
CACHE_PERSONNES_JOURS = 30


def archiver_page(url: str, html: str, saison: str | None, source: str) -> None:
    """Garde le HTML brut dans raw_pages (traçabilité : URL + date de collecte)."""
    sauver("raw_pages", [{
        "url": url,
        "saison": saison,
        "source": source,
        "html": html,
        "sha256": hashlib.sha256(html.encode("utf-8")).hexdigest(),
        "telecharge_le": datetime.now(timezone.utc),
    }])


def collecter_rsssf(saison: str) -> dict:
    url, html = rsssf.telecharger_saison(saison)
    archiver_page(url, html, saison, rsssf.SOURCE)
    matchs, classements = parser_rsssf.parse_page(html, saison, url)
    sauver("raw_matches", matchs)
    sauver("raw_standings", classements)
    return {"matchs": len(matchs), "classements": len(classements)}


def _collecter_article_saison(saison: str, langue: str, source: str) -> dict:
    url, html = wikipedia.telecharger_saison(saison, langue)
    archiver_page(url, html, saison, source)
    clubs = parser_wiki.parse_clubs(html, saison, url)
    buteurs = parser_wiki.parse_buteurs(html, saison, url)
    classements = parser_wiki.parse_classements(html, saison, url)
    joues, a_jouer = parser_wiki.parse_grille(html, saison, url)
    sauver("raw_clubs", clubs)
    sauver("raw_scorers", buteurs)
    sauver("raw_standings", classements)
    sauver("raw_matches", joues)
    sauver("raw_fixtures", a_jouer)
    return {"clubs": len(clubs), "buteurs": len(buteurs), "classements": len(classements),
            "matchs": len(joues), "a_jouer": len(a_jouer)}


def collecter_wikipedia(saison: str) -> dict:
    return _collecter_article_saison(saison, "fr", wikipedia.SOURCE)


def collecter_wikipedia_en(saison: str) -> dict:
    return _collecter_article_saison(saison, "en", wikipedia.SOURCE_EN)


def collecter_futbol24(saison: str) -> dict:
    bilan = {"matchs": 0, "a_jouer": 0}
    for url, html in futbol24.telecharger_saison(saison):
        archiver_page(url, html, saison, futbol24.SOURCE)
        joues, a_jouer = parser_futbol24.parse_matchs(html, saison, url)
        sauver("raw_matches", joues)
        sauver("raw_fixtures", a_jouer)
        bilan["matchs"] += len(joues)
        bilan["a_jouer"] += len(a_jouer)
    return bilan


COLLECTEURS = {
    "rsssf": collecter_rsssf,
    "wikipedia": collecter_wikipedia,
    "wikipedia_en": collecter_wikipedia_en,
}
# Sources utilisées seulement pour la saison en cours (dates des prochains matchs)
COLLECTEURS_SAISON_EN_COURS = {"futbol24": collecter_futbol24}


def collecter_personnes() -> dict:
    """Joueurs et entraîneurs des catégories Wikipédia, avec leur parcours."""
    personnes = wikipedia_personnes.lister_personnes()
    log.info("personnes | %d articles à traiter", len(personnes))
    bilan = {"fiches": 0, "sans_infobox": 0, "depuis_cache": 0, "erreurs": 0}
    for i, (url, infos) in enumerate(personnes.items(), start=1):
        try:
            html = lire_page(url, CACHE_PERSONNES_JOURS)
            if html:
                bilan["depuis_cache"] += 1
            else:
                html = telecharger_page(url)
                archiver_page(url, html, None, f"wikipedia_{infos['langue']}")
            fiche = parse_personne(html, url, infos["langue"])
            if fiche is None:
                bilan["sans_infobox"] += 1
                continue
            fiche["roles"] = sorted(infos["roles"])
            fiche["categories_clubs"] = sorted(infos["categories"])
            sauver("raw_persons", [fiche])
            bilan["fiches"] += 1
        except Exception as exc:  # noqa: BLE001 — une fiche en échec ne bloque pas les autres
            bilan["erreurs"] += 1
            log.error("personnes | %s | ÉCHEC : %r", url, exc)
        if i % 100 == 0:
            log.info("personnes | %d/%d", i, len(personnes))
    return bilan


def villes_des_clubs() -> list[str]:
    """Villes des clubs de Ligue 1 (référentiel PostgreSQL, sinon colonne Wikipédia)."""
    try:
        from src.stockage.postgres_client import lire

        return sorted(lire("SELECT DISTINCT v.nom FROM ligue1.club c JOIN ligue1.ville v "
                           "USING (id_ville) WHERE c.est_ligue1")["nom"])
    except Exception:  # noqa: BLE001 — base pas encore créée : première collecte
        return sorted(v for v in get_db().raw_clubs.distinct("ville") if v)


def collecter_villes() -> dict:
    """Coordonnées des villes manquantes (une ville déjà trouvée n'est pas re-téléchargée)."""
    deja = {d["ville"] for d in get_db().raw_villes.find({"statut": "ok"}, {"ville": 1})}
    bilan = {"trouvees": 0, "introuvables": [], "deja_connues": 0}
    for ville in villes_des_clubs():
        if ville in deja:
            bilan["deja_connues"] += 1
            continue
        doc, pages = wikipedia_villes.chercher_ville(ville)
        for url, html in pages:
            archiver_page(url, html, None, wikipedia_villes.SOURCE)
        sauver("raw_villes", [doc])
        if doc["statut"] == "ok":
            bilan["trouvees"] += 1
        else:
            bilan["introuvables"].append(ville)
    return bilan


def collecter(saisons: list[str], personnes: bool = True, api: bool = True) -> int:
    """Collecte chaque saison sur chaque source ; renvoie le nombre d'erreurs."""
    debut, erreurs = time.monotonic(), 0
    creer_index()
    for saison in saisons:
        collecteurs = dict(COLLECTEURS)
        if saison == SAISON_EN_COURS:
            collecteurs.update(COLLECTEURS_SAISON_EN_COURS)
        for source, fonction in collecteurs.items():
            try:
                bilan = fonction(saison)
                log.info("%s | %s | %s", saison, source, bilan)
            except PageAbsente as exc:  # page pas (encore) publiée : normal, pas une erreur
                log.warning("%s | %s | page absente : %s", saison, source, exc)
            except Exception as exc:  # noqa: BLE001 — une page en échec ne bloque pas les autres
                erreurs += 1
                log.error("%s | %s | ÉCHEC : %r", saison, source, exc)
    try:
        log.info("villes | %s", collecter_villes())
    except Exception as exc:  # noqa: BLE001
        erreurs += 1
        log.error("villes | ÉCHEC : %r", exc)
    if personnes:
        try:
            bilan = collecter_personnes()
            erreurs += bilan["erreurs"]
            log.info("personnes | %s", bilan)
        except Exception as exc:  # noqa: BLE001
            erreurs += 1
            log.error("personnes | ÉCHEC : %r", exc)
    if api:
        if API_FOOTBALL_KEY:
            bilan = api_football.collecter(log)
            erreurs += bilan["erreurs"]
            log.info("api_football | %s", bilan)
        else:
            log.warning("api_football | pas de clé API_FOOTBALL_KEY dans .env : étape ignorée")
    log.info("Collecte terminée en %.0f s, %d erreur(s)", time.monotonic() - debut, erreurs)
    return erreurs


def main():
    parser = argparse.ArgumentParser(description="Collecte Ligue 1 CI")
    parser.add_argument("--saison", choices=SAISONS, help="une saison (défaut : toutes)")
    parser.add_argument("--sans-personnes", action="store_true",
                        help="ne pas collecter les fiches joueurs/entraîneurs")
    parser.add_argument("--sans-api", action="store_true", help="ne pas appeler API-Football")
    parser.add_argument("--villes", action="store_true",
                        help="seulement les coordonnées des villes (carte)")
    args = parser.parse_args()
    if args.villes:
        creer_index()
        log.info("villes | %s", collecter_villes())
        return
    erreurs = collecter([args.saison] if args.saison else SAISONS,
                        not args.sans_personnes, not args.sans_api)
    raise SystemExit(1 if erreurs else 0)  # code d'erreur pour l'alerte GitHub Actions


if __name__ == "__main__":
    main()

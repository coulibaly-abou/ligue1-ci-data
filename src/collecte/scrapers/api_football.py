"""Client API-Football (https://www.api-football.com/documentation-v3).

API officielle avec clé : l'utilisation automatisée est prévue par le service.
L'offre gratuite donne 100 requêtes par jour : chaque réponse est gardée dans
MongoDB (raw_api) et réutilisée tant qu'elle est fraîche, pour économiser le quota.

    python -m src.collecte.scrapers.api_football   # vérifie la clé et la couverture
"""
import json
import time
from datetime import datetime, timezone

import requests
import truststore

from config.settings import API_FOOTBALL_KEY, DELAI_REQUETES
from src.stockage.mongo_client import get_db

truststore.inject_into_ssl()

BASE = "https://v3.football.api-sports.io"
ID_LIGUE = 386  # Ligue 1 ivoirienne
# L'offre gratuite n'ouvre que ces saisons (année de début : 2022 = 2022-2023)
SAISONS_GRATUITES = (2022, 2023, 2024)
DELAI_API = max(DELAI_REQUETES, 6.5)  # offre gratuite : 10 requêtes par minute
_restant: int | None = None  # requêtes restantes aujourd'hui (en-tête de l'API)


class CleAbsente(Exception):
    """API_FOOTBALL_KEY n'est pas renseignée dans le fichier .env."""


class QuotaEpuise(Exception):
    """Le quota journalier de l'offre gratuite est atteint."""


def _cle_cache(endpoint: str, params: dict) -> str:
    return endpoint + "?" + json.dumps(params, sort_keys=True)


def est_en_cache(endpoint: str, params: dict) -> bool:
    return get_db().raw_api.count_documents({"cle": _cle_cache(endpoint, params)}, limit=1) > 0


def appeler(endpoint: str, params: dict | None = None, max_jours: float = 7) -> dict:
    """GET sur l'API, avec cache MongoDB de max_jours (0 = toujours rappeler,
    float("inf") = ne jamais rappeler : pour les matchs terminés)."""
    global _restant
    if not API_FOOTBALL_KEY:
        raise CleAbsente("Renseigner API_FOOTBALL_KEY dans .env")
    params = params or {}
    cle = _cle_cache(endpoint, params)
    cache = get_db().raw_api.find_one({"cle": cle})
    if cache and max_jours > 0:
        age = datetime.now(timezone.utc) - cache["appele_le"].replace(tzinfo=timezone.utc)
        if age.total_seconds() < max_jours * 86400:
            return cache["reponse"]
    if _restant is not None and _restant <= 0:
        raise QuotaEpuise("quota journalier atteint")

    for _ in range(3):
        time.sleep(DELAI_API)
        reponse = requests.get(
            BASE + endpoint, params=params, timeout=30,
            headers={"x-apisports-key": API_FOOTBALL_KEY},
        )
        reponse.raise_for_status()
        restant = reponse.headers.get("x-ratelimit-requests-remaining")
        _restant = int(restant) if restant and restant.isdigit() else _restant
        donnees = reponse.json()
        erreurs = donnees.get("errors")
        if not erreurs:
            break
        # l'API renvoie 200 avec un champ "errors" : limite par minute, quota, plan...
        if isinstance(erreurs, dict) and "rateLimit" in erreurs:
            time.sleep(60)  # limite de 10 requêtes par minute : on attend et on réessaie
            continue
        texte = json.dumps(erreurs, ensure_ascii=False)
        if isinstance(erreurs, dict) and "requests" in erreurs:
            _restant = 0  # l'en-tête « remaining » n'est pas fiable une fois le quota atteint
            raise QuotaEpuise(texte)
        raise RuntimeError(texte)
    else:
        raise RuntimeError("limite par minute toujours atteinte après 3 essais")

    get_db().raw_api.update_one(
        {"cle": cle},
        {"$set": {"cle": cle, "endpoint": endpoint, "params": params, "reponse": donnees,
                  "appele_le": datetime.now(timezone.utc), "source": "api_football"}},
        upsert=True,
    )
    return donnees


def ligues_cote_divoire() -> list[dict]:
    """Compétitions ivoiriennes connues de l'API, avec la couverture par saison."""
    return appeler("/leagues", {"code": "CI"}, max_jours=30)["response"]


def verifier():
    """Affiche le quota restant et ce que l'API couvre pour la Ligue 1 ivoirienne."""
    statut = appeler("/status", max_jours=0)["response"]
    abonnement = statut.get("subscription", {})
    requetes = statut.get("requests", {})
    print(f"Compte : {statut.get('account', {}).get('email')} | plan {abonnement.get('plan')}")
    print(f"Requêtes aujourd'hui : {requetes.get('current')}/{requetes.get('limit_day')}")

    for ligue in ligues_cote_divoire():
        info = ligue["league"]
        print(f"\n[{info['id']}] {info['name']} ({info['type']})")
        for saison in ligue["seasons"]:
            c = saison["coverage"]
            f = c["fixtures"]
            print(f"  {saison['year']} | évènements:{f['events']} "
                  f"compos:{f['lineups']} effectifs/joueurs:{c['players']} "
                  f"buteurs:{c['top_scorers']} cartons:{c['top_cards']} "
                  f"classement:{c['standings']}")


# --- Collecte incrémentale --------------------------------------------------
# Les saisons 2022-2024 sont terminées : leurs réponses ne changent plus
# (cache permanent). Entraîneurs et transferts sont rafraîchis tous les 30 jours.
POUR_TOUJOURS = float("inf")
PAGES_MAX = 3  # limite de pagination de l'offre gratuite
CLASSEMENTS_JOUEURS = ("/players/topscorers", "/players/topassists",
                       "/players/topyellowcards", "/players/topredcards")


def _taches_saison(saison: int):
    """Requêtes « une par saison » : matchs, équipes, classements, palmarès joueurs."""
    base = {"league": ID_LIGUE, "season": saison}
    yield "/fixtures", base
    yield "/teams", base
    yield "/standings", base
    for endpoint in CLASSEMENTS_JOUEURS:
        yield endpoint, base


def collecter(log) -> dict:
    """Avance la collecte autant que le quota du jour le permet.

    Ordre de priorité : données par saison, joueurs (paginés), puis par équipe
    (entraîneurs, transferts), enfin les évènements match par match (le plus coûteux).
    Relancer chaque jour reprend là où on s'est arrêté.
    """
    bilan = {"appels_ok": 0, "deja_en_cache": 0, "erreurs": 0, "termine": False}

    def tenter(endpoint, params, max_jours=POUR_TOUJOURS):
        if est_en_cache(endpoint, params) and max_jours == POUR_TOUJOURS:
            bilan["deja_en_cache"] += 1
            return appeler(endpoint, params, max_jours)
        try:
            reponse = appeler(endpoint, params, max_jours)
            bilan["appels_ok"] += 1
            return reponse
        except QuotaEpuise:
            raise
        except Exception as exc:  # noqa: BLE001 — un appel en échec ne bloque pas les autres
            bilan["erreurs"] += 1
            log.error("api_football | %s %s | ÉCHEC : %s", endpoint, params, exc)
            return None

    try:
        equipes_par_saison, matchs_finis = {}, []
        for saison in SAISONS_GRATUITES:
            for endpoint, params in _taches_saison(saison):
                reponse = tenter(endpoint, params)
                if reponse and endpoint == "/teams":
                    equipes_par_saison[saison] = [e["team"]["id"] for e in reponse["response"]]
                if reponse and endpoint == "/fixtures":
                    matchs_finis += [m["fixture"]["id"] for m in reponse["response"]
                                     if m["fixture"]["status"]["short"] in ("FT", "AET", "PEN")]

        # Effectifs club par club (l'offre gratuite limite la pagination à 3 pages :
        # 60 joueurs par club suffisent, alors que 60 par ligue n'auraient pas suffi).
        for saison, equipes_saison in equipes_par_saison.items():
            for equipe in equipes_saison:
                page, total = 1, 1
                while page <= min(total, PAGES_MAX):
                    reponse = tenter("/players", {"team": equipe, "season": saison, "page": page})
                    if not reponse:
                        break
                    total = reponse.get("paging", {}).get("total", 1)
                    page += 1

        equipes = {e for liste in equipes_par_saison.values() for e in liste}

        for equipe in sorted(equipes):
            tenter("/coachs", {"team": equipe}, max_jours=30)
            tenter("/transfers", {"team": equipe}, max_jours=30)

        for match in matchs_finis:
            tenter("/fixtures/events", {"fixture": match})

        bilan["termine"] = True
    except QuotaEpuise:
        log.warning("api_football | quota du jour atteint : la suite au prochain lancement")
    bilan["requetes_restantes"] = _restant
    return bilan


if __name__ == "__main__":
    verifier()

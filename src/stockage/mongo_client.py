"""Accès à MongoDB : zone brute des données collectées."""
from datetime import datetime, timezone

from pymongo import MongoClient, UpdateOne

from config.settings import MONGO_DB, MONGO_URI

_client = None


def get_db():
    """Connexion unique, réutilisée par tout le projet."""
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    return _client[MONGO_DB]


def sauver_brut(collection: str, documents: list[dict], cle: list[str]) -> int:
    """Insère ou met à jour des documents sans créer de doublon.

    cle : champs qui identifient un document de façon unique,
          par ex. ["saison", "date", "equipe_dom", "equipe_ext"] pour un match.
    """
    if not documents:
        return 0

    maintenant = datetime.now(timezone.utc)
    operations = []
    for doc in documents:
        filtre = {champ: doc[champ] for champ in cle}
        doc = {**doc, "collecte_le": maintenant}
        operations.append(UpdateOne(filtre, {"$set": doc}, upsert=True))

    resultat = get_db()[collection].bulk_write(operations)
    return resultat.upserted_count + resultat.modified_count


# Champs qui identifient un document de façon unique, par collection.
# La source fait partie de la clé : RSSSF et Wikipédia sont gardés côte à côte,
# l'ETL choisira. raw_pages garde le HTML complet : on peut re-parser sans re-télécharger.
CLES = {
    "raw_pages": ["url"],
    "raw_matches": ["saison", "phase", "journee", "equipe_dom", "equipe_ext", "statut", "source"],
    "raw_fixtures": ["saison", "equipe_dom", "equipe_ext", "source"],
    "raw_standings": ["saison", "phase", "type_tableau", "groupe", "rang", "source"],
    "raw_clubs": ["saison", "club", "source"],
    "raw_scorers": ["saison", "joueur", "source"],
    "raw_persons": ["url"],
    "raw_api": ["cle"],  # réponses API-Football brutes (endpoint + paramètres)
    "raw_villes": ["ville"],  # coordonnées des villes (articles Wikipédia)
}
INDEX_SIMPLES = {
    "raw_pages": ["saison", "source"],
    "raw_persons": ["source", "passages.club"],
    "raw_api": ["endpoint", "appele_le"],
}


def sauver(collection: str, documents: list[dict]) -> int:
    """Upsert avec la clé définie dans CLES pour cette collection."""
    return sauver_brut(collection, documents, cle=CLES[collection])


def lire_page(url: str, max_jours: float) -> str | None:
    """HTML déjà archivé dans raw_pages s'il a moins de max_jours, sinon None."""
    doc = get_db().raw_pages.find_one({"url": url}, {"html": 1, "telecharge_le": 1})
    if not doc:
        return None
    age = datetime.now(timezone.utc) - doc["telecharge_le"].replace(tzinfo=timezone.utc)
    return doc["html"] if age.days < max_jours else None


def creer_index():
    """Index uniques (pas de doublon) + index de recherche sur saison et url."""
    db = get_db()
    for collection, cle in CLES.items():
        nom = "_".join(f"{champ}_1" for champ in cle)
        for ancien, info in db[collection].index_information().items():
            if info.get("unique") and ancien != nom:  # clé modifiée depuis la version précédente
                db[collection].drop_index(ancien)
        db[collection].create_index([(champ, 1) for champ in cle], unique=True, name=nom)
        for champ in INDEX_SIMPLES.get(collection, ["saison", "url_source"]):
            db[collection].create_index(champ)

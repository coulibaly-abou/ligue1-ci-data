"""Paramètres du projet, lus depuis le fichier .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

RACINE = Path(__file__).resolve().parent.parent
load_dotenv(RACINE / ".env")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "ligue1")
PG_URL = os.getenv("PG_URL")
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

DELAI_REQUETES = float(os.getenv("DELAI_REQUETES", "2"))
USER_AGENT = os.getenv("USER_AGENT", "ligue1-ci-data/0.1 (projet etudiant)")

# API-Football : offre gratuite limitée à 100 requêtes par jour
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY") or None
API_FOOTBALL_QUOTA_JOUR = int(os.getenv("API_FOOTBALL_QUOTA_JOUR", "100"))

# Saisons collectées : "2016-2017" ... "2026-2027" (saison en cours : Wikipédia seulement)
SAISONS = [f"{annee}-{annee + 1}" for annee in range(2016, 2027)]
SAISON_EN_COURS = SAISONS[-1]

DOSSIER_LOGS = RACINE / "logs"
FICHIER_ALIAS = RACINE / "config" / "clubs_alias.yml"
FICHIER_ALIAS_STADES = RACINE / "config" / "stades_alias.yml"

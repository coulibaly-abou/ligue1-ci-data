"""Chargement du graphe des carrières dans Neo4j, depuis PostgreSQL (schéma « ligue1 »).

Modèle :
    (:Personne)-[:A_JOUE_POUR | :FORME_A | :A_ENTRAINE {annee_debut, annee_fin, ...}]->(:Club)
    (:Club)-[:MOUVEMENT {annee, pret, source}]->(:Club)   mouvements de src/graphe/analyses.py

L'ETL recrée PostgreSQL (identifiants SERIAL renumérotés) : le graphe est donc vidé puis
rechargé entièrement à chaque exécution.  Lancement : python -m src.graphe.chargement_neo4j
"""
import sys
from collections.abc import Iterator, Sequence
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from config.settings import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER, RACINE
from src.graphe.analyses import SQL_PASSAGES, SQL_TRANSFERTS, mouvements
from src.utils.logs import get_logger

log = get_logger("graphe")

TAILLE_LOT = 1000
FICHIER_CONTRAINTES = RACINE / "cypher" / "contraintes.cypher"

# Rôle du passage (table ligue1.passage) -> type de relation ; 'selection' n'a pas de club
RELATION_PAR_ROLE = {"senior": "A_JOUE_POUR", "jeunes": "FORME_A", "entraineur": "A_ENTRAINE"}

SQL_CLUBS = """
SELECT c.nom, c.est_ligue1, v.nom AS ville
FROM ligue1.club c LEFT JOIN ligue1.ville v USING (id_ville)
"""

SQL_PERSONNES = """
SELECT id_personne, nom, nationalite, poste, est_joueur, est_entraineur
FROM ligue1.personne
"""

SQL_TOUS_PASSAGES = """
SELECT pa.id_personne, c.nom AS club, pa.role, pa.annee_debut, pa.annee_fin, pa.pret,
       pa.matchs, pa.buts
FROM ligue1.passage pa LEFT JOIN ligue1.club c USING (id_club)
"""

CYPHER_VIDER = "MATCH (n) CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 5000 ROWS"

CYPHER_CLUBS = """
UNWIND $lignes AS l
MERGE (c:Club {nom: l.nom})
SET c.est_ligue1 = l.est_ligue1, c.ville = l.ville
"""

CYPHER_PERSONNES = """
UNWIND $lignes AS l
MERGE (p:Personne {id_personne: l.id_personne})
SET p.nom = l.nom, p.nationalite = l.nationalite, p.poste = l.poste,
    p.est_joueur = l.est_joueur, p.est_entraineur = l.est_entraineur
"""

# Le type de relation ne peut pas être paramétré en Cypher : il vient de RELATION_PAR_ROLE
CYPHER_PASSAGES = """
UNWIND $lignes AS l
MATCH (p:Personne {{id_personne: l.id_personne}}), (c:Club {{nom: l.club}})
CREATE (p)-[:{relation} {{annee_debut: l.annee_debut, annee_fin: l.annee_fin, pret: l.pret,
                          matchs: l.matchs, buts: l.buts}}]->(c)
"""

CYPHER_MOUVEMENTS = """
UNWIND $lignes AS l
MATCH (a:Club {nom: l.depart}), (b:Club {nom: l.arrivee})
CREATE (a)-[:MOUVEMENT {annee: l.annee, pret: l.pret, source: l.source}]->(b)
"""


class ConnexionImpossible(Exception):
    """Neo4j injoignable ou identifiants refusés."""


# ------------------------------------------------------------ préparation (pure)

def valeur_propre(valeur: object) -> object:
    """Convertit une cellule pandas en valeur acceptée par le driver Neo4j."""
    if valeur is None or valeur is pd.NA or valeur is pd.NaT:
        return None
    if isinstance(valeur, float) and pd.isna(valeur):
        return None
    if isinstance(valeur, (pd.Timestamp, datetime, date)):
        return valeur.strftime("%Y-%m-%d")
    if hasattr(valeur, "item"):  # types numpy -> int, float, bool Python
        valeur = valeur.item()
    if isinstance(valeur, float) and valeur.is_integer():  # colonnes entières avec des NaN
        return int(valeur)
    return valeur


def _lignes(df: pd.DataFrame, colonnes: Sequence[str]) -> list[dict]:
    return [{col: valeur_propre(val) for col, val in zip(colonnes, ligne)}
            for ligne in df[list(colonnes)].itertuples(index=False, name=None)]


def noeuds_clubs(clubs: pd.DataFrame) -> list[dict]:
    return _lignes(clubs, ["nom", "est_ligue1", "ville"])


def noeuds_personnes(personnes: pd.DataFrame) -> list[dict]:
    return _lignes(personnes, ["id_personne", "nom", "nationalite", "poste", "est_joueur",
                               "est_entraineur"])


def relations_passages(passages: pd.DataFrame) -> dict[str, list[dict]]:
    """Passages avec un club connu, regroupés par type de relation Neo4j."""
    colonnes = ["id_personne", "club", "annee_debut", "annee_fin", "pret", "matchs", "buts"]
    avec_club = passages[passages["club"].notna() & passages["role"].isin(RELATION_PAR_ROLE)]
    return {RELATION_PAR_ROLE[role]: _lignes(groupe, colonnes)
            for role, groupe in avec_club.groupby("role", sort=False)}


def relations_mouvements(mvts: pd.DataFrame) -> list[dict]:
    lignes = _lignes(mvts, ["depart", "arrivee", "annee", "pret", "source"])
    return [{**ligne, "pret": bool(ligne["pret"])} for ligne in lignes]


def en_lots(lignes: Sequence, taille: int) -> Iterator[list]:
    if taille <= 0:
        raise ValueError(f"taille de lot invalide : {taille}")
    for debut in range(0, len(lignes), taille):
        yield list(lignes[debut:debut + taille])


def instructions_cypher(chemin: Path) -> list[str]:
    """Instructions d'un fichier .cypher (séparées par « ; », commentaires // retirés)."""
    sans_commentaires = "\n".join(ligne for ligne in chemin.read_text(encoding="utf-8")
                                  .splitlines() if not ligne.strip().startswith("//"))
    return [i.strip() for i in sans_commentaires.split(";") if i.strip()]


# ------------------------------------------------------------------ chargement

def ouvrir_driver():
    """Driver Neo4j vérifié ; import local : le paquet neo4j est optionnel (extra « graphe »)."""
    if not (NEO4J_URI and NEO4J_USER and NEO4J_PASSWORD):
        raise ConnexionImpossible("NEO4J_URI, NEO4J_USER et NEO4J_PASSWORD doivent être "
                                  "définis dans .env (voir .env.example).")
    try:
        from neo4j import GraphDatabase
        from neo4j.exceptions import DriverError, Neo4jError
    except ImportError as exc:
        raise ConnexionImpossible("Paquet neo4j absent : pip install -e \".[graphe]\"") from exc

    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    except (DriverError, ValueError) as exc:
        raise ConnexionImpossible(f"NEO4J_URI invalide : {NEO4J_URI}") from exc
    try:
        driver.verify_connectivity()
    except (DriverError, Neo4jError) as exc:
        driver.close()
        raise ConnexionImpossible(
            f"Connexion à Neo4j refusée ({NEO4J_URI}). Vérifier les identifiants NEO4J_* "
            "dans .env et que le conteneur tourne (docker compose up -d neo4j).") from exc
    return driver


def _ecrire(driver, cypher: str, lignes: list[dict], quoi: str) -> None:
    for lot in en_lots(lignes, TAILLE_LOT):
        driver.execute_query(cypher, lignes=lot)
    log.info("%s : %d", quoi, len(lignes))


def charger_graphe(driver, clubs: pd.DataFrame, personnes: pd.DataFrame,
                   passages: pd.DataFrame, mvts: pd.DataFrame) -> None:
    with driver.session() as session:  # CALL ... IN TRANSACTIONS exige une transaction auto
        session.run(CYPHER_VIDER).consume()
    for instruction in instructions_cypher(FICHIER_CONTRAINTES):
        driver.execute_query(instruction)
    _ecrire(driver, CYPHER_CLUBS, noeuds_clubs(clubs), "clubs")
    _ecrire(driver, CYPHER_PERSONNES, noeuds_personnes(personnes), "personnes")
    for relation, lignes in relations_passages(passages).items():
        _ecrire(driver, CYPHER_PASSAGES.format(relation=relation), lignes, relation)
    _ecrire(driver, CYPHER_MOUVEMENTS, relations_mouvements(mvts), "MOUVEMENT")


def verifier_sources(**tables: pd.DataFrame) -> None:
    """Refuse de vider Neo4j si PostgreSQL n'a rien à charger (ETL non lancé ou en échec)."""
    vides = [nom for nom, df in tables.items() if df.empty]
    if vides:
        raise ValueError(f"Tables PostgreSQL vides : {', '.join(vides)} ; lancer make etl.")


def compter(driver) -> dict[str, int]:
    enregistrements, _, _ = driver.execute_query(
        "MATCH (n) RETURN 'noeuds' AS quoi, count(n) AS nb "
        "UNION ALL MATCH ()-[r]->() RETURN 'relations' AS quoi, count(r) AS nb")
    return {e["quoi"]: e["nb"] for e in enregistrements}


def main() -> int:
    from src.stockage.postgres_client import lire

    try:
        driver = ouvrir_driver()  # avant PostgreSQL : échoue vite si Neo4j est absent
    except ConnexionImpossible as exc:
        log.error("%s", exc)
        return 1
    try:
        clubs, personnes = lire(SQL_CLUBS), lire(SQL_PERSONNES)
        passages = lire(SQL_TOUS_PASSAGES)
        verifier_sources(clubs=clubs, personnes=personnes, passages=passages)
        mvts = mouvements(lire(SQL_PASSAGES), lire(SQL_TRANSFERTS))
        charger_graphe(driver, clubs, personnes, passages, mvts)
        log.info("Graphe Neo4j chargé : %s", compter(driver))
    finally:
        driver.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

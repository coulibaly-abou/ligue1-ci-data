"""Exécute les 5 requêtes Cypher de cypher/requetes/ sur le graphe chargé dans Neo4j.

Lancement : python -m src.graphe.requetes   (après python -m src.graphe.chargement_neo4j)
Chaque requête doit renvoyer au moins une ligne : sinon le script s'arrête en erreur.
"""
import re
import sys
from pathlib import Path

import pandas as pd

from config.settings import RACINE
from src.graphe.chargement_neo4j import ConnexionImpossible, ouvrir_driver
from src.utils.logs import get_logger

log = get_logger("graphe")

DOSSIER_REQUETES = RACINE / "cypher" / "requetes"

# Valeurs d'exemple des paramètres $... utilisés par les requêtes
PARAMETRES_DEFAUT = {
    "joueur": "Serge Wawa",
    "club_depart": "ASEC Mimosas",
    "club_arrivee": "Africa Sports",
    "depuis": 2010,
}

_PARAMETRE = re.compile(r"\$([A-Za-z_]\w*)")


def fichiers_requetes() -> list[Path]:
    return sorted(DOSSIER_REQUETES.glob("*.cypher"))


def parametres_requis(texte: str) -> set[str]:
    """Paramètres $nom employés hors des commentaires // d'une requête."""
    code = "\n".join(ligne for ligne in texte.splitlines()
                     if not ligne.strip().startswith("//"))
    return set(_PARAMETRE.findall(code))


def executer(driver, fichier: Path, parametres: dict) -> pd.DataFrame:
    texte = fichier.read_text(encoding="utf-8")
    utiles = {nom: parametres[nom] for nom in parametres_requis(texte)}
    from neo4j import RoutingControl

    enregistrements, _, cles = driver.execute_query(texte.strip().rstrip(";"), utiles,
                                                    routing_=RoutingControl.READ)
    return pd.DataFrame([dict(e) for e in enregistrements], columns=cles)


def main() -> int:
    try:
        driver = ouvrir_driver()
    except ConnexionImpossible as exc:
        log.error("%s", exc)
        return 1
    vides = []
    try:
        for fichier in fichiers_requetes():
            resultat = executer(driver, fichier, PARAMETRES_DEFAUT)
            log.info("%s : %d ligne(s)\n%s", fichier.name, len(resultat),
                     resultat.head(10).to_string(index=False))
            if resultat.empty:
                vides.append(fichier.name)
    finally:
        driver.close()
    if vides:
        log.error("Requêtes sans résultat : %s", ", ".join(vides))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""ETL MongoDB (zone brute) -> PostgreSQL (modèle relationnel issu du MCD/MLD).

    python -m src.etl.run

Rechargement complet à chaque exécution : le schéma « ligue1 » est recréé
(sql/schema.sql, MPD), puis toutes les tables sont reconstruites depuis MongoDB.
Modèle : docs/modele_donnees.md (MCD, MLD).
Les anomalies détectées sont écrites dans logs/anomalies_etl.csv.
"""
import time

import pandas as pd

from config.settings import DOSSIER_LOGS, RACINE
from src.etl.transformation import construire_tout
from src.stockage.mongo_client import get_db
from src.stockage.postgres_client import (
    ConnexionImpossible,
    charger,
    creer_base_si_absente,
    executer_fichier,
)
from src.utils.logs import get_logger

log = get_logger("etl")
FICHIER_SCHEMA = RACINE / "sql" / "schema.sql"
FICHIER_VUES = RACINE / "sql" / "vues_materialisees.sql"


def main() -> None:
    debut = time.monotonic()
    tables, ctx = construire_tout(get_db())
    log.info("Transformation : %s", {nom: len(df) for nom, df in tables.items()})

    anomalies = pd.DataFrame(ctx.anomalies, columns=["table", "description", "detail"])
    DOSSIER_LOGS.mkdir(exist_ok=True)
    anomalies.to_csv(DOSSIER_LOGS / "anomalies_etl.csv", index=False, encoding="utf-8-sig")
    log.info("%d anomalie(s) -> logs/anomalies_etl.csv", len(anomalies))

    try:
        creer_base_si_absente()
        executer_fichier(FICHIER_SCHEMA)
        for nom, df in tables.items():  # ordre : dimensions puis faits (clés étrangères)
            log.info("Chargement %-20s %6d lignes", nom, charger(df, nom))
        if FICHIER_VUES.exists() and FICHIER_VUES.read_text(encoding="utf-8").strip():
            executer_fichier(FICHIER_VUES)
            log.info("Vues matérialisées créées")
    except ConnexionImpossible as exc:
        log.error("%s", exc)
        raise SystemExit(1) from exc
    log.info("ETL terminé en %.0f s", time.monotonic() - debut)


if __name__ == "__main__":
    main()

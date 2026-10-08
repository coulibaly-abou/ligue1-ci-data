"""Export des données du tableau de bord : PostgreSQL + résultats du modèle -> app/data/.

    python -m src.restitution.export        # ou : make export

L'application Streamlit ne lit que ces fichiers Parquet : elle peut ainsi être
déployée en ligne (Streamlit Community Cloud) sans exposer les bases de données.
"""
import json
import shutil

import pandas as pd
import yaml

from config.settings import FICHIER_ALIAS, RACINE
from src.graphe import analyses as graphe
from src.stockage.postgres_client import lire
from src.utils.logs import get_logger

log = get_logger("export")
DOSSIER = RACINE / "app" / "data"
RESULTATS = RACINE / "docs" / "resultats"

REQUETES = {
    "matchs": """
        SELECT m.id_match, m.id_saison, s.libelle AS saison, m.phase, m.journee,
               m.date_match, m.statut, d.nom AS dom, x.nom AS ext, m.buts_dom, m.buts_ext,
               m.resultat, st.nom AS stade
        FROM ligue1.v_match m
        JOIN ligue1.saison s USING (id_saison)
        JOIN ligue1.club d ON d.id_club = m.id_club_dom
        JOIN ligue1.club x ON x.id_club = m.id_club_ext
        LEFT JOIN ligue1.stade st ON st.id_stade = m.id_stade""",
    "resultats_club": """
        SELECT r.id_match, r.id_saison, s.libelle AS saison, r.date_match, r.a_domicile,
               k.nom AS club, a.nom AS adversaire, r.bp, r.bc, r.points, r.issue,
               r.journee_club
        FROM ligue1.mv_resultat_club r
        JOIN ligue1.saison s USING (id_saison)
        JOIN ligue1.club k USING (id_club)
        JOIN ligue1.club a ON a.id_club = r.id_adversaire""",
    "classement_journee": """
        SELECT c.id_saison, s.libelle AS saison, k.nom AS club, c.journee, c.points,
               c.difference, c.buts_pour, c.rang
        FROM ligue1.mv_classement_journee c
        JOIN ligue1.saison s USING (id_saison)
        JOIN ligue1.club k USING (id_club)""",
    "saisons": "SELECT * FROM ligue1.saison ORDER BY id_saison",
    "clubs": """
        SELECT k.nom AS club, v.nom AS ville, v.latitude::float AS lat,
               v.longitude::float AS lon, v.url_coordonnees, st.nom AS stade, st.capacite
        FROM ligue1.club k
        LEFT JOIN ligue1.ville v USING (id_ville)
        LEFT JOIN ligue1.stade st ON st.id_stade = k.id_stade
        WHERE k.est_ligue1""",
    "buteurs": """
        SELECT DISTINCT ON (b.id_saison, b.joueur) s.libelle AS saison, b.joueur,
               k.nom AS club, b.buts, b.matchs, b.source
        FROM ligue1.stat_buteur b
        JOIN ligue1.saison s USING (id_saison)
        LEFT JOIN ligue1.club k USING (id_club)
        ORDER BY b.id_saison, b.joueur, b.buts DESC""",
}
FICHIERS_SQL = {"palmares": "08_palmares.sql", "series": "04_series_invincibilite.sql",
                "scores": "07_scores_frequents.sql",
                "resultats_saison": "06_resultats_par_saison.sql"}


def _sauver(df: pd.DataFrame, nom: str) -> None:
    df.to_parquet(DOSSIER / f"{nom}.parquet", index=False)
    log.info("%-22s %6d lignes", nom, len(df))


def exporter_bases() -> None:
    for nom, sql in REQUETES.items():
        _sauver(lire(sql), nom)
    for nom, fichier in FICHIERS_SQL.items():
        _sauver(lire((RACINE / "sql" / "analyses" / fichier).read_text(encoding="utf-8")), nom)


def exporter_reseau() -> None:
    mvts = graphe.mouvements(lire(graphe.SQL_PASSAGES), lire(graphe.SQL_TRANSFERTS))
    g = graphe.construire_graphe(mvts)
    noeuds = graphe.indicateurs(g)
    # Sous-graphe affiché : clubs de Ligue 1 + 25 destinations les plus centrales
    affiches = set(noeuds.loc[noeuds["ligue1"], "club"]) | \
        set(noeuds.loc[~noeuds["ligue1"], "club"].head(25))
    pos = graphe.positions(g, list(affiches))
    noeuds["x"] = noeuds["club"].map(lambda n: pos.get(n, (None, None))[0])
    noeuds["y"] = noeuds["club"].map(lambda n: pos.get(n, (None, None))[1])
    aretes = mvts.groupby(["depart", "arrivee"]).size().reset_index(name="poids")
    _sauver(mvts, "reseau_mouvements")
    _sauver(noeuds, "reseau_noeuds")
    _sauver(aretes, "reseau_aretes")


def exporter_modele() -> None:
    """Copie les résultats de src.modele.entrainement (lancer make train avant)."""
    cible = DOSSIER / "modele"
    cible.mkdir(exist_ok=True)
    if not (RESULTATS / "metriques.json").exists():
        log.warning("Pas de résultats de modèle : lancer d'abord python -m src.modele.entrainement")
        return
    for f in RESULTATS.glob("*.csv"):
        if f.name == "jeu_features.csv":
            continue
        pd.read_csv(f).to_parquet(cible / f"{f.stem}.parquet", index=False)
    shutil.copy(RESULTATS / "metriques.json", cible / "metriques.json")
    log.info("Résultats du modèle copiés (%s)",
             json.loads((RESULTATS / "metriques.json").read_text(encoding="utf-8"))
             ["modele_retenu"])


def exporter_sources() -> None:
    """Volumes réels de la zone brute MongoDB, par collection et par source."""
    from src.stockage.mongo_client import get_db

    db = get_db()
    volumes = {}
    for nom in sorted(db.list_collection_names()):
        sources = {} if nom == "raw_pages" else {
            s: db[nom].count_documents({"source": s}) for s in db[nom].distinct("source")}
        volumes[nom] = {"documents": db[nom].estimated_document_count(), "sources": sources}
    derniere = db.raw_pages.find_one(sort=[("telecharge_le", -1)], projection={"telecharge_le": 1})
    infos = {"collections": volumes,
             "derniere_collecte": derniere["telecharge_le"].isoformat() if derniere else None,
             "villes_geolocalisees": db.raw_villes.count_documents({"statut": "ok"})}
    anomalies = RACINE / "logs" / "anomalies_etl.csv"
    if anomalies.exists():
        infos["anomalies_etl"] = (pd.read_csv(anomalies, encoding="utf-8-sig")
                                  .groupby("description").size().to_dict())
    alias = yaml.safe_load(FICHIER_ALIAS.read_text(encoding="utf-8"))
    infos["alias_clubs"] = {"clubs": len(alias),
                            "variantes": sum(len(v or []) for v in alias.values())}
    (DOSSIER / "sources.json").write_text(json.dumps(infos, indent=2, ensure_ascii=False),
                                          encoding="utf-8")
    log.info("sources.json : %d collections", len(volumes))


def main() -> None:
    DOSSIER.mkdir(parents=True, exist_ok=True)
    exporter_sources()
    exporter_bases()
    exporter_reseau()
    exporter_modele()


if __name__ == "__main__":
    main()

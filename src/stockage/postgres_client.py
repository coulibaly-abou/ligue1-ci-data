"""Accès à PostgreSQL : zone analytique (modèle relationnel, schéma « ligue1 »)."""
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import OperationalError

from config.settings import PG_URL

SCHEMA = "ligue1"
_engine = None


class ConnexionImpossible(Exception):
    """PostgreSQL injoignable ou identifiants refusés."""


def _creer_engine(url) -> Engine:
    url = make_url(url)
    if url.drivername == "postgresql":  # SQLAlchemy 2.1 choisirait psycopg 3 par défaut
        url = url.set(drivername="postgresql+psycopg2")
    return create_engine(url, pool_pre_ping=True)


def _verifier(engine: Engine) -> None:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except (OperationalError, UnicodeDecodeError) as exc:
        # Avec un serveur en français, le message d'erreur (accents) ne se décode pas
        raise ConnexionImpossible(
            f"Connexion à PostgreSQL refusée ({make_url(PG_URL).render_as_string()}). "
            "Vérifier PG_URL / PG_PASSWORD dans .env et que le service tourne."
        ) from exc


def creer_base_si_absente() -> None:
    """Crée la base indiquée dans PG_URL si elle n'existe pas encore."""
    url = make_url(PG_URL)
    admin = _creer_engine(url.set(database="postgres"))
    _verifier(admin)
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        existe = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :nom"),
                              {"nom": url.database}).scalar()
        if not existe:
            conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    admin.dispose()


def get_engine() -> Engine:
    """Connexion unique, réutilisée par tout le projet."""
    global _engine
    if _engine is None:
        if not PG_URL:
            raise ConnexionImpossible("PG_URL manquant dans .env")
        _engine = _creer_engine(PG_URL)
        _verifier(_engine)
    return _engine


def executer_fichier(chemin: Path) -> None:
    """Exécute un script SQL complet (plusieurs instructions)."""
    sql = Path(chemin).read_text(encoding="utf-8")
    with get_engine().begin() as conn:
        conn.exec_driver_sql(sql)


def _entiers(df: pd.DataFrame) -> pd.DataFrame:
    """Colonnes décimales qui ne contiennent que des entiers -> Int64 (NaN -> NULL)."""
    df = df.copy()
    for col in df.select_dtypes("float").columns:
        valeurs = df[col].dropna()
        if (valeurs == valeurs.round()).all():
            df[col] = df[col].astype("Int64")
    return df


def charger(df: pd.DataFrame, table: str) -> int:
    """Ajoute les lignes d'un DataFrame dans une table existante du schéma."""
    if df.empty:
        return 0
    with get_engine().begin() as conn:
        _entiers(df).to_sql(table, conn, schema=SCHEMA, if_exists="append", index=False,
                            method="multi", chunksize=1000)
        # les id ont été fixés en Python : on recale les séquences SERIAL
        colonne_id = conn.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_schema = :s "
            "AND table_name = :t AND column_default LIKE 'nextval%'"),
            {"s": SCHEMA, "t": table}).scalar()
        if colonne_id and colonne_id in df.columns:
            conn.execute(text(
                f"SELECT setval(pg_get_serial_sequence('{SCHEMA}.{table}', '{colonne_id}'), "
                f"(SELECT COALESCE(MAX({colonne_id}), 1) FROM {SCHEMA}.{table}))"))
    return len(df)


def lire(sql: str, **params) -> pd.DataFrame:
    with get_engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)

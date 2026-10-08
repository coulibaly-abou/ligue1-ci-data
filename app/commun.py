"""Fonctions partagées par les pages : chargement des données, couleurs, mise en forme."""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

DATA = Path(__file__).parent / "data"

# Palette validée (contraste ≥ 3:1, séparation daltonisme) : orange = domicile,
# vert = extérieur, gris neutre = nul ; brique = défaite (toujours avec une lettre / un %)
ORANGE, VERT, GRIS, ROUGE = "#E07000", "#006B45", "#9A9A94", "#B8322A"
COULEURS_RESULTAT = {"D": ORANGE, "N": GRIS, "E": VERT}
LIBELLES_RESULTAT = {"D": "Victoire domicile", "N": "Nul", "E": "Victoire extérieur"}
NOMS_MODELES = {"naif": "Référence naïve", "elo": "Elo", "logreg": "Régression logistique",
                "foret": "Forêt aléatoire", "boosting": "Gradient boosting",
                "mlp": "Réseau de neurones"}
SOURCES = ("Données : RSSSF, Wikipédia (CC BY-SA), Futbol24, API-Football · "
           "projet ligue1-ci-data")


@st.cache_data
def charger(nom: str) -> pd.DataFrame:
    return pd.read_parquet(DATA / f"{nom}.parquet")


@st.cache_data
def charger_modele(nom: str) -> pd.DataFrame | None:
    chemin = DATA / "modele" / f"{nom}.parquet"
    return pd.read_parquet(chemin) if chemin.exists() else None


@st.cache_data
def metriques() -> dict | None:
    chemin = DATA / "modele" / "metriques.json"
    return json.loads(chemin.read_text(encoding="utf-8")) if chemin.exists() else None


def configurer() -> None:
    """Styles communs (la configuration de la page est faite une fois dans Accueil.py)."""
    st.markdown("""<style>
        .block-container {padding-top: 2rem;}
        div[data-testid="stMetricValue"] {font-size: 1.8rem;}
        .serie span {display:inline-block; width:1.6rem; height:1.6rem; line-height:1.6rem;
                     margin-right:.2rem; border-radius:.3rem; text-align:center;
                     color:white; font-weight:700; font-size:.8rem;}
    </style>""", unsafe_allow_html=True)


def pied_de_page() -> None:
    st.divider()
    st.caption(SOURCES)


def serie_html(issues: list[str]) -> str:
    """Pastilles V / N / D colorées pour une série de résultats."""
    couleurs = {"V": VERT, "N": GRIS, "D": ROUGE}
    pastilles = "".join(f'<span style="background:{couleurs[i]}">{i}</span>' for i in issues)
    return f'<div class="serie">{pastilles}</div>'


def classement_final(classement_journee: pd.DataFrame, saison: str) -> pd.DataFrame:
    """Dernière ligne de chaque club pour la saison (classement recalculé)."""
    c = classement_journee[classement_journee["saison"] == saison]
    derniere = c.sort_values("journee").groupby("club").tail(1)
    derniere = derniere.sort_values(["points", "difference", "buts_pour"], ascending=False)
    derniere.insert(0, "rang_final", range(1, len(derniere) + 1))
    return derniere

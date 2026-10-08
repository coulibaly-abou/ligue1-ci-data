"""Fonctions partagées par les pages : chargement des données, couleurs, mise en forme."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DATA = Path(__file__).parent / "data"
FIGURES = Path(__file__).parent.parent / "docs" / "figures"

AUTEUR, ROLE = "COULIBALY ABOUBAKAR", "Data Scientist"
TITRE_PROJET = "Ligue 1 Côte d'Ivoire — Data Science & Machine Learning"

# Palette validée (contraste ≥ 3:1, séparation daltonisme) : orange = domicile,
# vert = extérieur, gris neutre = nul ; brique = défaite (toujours avec une lettre / un %)
ORANGE, VERT, GRIS, ROUGE = "#E07000", "#006B45", "#9A9A94", "#B8322A"
ENCRE, ENCRE_2, LIGNE = "#14211B", "#57606A", "#E6E8EB"
COULEURS_RESULTAT = {"D": ORANGE, "N": GRIS, "E": VERT}
LIBELLES_RESULTAT = {"D": "Victoire domicile", "N": "Nul", "E": "Victoire extérieur"}
NOMS_MODELES = {"naif": "Référence naïve", "elo": "Elo", "logreg": "Régression logistique",
                "foret": "Forêt aléatoire", "boosting": "Gradient boosting",
                "mlp": "Réseau de neurones"}
SOURCES = "Données : RSSSF, Wikipédia (CC BY-SA), Futbol24, API-Football"

PAGES = {  # chemin -> (titre, icône Material) ; partagé par la navigation et les liens
    "vues/accueil.py": ("Accueil", ":material/home:"),
    "vues/championnat.py": ("Championnat", ":material/emoji_events:"),
    "vues/club.py": ("Clubs", ":material/shield:"),
    "vues/reseau.py": ("Réseau", ":material/hub:"),
    "vues/prediction.py": ("Prédiction", ":material/online_prediction:"),
    "vues/modeles.py": ("Modèles", ":material/model_training:"),
    "vues/methodologie.py": ("Données & Méthodologie", ":material/database:"),
}

CSS = f"""<style>
.block-container {{padding-top: 1.6rem; max-width: 1320px;}}
div[data-testid="stMetricValue"] {{font-size: 1.8rem;}}
h1, h2, h3 {{color: {ENCRE}; letter-spacing: -0.01em;}}
.serie span {{display:inline-block; width:1.6rem; height:1.6rem; line-height:1.6rem;
             margin-right:.2rem; border-radius:.3rem; text-align:center;
             color:white; font-weight:700; font-size:.8rem;}}
.hero {{position:relative; overflow:hidden; border-radius:18px; padding:46px 52px 40px;
       background: radial-gradient(circle at 85% 20%, rgba(224,112,0,.22), transparent 42%),
                   linear-gradient(135deg, #0E2A1E 0%, #14211B 55%, #1B2621 100%);
       color:#FFFFFF; margin-bottom: 1.2rem;}}
.hero .barre {{position:absolute; bottom:0; left:0; right:0; height:6px;
              background: linear-gradient(90deg, {ORANGE} 0 33.3%, #FFFFFF 33.3% 66.6%,
                                          {VERT} 66.6% 100%);}}
.hero .auteur {{font-size:.95rem; font-weight:700; letter-spacing:.22em;}}
.hero .role {{font-size:.95rem; color:#F5A04A; font-weight:600; letter-spacing:.08em;
             margin-top:.1rem;}}
.hero .titre {{font-size:3.1rem; font-weight:800; line-height:1.05; margin:1.6rem 0 .5rem;
              letter-spacing:.01em;}}
.hero .tag {{font-size:1.05rem; color:#C8D3CD; letter-spacing:.28em; text-transform:uppercase;}}
.hero .accroche {{font-size:1.08rem; color:#E4EAE6; max-width:760px; margin-top:1.2rem;
                 line-height:1.55;}}
.surtitre {{font-size:.78rem; font-weight:700; letter-spacing:.18em; color:{ORANGE};
           text-transform:uppercase; margin:2.4rem 0 .1rem;}}
.titre-section {{font-size:1.75rem; font-weight:750; color:{ENCRE}; margin:0 0 .35rem;}}
.chapo {{color:{ENCRE_2}; font-size:1.05rem; margin-bottom:1rem;}}
.carte-axe {{border:1px solid {LIGNE}; border-radius:14px; padding:18px 18px 14px;
            background:#FFFFFF; height:100%; min-height:132px;}}
.carte-axe .num {{color:{ORANGE}; font-weight:800; font-size:.95rem; letter-spacing:.06em;}}
.carte-axe .nom {{color:{ENCRE}; font-weight:700; font-size:1.02rem; margin:.25rem 0 .3rem;}}
.carte-axe .txt {{color:{ENCRE_2}; font-size:.9rem; line-height:1.4;}}
.kpi {{border-left:4px solid {ORANGE}; background:#FBF8F4; border-radius:10px;
      padding:14px 18px; height:100%;}}
.kpi .val {{font-size:2.1rem; font-weight:800; color:{ENCRE}; line-height:1.1;}}
.kpi .lib {{font-size:.88rem; color:{ENCRE_2}; margin-top:.2rem;}}
.pied {{display:flex; justify-content:space-between; flex-wrap:wrap; gap:.5rem;
       color:{ENCRE_2}; font-size:.82rem; border-top:1px solid {LIGNE};
       padding-top:.9rem; margin-top:2.5rem;}}
.pied b {{color:{ENCRE}; letter-spacing:.08em;}}
.marque {{padding:.2rem 0 .8rem; border-bottom:1px solid {LIGNE}; margin-bottom:.4rem;}}
.marque .n {{font-weight:800; letter-spacing:.14em; font-size:.85rem; color:{ENCRE};}}
.marque .r {{color:{ORANGE}; font-weight:600; font-size:.85rem;}}
.marque .p {{color:{ENCRE_2}; font-size:.78rem; margin-top:.25rem;}}
</style>"""


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


@st.cache_data
def lire_json(nom: str) -> dict | None:
    chemin = DATA / f"{nom}.json"
    return json.loads(chemin.read_text(encoding="utf-8")) if chemin.exists() else None


def configurer() -> None:
    """Styles communs (la configuration de la page est faite une fois dans Accueil.py)."""
    st.markdown(CSS, unsafe_allow_html=True)


def entete(titre: str, sous_titre: str) -> None:
    """Titre de page + phrase qui dit à quoi sert la page."""
    st.title(titre)
    st.markdown(f"<p class='chapo'>{sous_titre}</p>", unsafe_allow_html=True)


def section(surtitre: str, titre: str, chapo: str | None = None) -> None:
    html = f"<div class='surtitre'>{surtitre}</div><div class='titre-section'>{titre}</div>"
    if chapo:
        html += f"<p class='chapo'>{chapo}</p>"
    st.markdown(html, unsafe_allow_html=True)


def kpis(valeurs: list[tuple[str, str]]) -> None:
    for col, (val, lib) in zip(st.columns(len(valeurs)), valeurs, strict=True):
        col.markdown(f"<div class='kpi'><div class='val'>{val}</div>"
                     f"<div class='lib'>{lib}</div></div>", unsafe_allow_html=True)


def pied_de_page() -> None:
    st.markdown(f"<div class='pied'><span><b>{AUTEUR}</b> · {ROLE}</span>"
                f"<span>{TITRE_PROJET}</span><span>{SOURCES}</span></div>",
                unsafe_allow_html=True)


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


# --------------------------------------------------------------------- carte
# Position des étiquettes (lisibilité seulement : les points restent aux coordonnées réelles)
POSITION_ETIQUETTE = {"Abidjan": "bottom center", "Abobo": "top left",
                      "Grand-Bassam": "bottom right", "Adiaké": "middle right",
                      "Agboville": "middle left", "Akoupé": "middle left",
                      "Ferkessédougou": "middle right", "Korhogo": "middle left"}


def villes_carte(clubs: pd.DataFrame, resultats: pd.DataFrame) -> pd.DataFrame:
    """Une ligne par ville : coordonnées collectées, clubs, matchs disputés dans les données."""
    matchs = resultats.groupby("club").size()
    saisons = resultats.groupby("club")["saison"].nunique()
    c = clubs.dropna(subset=["lat", "lon"]).copy()
    c["matchs"] = c["club"].map(matchs).fillna(0).astype(int)
    c["saisons"] = c["club"].map(saisons).fillna(0).astype(int)
    c = c.sort_values("matchs", ascending=False)
    c["ligne"] = c.apply(lambda r: f"{r['club']} — {r['matchs']} matchs, "
                                   f"{r['saisons']} saison(s)", axis=1)
    return c.groupby(["ville", "lat", "lon"]).agg(
        n_clubs=("club", "size"), matchs=("matchs", "sum"),
        detail=("ligne", lambda s: "<br>".join(s))).reset_index()


def carte_clubs(villes: pd.DataFrame, hauteur: int = 640, etiquettes: bool = True
                ) -> go.Figure:
    """Carte de la Côte d'Ivoire (géométrie pays intégrée à Plotly) et villes des clubs.

    Le cadrage est celui du territoire ivoirien (même emprise que le contrôle des
    coordonnées à la collecte) : il ne bouge pas quand on n'affiche qu'une partie des
    villes (apparition progressive dans la vidéo).
    """
    fig = go.Figure()
    fig.add_choropleth(locations=["CIV"], z=[1], locationmode="ISO-3", showscale=False,
                       colorscale=[[0, "#F3EEE6"], [1, "#F3EEE6"]], hoverinfo="skip",
                       marker_line={"color": "#B9AD9A", "width": 1.4})
    fig.add_scattergeo(
        lat=villes["lat"], lon=villes["lon"], mode="markers+text" if etiquettes else "markers",
        text=villes["ville"], textfont={"size": 13, "color": ENCRE},
        textposition=[POSITION_ETIQUETTE.get(v, "top center") for v in villes["ville"]],
        marker={"size": 11 + 7 * np.sqrt(villes["n_clubs"]), "color": ORANGE, "opacity": .92,
                "line": {"color": "white", "width": 2}},
        customdata=np.stack([villes["n_clubs"], villes["matchs"], villes["detail"]], axis=-1),
        hovertemplate="<b>%{text}</b><br>%{customdata[0]} club(s) · %{customdata[1]} "
                      "matchs dans les données<br><br>%{customdata[2]}<extra></extra>")
    fig.update_geos(
        projection_type="mercator", resolution=50, showcountries=True,
        countrycolor="#D6D0C4", showland=True, landcolor="#FBFAF7", showocean=True,
        oceancolor="#E6EEF1", showlakes=True, lakecolor="#E6EEF1", showcoastlines=True,
        coastlinecolor="#B9C7CC", showframe=False, bgcolor="rgba(0,0,0,0)",
        lataxis_range=[4.1, 10.9], lonaxis_range=[-8.8, -2.3])
    fig.update_layout(height=hauteur, margin={"l": 0, "r": 0, "t": 0, "b": 0},
                      paper_bgcolor="rgba(0,0,0,0)", showlegend=False,
                      hoverlabel={"bgcolor": "white", "font_size": 13})
    return fig

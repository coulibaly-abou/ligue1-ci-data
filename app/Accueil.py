"""Tableau de bord de la Ligue 1 ivoirienne — page d'accueil.

    streamlit run app/Accueil.py
"""
import plotly.express as px
import streamlit as st
from commun import (
    NOMS_MODELES,
    ORANGE,
    VERT,
    charger,
    configurer,
    metriques,
    pied_de_page,
)

configurer("Accueil")

st.title("⚽ Ligue 1 ivoirienne — la data du championnat")
st.markdown(
    "Dix saisons de **MTN Ligue 1** (2016 → 2026) collectées automatiquement sur le web, "
    "structurées dans **MongoDB → PostgreSQL**, analysées en SQL et en réseau, puis "
    "utilisées pour **prédire l'issue des matchs** avec plusieurs modèles, dont un "
    "réseau de neurones."
)

matchs = charger("matchs")
joues = matchs[matchs["statut"] == "joue"]
palmares = charger("palmares")
clubs = charger("clubs")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Saisons", matchs["saison"].nunique())
c2.metric("Matchs joués", f"{len(joues):,}".replace(",", " "))
c3.metric("Buts", f"{int(joues['buts_dom'].sum() + joues['buts_ext'].sum()):,}"
          .replace(",", " "))
c4.metric("Clubs", matchs["dom"].nunique())
c5.metric("Buts / match", f"{(joues['buts_dom'] + joues['buts_ext']).mean():.2f}")

gauche, droite = st.columns([3, 2])
with gauche:
    st.subheader("Qui gagne le championnat ?")
    titres = palmares.groupby("champion").size().sort_values().reset_index(name="titres")
    fig = px.bar(titres, x="titres", y="champion", orientation="h", text="titres",
                 color_discrete_sequence=[ORANGE])
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(height=280, margin={"l": 0, "r": 0, "t": 10, "b": 0}, xaxis_title=None,
                      yaxis_title=None)
    st.plotly_chart(fig, width="stretch")
    st.caption("Champions 2016-17 → 2025-26 (classements officiels RSSSF). "
               "L'ASEC Mimosas a remporté " +
               f"{int((palmares['champion'] == 'ASEC Mimosas').sum())} des "
               f"{len(palmares)} titres.")
with droite:
    st.subheader("Les clubs sur la carte")
    carte = clubs.dropna(subset=["lat"]).groupby(["ville", "lat", "lon"]) \
        .agg(clubs=("club", lambda s: ", ".join(s)), n=("club", "size")).reset_index()
    fig = px.scatter_map(carte, lat="lat", lon="lon", size="n", hover_name="ville",
                         hover_data={"clubs": True, "lat": False, "lon": False, "n": False},
                         color_discrete_sequence=[VERT], zoom=5.2, size_max=28,
                         center={"lat": 7.4, "lon": -5.5}, map_style="carto-positron")
    fig.update_layout(height=300, margin={"l": 0, "r": 0, "t": 0, "b": 0})
    st.plotly_chart(fig, width="stretch")

st.subheader("Prédire un match : les modèles comparés")
m = metriques()
if m:
    glis = m["validation_glissante_moyenne"]
    naif = glis["naif"]
    meilleur = min((n for n in glis if n != "naif"), key=lambda n: glis[n]["log_loss"])
    a, b, c = st.columns(3)
    a.metric("Meilleur modèle", NOMS_MODELES[meilleur])
    b.metric("Bons pronostics", f"{glis[meilleur]['accuracy']:.1%}",
             f"{(glis[meilleur]['accuracy'] - naif['accuracy']) * 100:+.1f} pts vs naïf")
    c.metric("Log-loss", f"{glis[meilleur]['log_loss']:.4f}",
             f"{glis[meilleur]['log_loss'] - naif['log_loss']:+.4f} vs naïf",
             delta_color="inverse")
    st.caption(f"Validation glissante : {m['protocole']['n_glissante']} matchs de 2021-22 à "
               "2025-26, chaque saison prédite avec les seules saisons précédentes. Détail "
               "dans la page **Modèles** ; prochains matchs dans la page **Prédiction**.")

st.subheader("Architecture")
st.markdown("""
| Étape | Outils | Rôle |
|---|---|---|
| Collecte | Python, requests, BeautifulSoup, API-Football | RSSSF, Wikipédia, Futbol24 — robots.txt respecté, collecte quotidienne planifiée |
| Zone brute | **MongoDB** | pages HTML archivées (URL, date, SHA-256), documents bruts par source |
| Zone analytique | **PostgreSQL** | modèle Merise, ETL avec recoupement des sources, 10 requêtes SQL, vues matérialisées |
| Réseau | networkx (Neo4j à venir) | graphe des carrières et transferts : PageRank, communautés |
| Modèles | scikit-learn, **PyTorch** | Elo, régression logistique, forêt, boosting, MLP — découpage temporel |
| Restitution | **Streamlit**, Plotly | ce tableau de bord |
""")
pied_de_page()

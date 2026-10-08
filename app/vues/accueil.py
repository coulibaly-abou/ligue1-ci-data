"""Page d'accueil : objectif et impact, chiffres clés, palmarès, carte, synthèse des modèles."""
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

configurer()

st.title("Ligue 1 ivoirienne — la data du championnat")

matchs = charger("matchs")
joues = matchs[matchs["statut"] == "joue"]
palmares = charger("palmares")
clubs = charger("clubs")
resultats = charger("resultats_club")
mouvements = charger("reseau_mouvements")

st.markdown(
    "#### Objectif\n"
    "La Ligue 1 ivoirienne forme des joueurs pour toute l'Afrique et l'Europe, mais ses "
    "données sont dispersées, incomplètes et presque jamais analysées. Ce projet les "
    "rassemble dans une **base fiable, sourcée et gratuite**, pour que les acteurs du "
    "football ivoirien puissent **décider avec des faits plutôt qu'avec des impressions**."
)

# Faits calculés sur les données : chaque impact s'appuie sur un constat mesuré
par_lieu = resultats.groupby(["club", "a_domicile"])["points"].mean().unstack()
par_lieu = par_lieu[resultats.groupby("club").size() >= 120]
ecart = (par_lieu[True] - par_lieu[False]).sort_values()
club_ecart = ecart.index[0]
departs = mouvements[mouvements["depart_ligue1"].astype(bool)
                     & ~mouvements["arrivee_ligue1"].astype(bool)]
part_asec = (departs["depart"] == "ASEC Mimosas").mean()
titres_asec = int((palmares["champion"] == "ASEC Mimosas").sum())
pct_nuls = (joues["resultat"] == "N").mean()

impacts = [
    ("Clubs et entraîneurs", "Mesurer sa performance sans cellule data",
     (f"{club_ecart} prend moins de points à domicile "
     f"({par_lieu.loc[club_ecart, True]:.2f} par match) qu'à l'extérieur "
     f"({par_lieu.loc[club_ecart, False]:.2f}) : un signal concret à travailler."),
     "Fiche club · Championnat"),
    ("Joueurs, agents, recruteurs", "Rendre visibles les talents locaux",
     (f"{len(departs)} départs suivis vers {departs['arrivee'].nunique()} clubs hors "
      "Ligue 1 (Europe, Maghreb, Afrique de l'Est…), "
     f"dont {part_asec:.0%} depuis la seule ASEC : les joueurs des autres clubs restent "
     "peu exposés."),
     "Réseau des clubs"),
    ("Médias et supporters", "Débattre avec des chiffres vérifiés",
     ("Scores recoupés entre trois sources, écarts signalés, probabilités de match "
     "expliquées plutôt qu'un pronostic tranché."),
     "Prédiction · Modèles"),
    ("Ligue et Fédération", "Piloter l'équilibre du championnat",
     (f"{titres_asec} titres sur {len(palmares)} pour l'ASEC, {pct_nuls:.0%} de nuls : des "
     "indicateurs pour évaluer le format, le calendrier et l'attractivité du "
     "championnat."),
     "Championnat"),
]
colonnes = st.columns(4)
for col, (public, but, fait, pages) in zip(colonnes, impacts, strict=True):
    with col.container(border=True, height="stretch"):
        st.markdown(f"**{public}**")
        st.markdown(f"<span style='color:{ORANGE};font-weight:600'>{but}</span>",
                    unsafe_allow_html=True)
        st.markdown(fait)
        st.caption(f"Pages : {pages}")
st.caption("Ce tableau de bord n'est pas un outil de paris : les probabilités servent à "
           "comprendre le championnat, pas à miser.")

st.markdown(
    "#### Le projet en chiffres\n"
    "Dix saisons de **MTN Ligue 1** (2016 → 2026) collectées automatiquement sur le web, "
    "structurées dans **MongoDB → PostgreSQL**, analysées en SQL et en réseau, puis "
    "utilisées pour **prédire l'issue des matchs** avec six modèles, dont un réseau de "
    "neurones."
)

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

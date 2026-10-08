import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from commun import ORANGE, VERT, charger, configurer, pied_de_page

configurer()
st.title("Réseau des clubs : où vont les joueurs ?")
st.markdown(
    "<p style='color:#57606A;font-size:1.05rem'>"
    "Pour les joueurs, agents et recruteurs : quels clubs exposent leurs joueurs, "
    "vers quels championnats ils partent, et quels clubs restent hors des radars."
    "</p>", unsafe_allow_html=True)
st.markdown(
    "Deux clubs sont reliés quand un joueur passe de l'un à l'autre : **carrières "
    "Wikipédia** (≈ 460 joueurs et entraîneurs) et **transferts API-Football** (2022 → 2026). "
    "La taille d'un club = son **PageRank** : un club est central s'il échange des joueurs "
    "avec d'autres clubs eux-mêmes centraux."
)

noeuds = charger("reseau_noeuds")
aretes = charger("reseau_aretes")
mvts = charger("reseau_mouvements")

c1, c2, c3 = st.columns(3)
c1.metric("Clubs dans le réseau", len(noeuds))
c2.metric("Mouvements de joueurs", len(mvts))
c3.metric("Liens club → club", len(aretes))

poids_min = st.slider("Afficher les liens d'au moins … mouvements", 1, 5, 1)
visibles = noeuds.dropna(subset=["x"]).set_index("club")
liens = aretes[aretes["depart"].isin(visibles.index) & aretes["arrivee"].isin(visibles.index)
               & (aretes["poids"] >= poids_min)]

fig = go.Figure()
for lien in liens.itertuples():
    a, b = visibles.loc[lien.depart], visibles.loc[lien.arrivee]
    fig.add_scatter(x=[a.x, b.x], y=[a.y, b.y], mode="lines", hoverinfo="skip",
                    line={"width": 0.6 + lien.poids * 0.6, "color": "rgba(140,140,140,0.35)"},
                    showlegend=False)
for ligue1, couleur, nom in ((True, ORANGE, "Club de Ligue 1 ivoirienne"),
                             (False, VERT, "Club étranger / autre division")):
    n = visibles[visibles["ligue1"] == ligue1]
    fig.add_scatter(
        x=n["x"], y=n["y"], mode="markers+text", name=nom,
        marker={"size": 8 + 260 * n["pagerank"] ** 0.75, "color": couleur,
                "line": {"width": 1, "color": "white"}},
        text=[c if p > 0.004 else "" for c, p in zip(n.index, n["pagerank"], strict=True)],
        textposition="top center", textfont={"size": 10},
        customdata=n[["pagerank", "arrivees", "departs"]].to_numpy(),
        hovertext=n.index,
        hovertemplate="<b>%{hovertext}</b><br>PageRank %{customdata[0]:.4f}"
                      "<br>arrivées %{customdata[1]} · départs %{customdata[2]}<extra></extra>")
fig.update_layout(height=720, margin={"l": 0, "r": 0, "t": 10, "b": 0},
                  xaxis={"visible": False}, yaxis={"visible": False},
                  legend={"orientation": "h", "y": 1.02}, plot_bgcolor="rgba(0,0,0,0)")
st.plotly_chart(fig, width="stretch")
st.caption("Affichage : clubs de Ligue 1 + les 25 clubs étrangers les plus centraux. "
           "Biais : seuls les joueurs ayant un article Wikipédia sont suivis — surtout "
           "ceux de l'ASEC, de l'Africa Sports et les joueurs partis à l'étranger.")

gauche, droite = st.columns(2)
with gauche:
    st.subheader("Clubs les plus centraux (PageRank)")
    top = noeuds.head(15).copy()
    top["Type"] = top["ligue1"].map({True: "Ligue 1 CI", False: "Étranger"})
    fig = px.bar(top.iloc[::-1], x="pagerank", y="club", orientation="h", color="Type",
                 color_discrete_map={"Ligue 1 CI": ORANGE, "Étranger": VERT})
    fig.update_layout(height=480, margin={"l": 0, "r": 0, "t": 10, "b": 0},
                      xaxis_title="PageRank", yaxis_title=None,
                      legend={"orientation": "h", "y": 1.08})
    st.plotly_chart(fig, width="stretch")
with droite:
    st.subheader("Principales destinations à l'étranger")
    sortants = mvts[mvts["depart_ligue1"].astype(bool) & ~mvts["arrivee_ligue1"].astype(bool)]
    dest = sortants.groupby("arrivee").size().sort_values(ascending=False).head(15)
    st.dataframe(dest.rename("joueurs venus de Ligue 1 CI").reset_index()
                 .rename(columns={"arrivee": "club"}), hide_index=True,
                 width="stretch", height=480)

st.subheader("Communautés de clubs (algorithme de Louvain)")
st.caption("Groupes de clubs qui s'échangent surtout des joueurs entre eux.")
comm = noeuds[noeuds["ligue1"]].groupby("communaute")["club"].apply(list)
for i, clubs in comm.items():
    etrangers = noeuds[(noeuds["communaute"] == i) & ~noeuds["ligue1"]]["club"].head(5)
    st.markdown(f"**Groupe {i + 1}** — {', '.join(clubs)}  \n"
                f"<span style='color:gray'>liés à : {', '.join(etrangers)}</span>",
                unsafe_allow_html=True)
pied_de_page()

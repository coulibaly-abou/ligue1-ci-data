import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from commun import (
    COULEURS_RESULTAT,
    LIBELLES_RESULTAT,
    ORANGE,
    VERT,
    charger,
    classement_final,
    configurer,
    entete,
    kpis,
    pied_de_page,
    section,
    serie_html,
)

configurer()
entete("Championnat",
       "Suivre la hiérarchie, l'équilibre du championnat et le poids réel de l'avantage "
       "du terrain, saison par saison.")

classement = charger("classement_journee")
resultats_saison = charger("resultats_saison")
resultats_club = charger("resultats_club")
saisons = sorted(classement["saison"].unique(), reverse=True)
saison = st.selectbox("Saison", saisons, index=1 if len(saisons) > 1 else 0)

palmares = charger("palmares")
r_saison = resultats_saison.set_index("saison")
champion = palmares.set_index("saison")["champion"].get(saison)
kpis([(champion or "en cours", "champion (classement officiel RSSSF)"),
      (f"{int(r_saison.loc[saison, 'matchs'])}" if saison in r_saison.index else "—",
       "matchs joués"),
      (f"{r_saison.loc[saison, 'pct_nul']:.0f} %" if saison in r_saison.index else "—",
       "de matchs nuls"),
      (f"{r_saison.loc[saison, 'buts_par_match']:.2f}".replace(".", ",")
       if saison in r_saison.index else "—", "buts par match")])

section("Classement", f"Classement recalculé — {saison}")
st.caption("Recalculé à partir des matchs (vue matérialisée `mv_classement_journee`). "
           "En 2020-21 (deux poules + play-off) et 2019-20 (arrêt Covid), il diffère du "
           "classement officiel.")
final = classement_final(classement, saison)
c = resultats_club[resultats_club["saison"] == saison]
bilan = c.groupby("club").agg(J=("issue", "size"), V=("issue", lambda s: (s == "V").sum()),
                              N=("issue", lambda s: (s == "N").sum()),
                              D=("issue", lambda s: (s == "D").sum()),
                              BP=("bp", "sum"), BC=("bc", "sum"))
tableau = final.set_index("club")[["rang_final", "points", "difference"]].join(bilan)
tableau = tableau.rename(columns={"rang_final": "Rang", "points": "Pts", "difference": "Diff"})
tableau.index.name = "Club"
gauche, droite = st.columns([2, 3])
gauche.dataframe(tableau, height=600, width="stretch")

with droite:
    st.markdown("**Évolution du rang journée après journée**")
    evo = classement[classement["saison"] == saison]
    top = list(final["club"].head(4))
    choix = st.multiselect("Clubs", list(final["club"]), default=top)
    fig = px.line(evo[evo["club"].isin(choix)], x="journee", y="rang", color="club",
                  markers=True, category_orders={"club": choix},
                  color_discrete_sequence=[ORANGE, VERT, "#2A78D6", "#7A4FB0", "#B8322A",
                                           "#9A9A94", "#C98500", "#1BAF7A"])
    fig.update_yaxes(autorange="reversed", title="Rang", dtick=1)
    fig.update_xaxes(title="Journée (matchs joués par le club)")
    fig.update_layout(height=520, margin={"l": 0, "r": 0, "t": 10, "b": 0},
                      legend={"orientation": "h", "y": -0.15})
    st.plotly_chart(fig, width="stretch")

section("Forme", "Forme actuelle des clubs",
        f"Cinq derniers matchs de chaque club engagé en {saisons[0]}, saison précédente "
        "comprise si besoin (le plus récent à droite).")
engages = resultats_club.loc[resultats_club["saison"] == saisons[0], "club"].unique()
actuelle = resultats_club[resultats_club["club"].isin(engages)].sort_values("date_match")
forme = actuelle.groupby("club").agg(series=("issue", lambda s: list(s.tail(5))),
                                     points=("points", lambda s: int(s.tail(5).sum())),
                                     joues=("issue", "size"))
forme = forme.sort_values(["points", "joues"], ascending=False)
colonnes = st.columns(4)
for i, (club, ligne) in enumerate(forme.iterrows()):
    colonnes[i % 4].markdown(f"<div style='margin-bottom:.7rem'><b>{club}</b> "
                             f"<span style='color:#57606A'>· {ligne.points} pts</span>"
                             f"{serie_html(ligne.series)}</div>", unsafe_allow_html=True)

section("Performances par saison", "Rang final de chaque club, saison après saison",
        "Classement recalculé à partir des matchs ; saison en cours exclue. Case vide : "
        "club absent de la Ligue 1 cette saison-là.")
rangs = pd.concat([classement_final(classement, s)[["club", "rang_final"]].assign(saison=s)
                   for s in saisons[1:]])
grille = rangs.pivot(index="club", columns="saison", values="rang_final")
grille = grille.loc[grille.notna().sum(axis=1).sort_values(ascending=False).index]
grille = grille.loc[grille.mean(axis=1).sort_values().index]
fig = px.imshow(grille, text_auto=True, aspect="auto",
                color_continuous_scale=[[0, ORANGE], [0.35, "#F8D9B8"], [1, "#F4F4F2"]])
fig.update_layout(height=760, margin={"l": 0, "r": 0, "t": 10, "b": 0},
                  coloraxis_colorbar={"title": "Rang"}, xaxis_title=None, yaxis_title=None)
fig.update_traces(hovertemplate="%{y} · %{x} : rang %{z}<extra></extra>")
st.plotly_chart(fig, width="stretch")

section("Palmarès", "Qui gagne le championnat ?")
gauche, droite = st.columns([3, 2])
with gauche:
    titres = palmares.groupby("champion").size().sort_values().reset_index(name="titres")
    fig = px.bar(titres, x="titres", y="champion", orientation="h", text="titres",
                 color_discrete_sequence=[ORANGE])
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(height=300, margin={"l": 0, "r": 0, "t": 10, "b": 0},
                      xaxis_title="Titres", yaxis_title=None)
    st.plotly_chart(fig, width="stretch")
with droite:
    st.dataframe(palmares.rename(columns={"saison": "Saison", "champion": "Champion",
                                          "points": "Points",
                                          "titres_depuis_2016": "Titres depuis 2016"}),
                 hide_index=True, width="stretch", height=300)
st.caption("Champions 2016-17 → 2025-26 selon les classements officiels RSSSF.")

section("Profil du championnat", "Un championnat fermé : beaucoup de nuls, peu de buts")
r = resultats_saison[resultats_saison["matchs"] >= 90].copy()  # sans la saison qui débute
gauche, droite = st.columns(2)
with gauche:
    long = r.melt(id_vars="saison", value_vars=["pct_domicile", "pct_nul", "pct_exterieur"],
                  var_name="issue", value_name="pct")
    long["issue"] = long["issue"].map({"pct_domicile": "D", "pct_nul": "N",
                                       "pct_exterieur": "E"})
    long["Résultat"] = long["issue"].map(LIBELLES_RESULTAT)
    fig = px.bar(long, x="saison", y="pct", color="Résultat", text_auto=".0f",
                 color_discrete_map={LIBELLES_RESULTAT[k]: v for k, v in
                                     COULEURS_RESULTAT.items()})
    fig.update_layout(height=380, yaxis_title="% des matchs", xaxis_title=None,
                      margin={"l": 0, "r": 0, "t": 10, "b": 0}, legend={"orientation": "h", "y": 1.1})
    st.plotly_chart(fig, width="stretch")
with droite:
    fig = px.bar(r, x="saison", y="buts_par_match", text_auto=".2f",
                 color_discrete_sequence=[ORANGE])
    fig.update_layout(height=380, yaxis_title="Buts par match", xaxis_title=None,
                      margin={"l": 0, "r": 0, "t": 10, "b": 0})
    st.plotly_chart(fig, width="stretch")
st.caption("Pour comparaison : environ 2,7 buts par match et 25 % de nuls dans les grands "
           "championnats européens.")

section("Avantage du terrain", "Points par match à domicile et à l'extérieur",
        "Toutes saisons confondues, clubs avec au moins 60 matchs.")
av = resultats_club.groupby(["club", "a_domicile"])["points"].mean().unstack()
av.columns = ["Extérieur", "Domicile"]
av["n"] = resultats_club.groupby("club").size()
av = av[av["n"] >= 60].assign(Avantage=lambda d: d["Domicile"] - d["Extérieur"]) \
    .sort_values("Avantage")
fig = go.Figure()
fig.add_bar(y=av.index, x=av["Domicile"], orientation="h", name="Domicile",
            marker_color=ORANGE)
fig.add_bar(y=av.index, x=av["Extérieur"], orientation="h", name="Extérieur",
            marker_color=VERT)
fig.update_layout(barmode="group", height=650, xaxis_title="Points par match",
                  margin={"l": 0, "r": 0, "t": 10, "b": 0}, legend={"orientation": "h", "y": 1.05})
st.plotly_chart(fig, width="stretch")

gauche, droite = st.columns(2)
with gauche:
    section("Scores", "Scores les plus fréquents")
    st.dataframe(charger("scores"), hide_index=True, width="stretch")
with droite:
    section("Séries", "Plus longues séries sans défaite")
    st.dataframe(charger("series"), hide_index=True, width="stretch")
pied_de_page()

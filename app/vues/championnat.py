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
    pied_de_page,
)

configurer()
st.title("Championnat")

classement = charger("classement_journee")
resultats_saison = charger("resultats_saison")
resultats_club = charger("resultats_club")
saisons = sorted(classement["saison"].unique(), reverse=True)
saison = st.selectbox("Saison", saisons, index=1 if len(saisons) > 1 else 0)

st.subheader(f"Classement recalculé — {saison}")
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
gauche, droite = st.columns([2, 3])
gauche.dataframe(tableau, height=600, width="stretch")

with droite:
    st.markdown("**Évolution du rang journée après journée**")
    evo = classement[classement["saison"] == saison]
    top = list(final["club"].head(4))
    choix = st.multiselect("Clubs", list(final["club"]), default=top)
    fig = px.line(evo[evo["club"].isin(choix)], x="journee", y="rang", color="club",
                  markers=True)
    fig.update_yaxes(autorange="reversed", title="Rang", dtick=1)
    fig.update_xaxes(title="Journée (matchs joués par le club)")
    fig.update_layout(height=520, margin={"l": 0, "r": 0, "t": 10, "b": 0},
                      legend={"orientation": "h", "y": -0.15})
    st.plotly_chart(fig, width="stretch")

st.subheader("Un championnat fermé : beaucoup de nuls, peu de buts")
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

st.subheader("Avantage du terrain par club (toutes saisons)")
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
    st.subheader("Scores les plus fréquents")
    st.dataframe(charger("scores"), hide_index=True, width="stretch")
with droite:
    st.subheader("Plus longues séries sans défaite")
    st.dataframe(charger("series"), hide_index=True, width="stretch")
pied_de_page()

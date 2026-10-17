import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from commun import (
    GRIS,
    ORANGE,
    ROUGE,
    VERT,
    charger,
    classement_final,
    configurer,
    entete,
    kpis,
    note_html,
    parametre,
    pied_de_page,
    section,
    serie_html,
)

configurer()
entete("Clubs", "Le bilan objectif d'un club : résultats, buts, régularité, forme et "
       "performance à domicile et à l'extérieur, à comparer d'une saison à l'autre.")

resultats = charger("resultats_club")
classement = charger("classement_journee")
buteurs = charger("buteurs")
clubs_info = charger("clubs").set_index("club")
palmares = charger("palmares")

saison_actuelle = resultats["saison"].max()
actuels = sorted(resultats.loc[resultats["saison"] == saison_actuelle, "club"].unique())
autres = sorted(set(resultats["club"]) - set(actuels))
choix = actuels + autres
club = st.selectbox("Club", choix, index=choix.index(parametre(
    "club", choix, "ASEC Mimosas" if "ASEC Mimosas" in choix else choix[0])))
st.query_params["club"] = club
r = resultats[resultats["club"] == club].sort_values("date_match")

info = clubs_info.loc[club] if club in clubs_info.index else None
if info is not None:
    st.caption(f"Ville : {info['ville'] or '—'} · Stade : {info['stade'] or '—'}")

n = len(r)
v, nul, d = ((r["issue"] == x).sum() for x in ("V", "N", "D"))
kpis([(f"{n}", f"matchs en Ligue 1 · {r['saison'].nunique()} saison(s)"),
      (f"{v}", f"victoires ({v / n:.0%})"), (f"{nul}", f"nuls ({nul / n:.0%})"),
      (f"{d}", f"défaites ({d / n:.0%})")])
st.write("")
kpis([(f"{int(r['bp'].sum())}", f"buts marqués ({r['bp'].mean():.2f} par match)"
       .replace(".", ",")),
      (f"{int(r['bc'].sum())}", f"buts encaissés ({r['bc'].mean():.2f} par match)"
       .replace(".", ",")),
      (f"{r['points'].mean():.2f}".replace(".", ","), "points par match"),
      (f"{int((palmares['champion'] == club).sum())}", "titres depuis 2016")])

section("Forme", "Les 10 derniers matchs")
st.caption("Le plus récent à droite.")
st.markdown(serie_html(list(r["issue"].tail(10))), unsafe_allow_html=True)
derniers = r.tail(10).iloc[::-1][["date_match", "a_domicile", "adversaire", "bp", "bc"]]
derniers["Lieu"] = derniers.pop("a_domicile").map({True: "Domicile", False: "Extérieur"})
derniers["Score"] = derniers.pop("bp").astype(str) + " - " + derniers.pop("bc").astype(str)
with st.expander("Détail des 10 derniers matchs"):
    st.dataframe(derniers, hide_index=True, width="stretch")

section("Évolution", "Performances saison après saison")
par_saison_ppm = r.groupby("saison")["points"].agg(ppm="mean", matchs="size").reset_index()
par_saison_ppm["statut"] = (par_saison_ppm["saison"] == saison_actuelle).map(
    {True: "Saison en cours", False: "Saison terminée"})
fig = px.bar(par_saison_ppm, x="saison", y="ppm", text_auto=".2f", color="statut",
             color_discrete_map={"Saison terminée": ORANGE, "Saison en cours": GRIS},
             hover_data={"matchs": True, "statut": False})
fig.update_traces(textfont_color="white")
fig.update_layout(legend={"orientation": "h", "y": 1.12, "title": None})
fig.update_layout(height=300, margin={"l": 0, "r": 0, "t": 10, "b": 0}, xaxis_title=None,
                  yaxis_title="Points par match")
st.plotly_chart(fig, width="stretch")

gauche, droite = st.columns(2)
with gauche:
    st.markdown("**Rang final par saison**")
    rangs = []
    for s in sorted(r["saison"].unique()):
        if s == saison_actuelle:  # saison qui débute : rang pas encore significatif
            continue
        f = classement_final(classement, s)
        ligne = f[f["club"] == club]
        if len(ligne):
            rangs.append({"saison": s, "rang": int(ligne["rang_final"].iloc[0]),
                          "points": int(ligne["points"].iloc[0])})
    if rangs:
        fig = px.line(rangs, x="saison", y="rang", markers=True, text="rang",
                      color_discrete_sequence=[ORANGE])
        fig.update_traces(textposition="top center")
        fig.update_yaxes(autorange="reversed", dtick=2, title="Rang")
        fig.update_layout(height=360, margin={"l": 0, "r": 0, "t": 10, "b": 0}, xaxis_title=None)
        st.plotly_chart(fig, width="stretch")
        st.caption("Saison en cours exclue.")
with droite:
    st.markdown("**Résultats à domicile et à l'extérieur**")
    lieux = r.assign(Lieu=r["a_domicile"].map({True: "Domicile", False: "Extérieur"}))
    rep = lieux.groupby(["Lieu", "issue"]).size().unstack(fill_value=0)
    rep = rep.div(rep.sum(axis=1), axis=0).reindex(columns=["V", "N", "D"], fill_value=0)
    fig = go.Figure()
    for issue, couleur, nom in (("V", VERT, "Victoire"), ("N", GRIS, "Nul"),
                                ("D", ROUGE, "Défaite")):
        fig.add_bar(y=rep.index, x=rep[issue], name=nom, orientation="h",
                    marker_color=couleur, textfont={"color": "white"},
                    text=(rep[issue] * 100).round().astype(int).astype(str) + " %")
    fig.update_layout(barmode="stack", height=360, xaxis_tickformat=".0%",
                      margin={"l": 0, "r": 0, "t": 10, "b": 0}, legend={"orientation": "h", "y": 1.1})
    st.plotly_chart(fig, width="stretch")

section("Buts", "Buts marqués et encaissés par saison")
par_saison = r.groupby("saison")[["bp", "bc"]].sum().reset_index()
fig = go.Figure()
fig.add_bar(x=par_saison["saison"], y=par_saison["bp"], name="Marqués", marker_color=VERT)
fig.add_bar(x=par_saison["saison"], y=par_saison["bc"], name="Encaissés", marker_color=ORANGE)
fig.update_layout(barmode="group", height=320, margin={"l": 0, "r": 0, "t": 10, "b": 0},
                  legend={"orientation": "h", "y": 1.1})
st.plotly_chart(fig, width="stretch")

section("Joueurs", "Les meilleurs joueurs offensifs du club",
        "Note de contribution offensive sur 10 (saisons 2022-23 → 2024-25) : "
        "cliquer sur un joueur pour ouvrir sa fiche.")
notes = charger("joueurs")
notes = notes[notes["club"] == club].sort_values("note", ascending=False).head(8)
if len(notes):
    cols = st.columns(4)
    for i, j in enumerate(notes.itertuples()):
        with cols[i % 4].container(border=True):
            st.markdown(f"<div style='display:flex;justify-content:space-between;"
                        f"align-items:center;gap:.5rem'><div><b>{j.nom}</b><br>"
                        f"<span style='color:#57606A;font-size:.85rem'>{j.saison} · {j.buts} "
                        f"buts</span></div>{note_html(j.note, 40)}</div>",
                        unsafe_allow_html=True)
            st.page_link("vues/joueurs.py", label="Fiche", icon=":material/arrow_forward:",
                         query_params={"saison": j.saison, "joueur": j.joueur})
else:
    st.info("Aucun buteur de ce club dans les déroulés publiés (2022-23 → 2024-25).")
st.page_link("vues/attaque_defense.py", label=f"Attaque et défense de {club} en détail",
             icon=":material/swords:", query_params={"club": club})
st.page_link("vues/matchs.py", label=f"Tous les matchs de {club}",
             icon=":material/scoreboard:")

b = buteurs[buteurs["club"] == club].sort_values(["saison", "buts"], ascending=[False, False])
if len(b):
    with st.expander("Meilleurs buteurs publiés (Wikipédia, API-Football), depuis 2016"):
        st.dataframe(b[["saison", "joueur", "buts", "source"]]
                     .rename(columns=str.capitalize), hide_index=True, width="stretch")
pied_de_page()

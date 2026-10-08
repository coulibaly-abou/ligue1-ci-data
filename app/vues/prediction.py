import numpy as np
import plotly.graph_objects as go
import streamlit as st
from commun import (
    COULEURS_RESULTAT,
    NOMS_MODELES,
    charger_modele,
    configurer,
    metriques,
    pied_de_page,
)

configurer()
st.title("Prédiction des matchs 2026-2027")

m = metriques()
prochains = charger_modele("predictions_a_venir")
duels = charger_modele("predictions_duels")
elo = charger_modele("elo_actuel")
if m is None or duels is None:
    st.warning("Résultats du modèle absents : lancer `make train` puis `make export`.")
    st.stop()

st.markdown(
    f"Modèle utilisé : **{NOMS_MODELES[m['modele_retenu']]}**, choisi en validation glissante "
    "et ré-entraîné sur toutes les saisons jouées. Les variables (Elo, forme, classement…) "
    "sont celles connues **après le dernier match joué**."
)


def barre(p_dom, p_nul, p_ext, dom, ext):
    fig = go.Figure()
    for p, cle, nom in ((p_dom, "D", dom), (p_nul, "N", "Nul"), (p_ext, "E", ext)):
        fig.add_bar(x=[p], y=[""], orientation="h", name=nom, text=f"{nom}<br>{p:.0%}",
                    marker_color=COULEURS_RESULTAT[cle], textposition="inside",
                    insidetextanchor="middle",
                    textfont={"color": "white", "size": 13},
                    marker_line={"color": "white", "width": 2})
    fig.update_layout(barmode="stack", height=90, showlegend=False,
                      margin={"l": 0, "r": 0, "t": 0, "b": 0},
                      xaxis={"visible": False, "range": [0, 1]}, yaxis={"visible": False})
    return fig


st.subheader("Simulateur : choisissez une affiche")
clubs = sorted(duels["dom"].unique())
a, b = st.columns(2)
dom = a.selectbox("Équipe à domicile", clubs,
                  index=clubs.index("ASEC Mimosas") if "ASEC Mimosas" in clubs else 0)
ext = b.selectbox("Équipe à l'extérieur", [c for c in clubs if c != dom],
                  index=0)
d = duels[(duels["dom"] == dom) & (duels["ext"] == ext)].iloc[0]
st.plotly_chart(barre(d.p_dom, d.p_nul, d.p_ext, dom, ext), width="stretch",
                key="simulateur")
if elo is not None:
    notes = elo.set_index("club")["elo"]
    st.caption(f"Elo actuel : {dom} {notes.get(dom, 1500):.0f} · {ext} {notes.get(ext, 1500):.0f}")

st.subheader("Prochains matchs datés")
if prochains is not None and len(prochains):
    dates = prochains.dropna(subset=["date_match"]).sort_values(["date_match", "dom"])
    if len(dates):
        for ligne in dates.itertuples():
            g, dr = st.columns([1, 3])
            g.markdown(f"**{ligne.dom}** – **{ligne.ext}**  \n"
                       f"<span style='color:gray'>{ligne.date_match}</span>",
                       unsafe_allow_html=True)
            dr.plotly_chart(barre(ligne.p_dom, ligne.p_nul, ligne.p_ext, ligne.dom, ligne.ext),
                            width="stretch", key=f"m{ligne.id_match}")
    else:
        st.info("Aucun match daté pour l'instant : le calendrier est publié journée par "
                "journée et la collecte quotidienne l'ajoute dès sa parution.")

    st.subheader("Tous les matchs restants de la saison")
    club = st.selectbox("Filtrer par club", ["Tous les clubs"] + clubs)
    reste = prochains if club == "Tous les clubs" else \
        prochains[(prochains["dom"] == club) | (prochains["ext"] == club)]
    reste = reste.assign(favori=lambda d: np.select(
        [d["p_dom"] >= d[["p_nul", "p_ext"]].max(axis=1),
         d["p_ext"] >= d[["p_nul", "p_dom"]].max(axis=1)], [d["dom"], d["ext"]], "Nul"))
    reste = reste.assign(date_match=reste["date_match"].fillna("à confirmer"))
    st.dataframe(
        reste[["date_match", "dom", "ext", "p_dom", "p_nul", "p_ext", "favori"]]
        .sort_values(["date_match", "dom"]),
        hide_index=True, width="stretch", height=420,
        column_config={
            "date_match": st.column_config.TextColumn("Date"),
            "dom": "Domicile", "ext": "Extérieur", "favori": "Favori",
            "p_dom": st.column_config.ProgressColumn("Victoire dom.", format="percent",
                                                     min_value=0, max_value=1),
            "p_nul": st.column_config.ProgressColumn("Nul", format="percent",
                                                     min_value=0, max_value=1),
            "p_ext": st.column_config.ProgressColumn("Victoire ext.", format="percent",
                                                     min_value=0, max_value=1)})
    st.caption(f"{len(reste)} matchs. Probabilités recalculées après chaque journée par "
               "la collecte quotidienne puis `make train export`.")

if elo is not None:
    st.subheader("Classement Elo actuel")
    actuels = elo[elo["club"].isin(clubs)].reset_index(drop=True)
    actuels.index += 1
    st.dataframe(actuels.style.format({"elo": "{:.0f}"}).bar(subset=["elo"], color="#E07000"),
                 width="stretch")

st.info("Le football ivoirien est très serré (≈ 30 % de nuls, ≈ 2 buts par match) : "
        "même le meilleur modèle se trompe plus d'une fois sur deux. Les probabilités "
        "sont utiles pour comparer des affiches, pas pour parier.")
pied_de_page()

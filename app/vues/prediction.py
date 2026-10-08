import numpy as np
import plotly.graph_objects as go
import streamlit as st
from commun import (
    COULEURS_RESULTAT,
    NOMS_MODELES,
    charger_modele,
    configurer,
    entete,
    kpis,
    lire_json,
    metriques,
    pied_de_page,
    section,
)

configurer()
entete("Prédiction des matchs 2026-2027",
       "Des probabilités expliquées pour situer chaque affiche de la saison en cours — "
       "pas un outil de paris.")

m = metriques()
prochains = charger_modele("predictions_a_venir")
duels = charger_modele("predictions_duels")
elo = charger_modele("elo_actuel")
if m is None or duels is None:
    st.warning("Résultats du modèle absents : lancer `make train` puis `make export`.")
    st.stop()

glis = m["validation_glissante_moyenne"][m["modele_retenu"]]
naif = m["validation_glissante_moyenne"]["naif"]
st.markdown(
    "<div class='carte-axe' style='min-height:0'>"
    "<div class='num'>LA QUESTION</div>"
    "<div class='nom' style='font-size:1.25rem'>Peut-on estimer le résultat d'un match à "
    "partir des informations disponibles avant le match ?</div>"
    f"<div class='txt'>Modèle utilisé : <b>{NOMS_MODELES[m['modele_retenu']]}</b>, retenu en "
    "validation glissante puis ré-entraîné sur toutes les saisons jouées. Il donne trois "
    "probabilités dont la somme vaut 100 % : <b>victoire domicile</b>, <b>match nul</b>, "
    "<b>victoire extérieur</b>. Le <b>résultat prédit</b> est l'issue la plus probable."
    "</div></div>", unsafe_allow_html=True)
st.write("")
kpis([(f"{glis['accuracy']:.1%}".replace(".", ","),
       (f"de résultats correctement prédits en validation ({m['protocole']['n_glissante']} "
       "matchs)")),
      (f"{naif['accuracy']:.1%}".replace(".", ","),
       "pour la référence naïve « toujours domicile »"),
      (f"{(glis['accuracy'] - naif['accuracy']) * 100:+.1f} pts".replace(".", ","),
       "de gain sur la référence")])
st.write("")


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


section("Simulateur", "Choisissez une affiche")
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

sources = lire_json("sources") or {}
collecte = (sources.get("derniere_collecte") or "")[:10]
section("Calendrier", "Matchs programmés",
        f"Dernier calendrier collecté le {collecte}. Un match passé dont le score n'est pas "
        "encore collecté reste affiché avec sa prédiction d'avant-match." if collecte else None)
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

    section("Saison 2026-2027", "Tous les matchs restants")
    club = st.selectbox("Filtrer par club", ["Tous les clubs"] + clubs)
    reste = prochains if club == "Tous les clubs" else \
        prochains[(prochains["dom"] == club) | (prochains["ext"] == club)]
    reste = reste.assign(favori=lambda d: np.select(
        [d["p_dom"] >= d[["p_nul", "p_ext"]].max(axis=1),
         d["p_ext"] >= d[["p_nul", "p_dom"]].max(axis=1)],
        ["Victoire " + d["dom"], "Victoire " + d["ext"]], "Nul"),
        proba_prevue=lambda d: d[["p_dom", "p_nul", "p_ext"]].max(axis=1))
    reste = reste.assign(date_match=reste["date_match"].fillna("à confirmer"))
    st.dataframe(
        reste[["date_match", "dom", "ext", "p_dom", "p_nul", "p_ext", "favori",
               "proba_prevue"]]
        .sort_values(["date_match", "dom"]),
        hide_index=True, width="stretch", height=420,
        column_config={
            "date_match": st.column_config.TextColumn("Date"),
            "dom": "Domicile", "ext": "Extérieur", "favori": "Résultat prédit",
            "proba_prevue": st.column_config.NumberColumn("Probabilité du résultat prédit",
                                                         format="percent"),
            "p_dom": st.column_config.ProgressColumn("Victoire dom.", format="percent",
                                                     min_value=0, max_value=1),
            "p_nul": st.column_config.ProgressColumn("Nul", format="percent",
                                                     min_value=0, max_value=1),
            "p_ext": st.column_config.ProgressColumn("Victoire ext.", format="percent",
                                                     min_value=0, max_value=1)})
    note_nul = ("" if (reste["favori"] == "Nul").any() else
                " Le nul n'est jamais l'issue la plus probable pour ce modèle : sa probabilité "
                "reste proche de 30 % quel que soit le match.")
    st.caption(f"{len(reste)} matchs. Probabilités recalculées après chaque journée par "
               f"la collecte quotidienne puis `make train export`.{note_nul}")

if elo is not None:
    section("Niveau des équipes", "Classement Elo actuel")
    actuels = elo[elo["club"].isin(clubs)].reset_index(drop=True)
    actuels.index += 1
    actuels = actuels.rename(columns={"club": "Club", "elo": "Score Elo"})
    st.dataframe(actuels.style.format({"Score Elo": "{:.0f}"})
                 .bar(subset=["Score Elo"], color="#E07000"),
                 width="stretch")

st.info("Le football ivoirien est très serré (≈ 30 % de nuls, ≈ 2 buts par match) : "
        "même le meilleur modèle se trompe plus d'une fois sur deux. Les probabilités "
        "sont utiles pour comparer des affiches, pas pour parier.")
pied_de_page()

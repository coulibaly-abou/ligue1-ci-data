import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from commun import (
    GRIS,
    LIGNE,
    ORANGE,
    ROUGE,
    VERT,
    cartes,
    charger,
    charger_modele,
    classement_final,
    configurer,
    couleur_club,
    nombre,
    note_html,
    parametre,
    pastille,
    pied_de_page,
    section,
    serie_html,
)
from indicateurs import (
    LIEUX,
    bilan,
    bilan_adversaires,
    classement,
    filtrer_resultats,
    prochains_matchs,
    tendance,
)

configurer()
resultats = charger("resultats_club")
classement_j = charger("classement_journee")
buteurs = charger("buteurs")
clubs_info = charger("clubs").set_index("club")
palmares = charger("palmares")
matchs = charger("matchs")
a_venir = charger_modele("predictions_a_venir")

# ------------------------------------------------------------------- club
saison_actuelle = resultats["saison"].max()
actuels = sorted(resultats.loc[resultats["saison"] == saison_actuelle, "club"].unique())
choix = actuels + sorted(set(resultats["club"]) - set(actuels))
club = st.selectbox("Club", choix, index=choix.index(parametre(
    "club", choix, "ASEC Mimosas" if "ASEC Mimosas" in choix else choix[0])),
    help="Les 16 clubs de la saison en cours d'abord, puis les anciens clubs de Ligue 1.")
st.query_params["club"] = club
tout = resultats[resultats["club"] == club].sort_values("date_match")

info = clubs_info.loc[club] if club in clubs_info.index else None
lieu_txt = " · ".join(x for x in ([info["ville"], info["stade"]] if info is not None else [])
                      if isinstance(x, str))
titres = int((palmares["champion"] == club).sum())
st.markdown(f"""
<div class="hero" style="padding:28px 34px 26px;margin-top:.4rem">
  <div class="barre" style="background:{couleur_club(club)}"></div>
  <div style="display:flex;gap:1.3rem;align-items:center;flex-wrap:wrap">
    {pastille(club, 76)}
    <div>
      <div class="tag" style="letter-spacing:.18em">Tableau de bord · Ligue 1 Côte d'Ivoire</div>
      <div class="titre" style="font-size:2.4rem;margin:.3rem 0 .2rem">{club}</div>
      <div class="profil">{lieu_txt or "Ville et stade non renseignés"} ·
        {tout['saison'].nunique()} saison(s) en Ligue 1 depuis 2016 ·
        {titres} titre{'s' if titres > 1 else ''} de champion</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

# ---------------------------------------------------------------- filtres
saisons_club = sorted(tout["saison"].unique(), reverse=True)
TOUTES = "Toutes les saisons"
# Saison par défaut : l'en-cours si le club y a déjà 5 matchs, sinon la dernière jouée
par_saison_n = tout.groupby("saison").size()
defaut = next((s for s in saisons_club if par_saison_n[s] >= 5), saisons_club[0])
cles = {"c_saison": defaut, "c_lieu": "Tous", "c_periode": None}
if st.session_state.get("c_club") != club:  # nouveau club : filtres remis à zéro
    for k, v in cles.items():
        st.session_state[k] = v
    st.session_state["c_club"] = club

a, b, c = st.columns([1.2, 1.3, 2])
saison = a.selectbox("Saison", [TOUTES] + saisons_club, key="c_saison")
lieu = b.segmented_control("Lieu", LIEUX, key="c_lieu") or "Tous"
journees = None
if saison != TOUTES:
    n_max = int(tout.loc[tout["saison"] == saison, "journee_club"].max())
    if n_max > 1:
        periode = st.session_state.get("c_periode") or (1, n_max)
        st.session_state["c_periode"] = (max(1, min(periode[0], n_max)),
                                         max(1, min(periode[1], n_max)))
        journees = c.slider("Période (matchs du club dans la saison)", 1, n_max,
                            key="c_periode")
        if journees == (1, n_max):
            journees = None

r = filtrer_resultats(tout, saison=None if saison == TOUTES else saison, lieu=lieu,
                      journees=journees)
actifs = [f"Saison : {saison}"] + ([f"Lieu : {lieu}"] if lieu != "Tous" else []) + \
    ([f"Matchs {journees[0]} à {journees[1]}"] if journees else [])
g, d = st.columns([5, 1])
g.markdown("Filtres actifs : " + "".join(f"<span class='puce'>{x}</span>" for x in actifs),
           unsafe_allow_html=True)


def reinitialiser() -> None:  # rappel exécuté avant le prochain affichage des filtres
    for k, v in cles.items():
        st.session_state[k] = v


d.button("Réinitialiser", icon=":material/restart_alt:", width="stretch",
         on_click=reinitialiser, disabled=not actifs[1:] and saison == defaut)

if r.empty:
    st.info("Aucun match ne correspond à ces filtres.")
    st.stop()

# ------------------------------------------------------------------- bilan
bl = bilan(r)
rang_txt, rang_det = "—", "classement calculé sur une seule saison"
if saison != TOUTES:
    t = classement(resultats, saison, lieu=lieu, journees=journees)
    if club in t.index:
        rang_txt = f"{int(t.loc[club, 'Rang'])}e"
        rang_det = f"sur {len(t)} clubs" + (" (sélection filtrée)" if actifs[1:] else "")
cartes([("Matchs", f"{bl.matchs}", f"{bl.victoires} V · {bl.nuls} N · {bl.defaites} D"),
        ("Points", f"{bl.points}", f"{nombre(bl.par_match(bl.points))} par match"),
        ("Classement", rang_txt, rang_det),
        ("Différence de buts", f"{bl.difference:+d}",
         f"{bl.buts_pour} marqués · {bl.buts_contre} encaissés")])
st.write("")
cartes([("Victoires", f"{bl.taux(bl.victoires):.0%}".replace("%", " %"),
         f"{bl.victoires} sur {bl.matchs} matchs"),
        ("Buts marqués / match", nombre(bl.par_match(bl.buts_pour)),
         f"sans marquer : {bl.sans_marquer} match(s)"),
        ("Buts encaissés / match", nombre(bl.par_match(bl.buts_contre)),
         f"sans encaisser : {bl.sans_encaisser} match(s)"),
        ("Titres", f"{titres}", "champion depuis 2016 (classements officiels RSSSF)")])

# --------------------------------------------------- tendance et prochains
section("Dynamique", "Forme récente et prochains matchs")
gauche, droite = st.columns(2)
with gauche, st.container(border=True):
    st.markdown("**Forme : 5 derniers matchs de la sélection** (le plus récent à droite)")
    st.markdown(serie_html(list(r["issue"].tail(5))), unsafe_allow_html=True)
    td = tendance(r)
    if td is None:
        st.caption("Tendance : données insuffisantes (au moins 10 matchs nécessaires pour "
                   "comparer les 5 derniers au reste de la sélection).")
    else:
        sens = "en hausse" if td["ecart"] > 0.25 else "en baisse" if td["ecart"] < -0.25 \
            else "stable"
        st.markdown(f"Tendance **{sens}** : {nombre(td['recent'])} pts/match sur les 5 "
                    f"derniers contre {nombre(td['avant'])} avant.")
        st.caption("Écart descriptif sur un petit nombre de matchs : il ne permet pas de "
                   "conclure à un changement de niveau.")
with droite, st.container(border=True):
    st.markdown("**Prochains matchs**")
    prochains = prochains_matchs(matchs, club)
    if prochains.empty:
        st.caption("Aucun match à jouer publié pour ce club.")
    probas = a_venir.set_index("id_match") if a_venir is not None else pd.DataFrame()
    for m in prochains.itertuples():
        domicile = m.dom == club
        adv = m.ext if domicile else m.dom
        quand = pd.Timestamp(m.date_match).strftime("%d/%m/%Y") if pd.notna(m.date_match) \
            else "date non confirmée"
        ligne = f"{quand} · {'reçoit' if domicile else 'chez'} **{adv}**"
        if m.id_match in probas.index:
            p = probas.loc[m.id_match]
            v, n_, d_ = (p.p_dom, p.p_nul, p.p_ext) if domicile else (p.p_ext, p.p_nul, p.p_dom)
            ligne += f" — victoire {v:.0%} · nul {n_:.0%} · défaite {d_:.0%}"
        st.markdown(ligne)
    if len(prochains):
        st.page_link("vues/prediction.py", label="Probabilités expliquées (modèle Elo)",
                     icon=":material/online_prediction:")

# ---------------------------------------------------------------- évolution
if saison != TOUTES:
    section("Évolution", f"Course aux points — {saison}",
            "Points cumulés match après match, comparés au leader et à la moyenne des clubs "
            "(tous lieux confondus, toute la saison).")
    s_all = resultats[resultats["saison"] == saison].sort_values("date_match").copy()
    s_all["cumul"] = s_all.groupby("club")["points"].cumsum()
    final = s_all.groupby("club")["cumul"].last().sort_values(ascending=False)
    leader = final.index[0] if final.index[0] != club else (
        final.index[1] if len(final) > 1 else None)
    moyenne = s_all.groupby("journee_club")["cumul"].mean()
    fig = go.Figure()
    fig.add_scatter(x=moyenne.index, y=moyenne, name="Moyenne des clubs",
                    line={"color": GRIS, "dash": "dot"},
                    hovertemplate="Match %{x} : %{y:.1f} pts<extra>Moyenne</extra>")
    if leader:
        lc = s_all[s_all["club"] == leader]
        fig.add_scatter(x=lc["journee_club"], y=lc["cumul"], name=f"{leader} (1er)"
                        if final.index[0] == leader else leader,
                        line={"color": VERT, "width": 2},
                        hovertemplate="Match %{x} : %{y} pts<extra>" + leader + "</extra>")
    cc = s_all[s_all["club"] == club]
    sel = cc["id_match"].isin(r["id_match"])
    fig.add_scatter(x=cc["journee_club"], y=cc["cumul"], name=club, mode="lines+markers",
                    line={"color": ORANGE, "width": 3},
                    marker={"size": [9 if s else 5 for s in sel],
                            "color": [ORANGE if s else LIGNE for s in sel]},
                    customdata=cc[["adversaire", "bp", "bc"]],
                    hovertemplate="Match %{x} : %{y} pts<br>%{customdata[1]}-%{customdata[2]} "
                                  "contre %{customdata[0]}<extra>" + club + "</extra>")
    fig.update_layout(height=360, margin={"l": 0, "r": 0, "t": 10, "b": 0},
                      xaxis_title="Match du club dans la saison", yaxis_title="Points cumulés",
                      legend={"orientation": "h", "y": 1.12})
    st.plotly_chart(fig, width="stretch")
    if actifs[1:]:
        st.caption("Points en couleur : matchs retenus par les filtres.")
else:
    section("Évolution", "Performances saison après saison")
    ppm = r.groupby("saison")["points"].agg(ppm="mean", matchs="size").reset_index()
    fig = px.bar(ppm, x="saison", y="ppm", text_auto=".2f", color_discrete_sequence=[ORANGE],
                 hover_data={"matchs": True})
    fig.update_traces(textfont_color="white",
                      hovertemplate="%{x} : %{y:.2f} pts/match (%{customdata[0]} matchs)"
                                    "<extra></extra>")
    fig.update_layout(height=300, margin={"l": 0, "r": 0, "t": 10, "b": 0}, xaxis_title=None,
                      yaxis_title="Points par match")
    st.plotly_chart(fig, width="stretch")
    rangs = []
    for s in sorted(tout["saison"].unique()):
        if s == saison_actuelle:  # saison qui débute : rang pas encore significatif
            continue
        f = classement_final(classement_j, s)
        ligne = f[f["club"] == club]
        if len(ligne):
            rangs.append({"saison": s, "rang": int(ligne["rang_final"].iloc[0])})
    if rangs:
        fig = px.line(rangs, x="saison", y="rang", markers=True, text="rang",
                      color_discrete_sequence=[ORANGE])
        fig.update_traces(textposition="top center")
        fig.update_yaxes(autorange="reversed", dtick=2, title="Rang final")
        fig.update_layout(height=300, margin={"l": 0, "r": 0, "t": 10, "b": 0},
                          xaxis_title=None)
        st.plotly_chart(fig, width="stretch")
        st.caption("Rang final recalculé à partir des matchs ; saison en cours exclue.")

# -------------------------------------------- domicile / extérieur et buts
gauche, droite = st.columns(2)
with gauche:
    st.markdown("**Résultats à domicile et à l'extérieur** (sélection)")
    lieux = r.assign(Lieu=r["a_domicile"].map({True: "Domicile", False: "Extérieur"}))
    rep = lieux.groupby(["Lieu", "issue"]).size().unstack(fill_value=0)
    effectifs = rep.sum(axis=1)
    rep = rep.div(effectifs, axis=0).reindex(columns=["V", "N", "D"], fill_value=0)
    fig = go.Figure()
    for issue, couleur, nom in (("V", VERT, "Victoire"), ("N", GRIS, "Nul"),
                                ("D", ROUGE, "Défaite")):
        fig.add_bar(y=[f"{x} ({effectifs[x]} m.)" for x in rep.index], x=rep[issue], name=nom,
                    orientation="h", marker_color=couleur, textfont={"color": "white"},
                    text=(rep[issue] * 100).round().astype(int).astype(str) + " %",
                    hovertemplate=nom + " : %{x:.0%}<extra></extra>")
    fig.update_layout(barmode="stack", height=260, xaxis_tickformat=".0%",
                      margin={"l": 0, "r": 0, "t": 10, "b": 0},
                      legend={"orientation": "h", "y": 1.2})
    st.plotly_chart(fig, width="stretch")
with droite:
    st.markdown("**Buts marqués et encaissés par saison** (sélection)")
    par_saison = r.groupby("saison")[["bp", "bc"]].sum().reset_index()
    fig = go.Figure()
    fig.add_bar(x=par_saison["saison"], y=par_saison["bp"], name="Marqués", marker_color=VERT)
    fig.add_bar(x=par_saison["saison"], y=par_saison["bc"], name="Encaissés",
                marker_color=ORANGE)
    fig.update_layout(barmode="group", height=260, margin={"l": 0, "r": 0, "t": 10, "b": 0},
                      legend={"orientation": "h", "y": 1.2}, yaxis_title="Buts")
    st.plotly_chart(fig, width="stretch")

# --------------------------------------------------------------- matchs
section("Matchs", "Résultats de la sélection",
        "Cliquer sur une ligne pour ouvrir la fiche du match.")
liste = r.sort_values("date_match", ascending=False).assign(
    Lieu=lambda x: x["a_domicile"].map({True: "Domicile", False: "Extérieur"}),
    Score=lambda x: x["bp"].astype(str) + " - " + x["bc"].astype(str),
    Date=lambda x: pd.to_datetime(x["date_match"]))
choix_match = st.dataframe(
    liste[["Date", "saison", "Lieu", "adversaire", "Score", "issue", "points"]],
    hide_index=True, height=320, on_select="rerun", selection_mode="single-row",
    key=f"liste_{club}_{saison}_{lieu}_{journees}",
    column_config={"Date": st.column_config.DateColumn(format="DD/MM/YYYY"),
                   "saison": "Saison", "adversaire": "Adversaire", "issue": "Résultat",
                   "points": "Points"})
if choix_match.selection.rows:
    st.switch_page("vues/matchs.py", query_params={
        "match": str(liste.iloc[choix_match.selection.rows[0]]["id_match"])})

section("Adversaires", "Bilan face à chaque adversaire",
        "Sur la sélection filtrée. Peu de confrontations par adversaire : à lire comme un "
        "historique, pas comme une mesure de niveau.")
adv = bilan_adversaires(r).reset_index()
st.dataframe(adv, hide_index=True, height=300, column_config={
    "adversaire": "Adversaire", "matchs": "Matchs", "bp": "Buts pour", "bc": "Buts contre",
    "points": "Points",
    "ppm": st.column_config.ProgressColumn("Points / match", min_value=0, max_value=3,
                                           format="%.2f")})

# ---------------------------------------------------------------- joueurs
section("Joueurs", "Les meilleurs joueurs offensifs du club",
        "Note de contribution offensive sur 10 (saisons 2022-23 → 2024-25) : "
        "cliquer sur un joueur pour ouvrir sa fiche.")
notes = charger("joueurs")
notes = notes[notes["club"] == club]
if saison != TOUTES and saison in set(notes["saison"]):
    notes = notes[notes["saison"] == saison]
notes = notes.sort_values("note", ascending=False).head(8)
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

b = buteurs[buteurs["club"] == club].sort_values(["saison", "buts"], ascending=[False, False])
if len(b):
    with st.expander("Meilleurs buteurs publiés (Wikipédia, API-Football), depuis 2016"):
        st.dataframe(b[["saison", "joueur", "buts", "source"]]
                     .rename(columns=str.capitalize), hide_index=True, width="stretch")
pied_de_page()

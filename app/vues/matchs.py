import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from commun import (
    COULEURS_RESULTAT,
    GRIS,
    ORANGE,
    SAISONS_EVENEMENTS,
    VERT,
    charger,
    charger_modele,
    club_html,
    configurer,
    entete,
    pastille,
    pied_de_page,
    serie_html,
)
from indicateurs import phase, voisins

configurer()
entete("Matchs", "La fiche de chaque match : score, déroulé minute par minute, contexte "
       "avant la rencontre et historique des confrontations.")

matchs = charger("matchs")
matchs = matchs[matchs["statut"] == "joue"].copy()
matchs["date_match"] = pd.to_datetime(matchs["date_match"])
resultats = charger("resultats_club")
classement = charger("classement_journee")
buts = charger("buts_match")
cartons = charger("cartons")
predictions = charger_modele("predictions_test")

# ------------------------------------------------------------- sélection
# Un match demandé dans l'URL (lien depuis une autre page) prime sur les filtres
TOUS = "Tous les clubs"
demande = st.query_params.get("match")
choisi = matchs[matchs["id_match"].astype(str) == demande]
if len(choisi) and demande != st.session_state.get("match_affiche"):
    st.session_state["m_saison"] = choisi["saison"].iloc[0]
    st.session_state["m_club"] = TOUS
    st.session_state["m_match"] = int(choisi["id_match"].iloc[0])

saisons = sorted(matchs["saison"].unique(), reverse=True)
a, b, c = st.columns([1, 1.3, 2.4])
saison = a.selectbox("Saison", saisons, key="m_saison")
du_choix = matchs[matchs["saison"] == saison]
clubs = [TOUS] + sorted(set(du_choix["dom"]) | set(du_choix["ext"]))
if st.session_state.get("m_club") not in clubs:
    st.session_state["m_club"] = TOUS
club = b.selectbox("Club", clubs, key="m_club")
if club != TOUS:
    du_choix = du_choix[(du_choix["dom"] == club) | (du_choix["ext"] == club)]
du_choix = du_choix.sort_values("date_match", ascending=False)


def libelle(m) -> str:
    j = f"J{int(m.journee)} · " if pd.notna(m.journee) else ""
    return (f"{j}{m.date_match:%d/%m/%Y} · {m.dom} {int(m.buts_dom)}-{int(m.buts_ext)} "
            f"{m.ext}")


ids = [int(i) for i in du_choix["id_match"]]
if not ids:
    st.info("Aucun match pour ce choix.")
    st.stop()
if st.session_state.get("m_match") not in ids:
    st.session_state["m_match"] = ids[0]
libelles = {int(m.id_match): libelle(m) for m in du_choix.itertuples()}
id_match = c.selectbox("Match", ids, format_func=libelles.get, key="m_match")
st.session_state["match_affiche"] = str(id_match)
st.query_params["match"] = str(id_match)
m = matchs.set_index("id_match").loc[id_match]


def aller(cible: int) -> None:
    st.session_state["m_match"] = cible


# Match précédent / suivant : dans la saison, ou parmi ceux du club filtré
precedent, suivant = voisins(matchs, id_match, None if club == TOUS else club)
g, _, d = st.columns([1, 2, 1])
g.button("Match précédent", icon=":material/arrow_back:", disabled=precedent is None,
         on_click=aller, args=(precedent,), width="stretch",
         help=libelles.get(precedent) if precedent else "Premier match de la sélection")
d.button("Match suivant", icon=":material/arrow_forward:", disabled=suivant is None,
         on_click=aller, args=(suivant,), width="stretch",
         help=libelles.get(suivant) if suivant else "Dernier match de la sélection")

# ---------------------------------------------------------------- affiche
issue = {"D": f"Victoire de {m.dom}", "N": "Match nul", "E": f"Victoire de {m.ext}"}[m.resultat]
journee = f"Journée {int(m.journee)} · " if pd.notna(m.journee) else ""
lieu = f" · {m.stade}" if pd.notna(m.stade) else ""
st.markdown(f"""
<div class="affiche">
  <div class="meta">{m.saison} · Ligue 1 · {phase(m.phase)} · {journee}{m.date_match:%d/%m/%Y}{lieu}</div>
  <div class="ligne">
    <div class="equipe">{pastille(m.dom, 64)}<span>{m.dom}</span></div>
    <div class="score">{int(m.buts_dom)} – {int(m.buts_ext)}</div>
    <div class="equipe">{pastille(m.ext, 64)}<span>{m.ext}</span></div>
  </div>
  <div class="issue">{issue}</div>
</div>""", unsafe_allow_html=True)

b_match = buts[buts["id_match"] == id_match].sort_values("minute", kind="stable")
c_match = cartons[cartons["id_match"] == id_match]
onglets = st.tabs(["Déroulé", "Statistiques", "Avant le match", "Face-à-face"])

# ------------------------------------------------------------ statistiques
with onglets[1]:
    # « Non publié » n'est jamais remplacé par 0 : une donnée absente n'est pas une valeur
    NP = "Non publié"
    deroule = not b_match.empty or (m.buts_dom + m.buts_ext == 0 and
                                    m.saison in set(buts["saison"]))
    rouges = c_match[c_match["couleur"].isin(["rouge", "jaune_rouge"])]
    lignes = [("Buts", int(m.buts_dom), int(m.buts_ext), "RSSSF / Wikipédia"),
              ("dont penalties", *((int(((b_match["club"] == eq) &
                                         (b_match["type_but"] == "penalty")).sum())
                                    for eq in (m.dom, m.ext)) if not b_match.empty
                                   else (NP, NP)), "API-Football"),
              ("Cartons rouges", *((int((rouges["club"] == eq).sum()) for eq in (m.dom, m.ext))
                                   if deroule else (NP, NP)), "API-Football")]
    lignes += [(nom, NP, NP, "—") for nom in
               ("Possession", "Tirs", "Tirs cadrés", "Corners", "Cartons jaunes",
                "Compositions et remplacements", "Formation")]
    st.dataframe(pd.DataFrame(lignes, columns=["Statistique", m.dom, m.ext, "Source"])
                 .astype({m.dom: str, m.ext: str}), hide_index=True, width="stretch")
    st.caption("API-Football et les autres sources gratuites ne publient ni compositions, "
               "ni statistiques d'équipe pour la Ligue 1 ivoirienne (couverture vérifiée "
               "saison par saison : `python -m src.collecte.scrapers.api_football`). "
               "Sportmonks : la Ligue 1 ivoirienne n'est pas dans l'offre gratuite. "
               "Les champs apparaîtront dès qu'une source les fournira (docs/sources.md).")

# ---------------------------------------------------------------- déroulé
with onglets[0]:
    if m.buts_dom + m.buts_ext == 0:
        st.info("Aucun but dans ce match.")
    elif b_match.empty:
        st.info(f"Déroulé non disponible : les évènements match par match ne sont publiés "
                f"que pour les saisons {SAISONS_EVENEMENTS} (API-Football), et pas pour "
                "tous les matchs.")
    else:
        complet = bool(b_match["complet"].all())
        if not complet:
            st.warning("Le déroulé publié ne redonne pas exactement le score final : "
                       "il est affiché tel quel, sans buts décisifs.")
        evenements = [("but", r) for r in b_match.itertuples()] + \
                     [("carton", r) for r in c_match.itertuples()]
        evenements.sort(key=lambda e: (e[1].minute if pd.notna(e[1].minute) else 999))
        lignes = []
        for genre, e in evenements:
            minute = f"{int(e.minute)}'" if pd.notna(e.minute) else "—"
            if genre == "but":
                nom = e.buteur if pd.notna(e.buteur) else "Buteur non renseigné"
                details = {"penalty": " (pen.)", "contre_son_camp": " (c.s.c.)"}.get(
                    e.type_but, "")
                score = f"{int(e.score_dom)}-{int(e.score_ext)}"
                texte = (f"⚽ <b>{nom}</b>{details} <span class='sc'>{score}"
                         f"{' · décisif' if e.decisif else ''}</span>")
            else:
                texte = f"🟥 {e.joueur if pd.notna(e.joueur) else 'Joueur non renseigné'}"
            dom = e.club == m.dom
            lignes.append(f"<div class='dom'>{texte if dom else ''}</div>"
                          f"<div class='min'>{minute}</div>"
                          f"<div>{'' if dom else texte}</div>")
        gauche, droite = st.columns([1.1, 1])
        with gauche:
            st.markdown(f"<div class='chrono'><div class='dom'>{club_html(m.dom, 24)}</div>"
                        f"<div></div><div>{club_html(m.ext, 24)}</div>{''.join(lignes)}</div>",
                        unsafe_allow_html=True)
        with droite:
            # Écart au score minute par minute (positif : avantage à l'équipe à domicile)
            t = b_match.dropna(subset=["minute"])
            x = [0] + [v for v in t["minute"] for _ in (0, 1)] + [max(90, t["minute"].max())]
            ecart = (t["score_dom"] - t["score_ext"]).tolist()
            y = [0] + [v for pair in zip([0] + ecart[:-1], ecart, strict=True)
                       for v in pair] + [ecart[-1] if ecart else 0]
            fig = go.Figure()
            fig.add_scatter(x=x, y=y, mode="lines", line={"color": ORANGE, "width": 3},
                            fill="tozeroy", fillcolor="rgba(224,112,0,.12)", hoverinfo="skip")
            fig.add_scatter(x=t["minute"], y=ecart, mode="markers",
                            marker={"size": 11, "color": [ORANGE if d else VERT for d in
                                                          t["club"] == m.dom],
                                    "line": {"color": "white", "width": 2}},
                            customdata=t[["buteur", "score_dom", "score_ext"]].fillna("?"),
                            hovertemplate="%{x}' · %{customdata[0]}<br>Score "
                                          "%{customdata[1]}-%{customdata[2]}<extra></extra>")
            fig.add_hline(y=0, line_color=GRIS, line_width=1)
            fig.update_layout(height=300, showlegend=False, margin={"l": 0, "r": 0, "t": 30,
                                                                   "b": 0},
                              title={"text": "Écart au score", "font": {"size": 14}},
                              xaxis={"title": "Minute", "range": [0, x[-1] + 2], "dtick": 15},
                              yaxis={"title": f"+ : {m.dom} devant", "dtick": 1,
                                     "zeroline": False})
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        noms = b_match.dropna(subset=["joueur"]).drop_duplicates("joueur")
        if len(noms):
            st.caption("Fiches des buteurs :")
            cols = st.columns(min(len(noms), 4))
            for i, r in enumerate(noms.itertuples()):
                cols[i % len(cols)].page_link(
                    "vues/joueurs.py", label=r.buteur, icon=":material/person:",
                    query_params={"saison": r.saison, "joueur": r.joueur})

# --------------------------------------------------------- avant le match
with onglets[2]:
    avant = resultats[resultats["date_match"] < m.date_match.date()] \
        .sort_values("date_match")

    def contexte(equipe: str):
        r = avant[(avant["club"] == equipe) & (avant["saison"] == m.saison)]
        rang = classement[(classement["saison"] == m.saison) & (classement["club"] == equipe)
                          & (classement["journee"] == len(r))]
        forme = avant[avant["club"] == equipe].tail(5)
        return r, (int(rang["rang"].iloc[0]) if len(rang) and len(r) else None), forme

    cols = st.columns(2)
    for col, equipe in zip(cols, (m.dom, m.ext), strict=True):
        r, rang, forme = contexte(equipe)
        with col.container(border=True):
            st.markdown(club_html(equipe, 30), unsafe_allow_html=True)
            st.markdown(f"**{f'{rang}e' if rang else '—'}** au classement · "
                        f"**{int(r['points'].sum())} pts** en {len(r)} matchs cette saison")
            st.markdown("Forme (5 derniers matchs, le plus récent à droite)")
            if len(forme):
                st.markdown(serie_html(list(forme["issue"])), unsafe_allow_html=True)
            else:
                st.caption("Premier match dans les données.")

    p = predictions[predictions["id_match"] == id_match] if predictions is not None else []
    if len(p):
        p = p.iloc[0]
        st.markdown("**Probabilités du modèle Elo avant le match** (saison de test)")
        fig = go.Figure()
        for v, cle, nom in ((p.elo_p_D, "D", m.dom), (p.elo_p_N, "N", "Nul"),
                            (p.elo_p_E, "E", m.ext)):
            fig.add_bar(x=[v], y=[""], orientation="h", text=f"{nom}<br>{v:.0%}",
                        marker_color=COULEURS_RESULTAT[cle], textposition="inside",
                        insidetextanchor="middle", textfont={"color": "white"},
                        marker_line={"color": "white", "width": 2}, hoverinfo="skip")
        fig.update_layout(barmode="stack", height=80, showlegend=False,
                          margin={"l": 0, "r": 0, "t": 0, "b": 0},
                          xaxis={"visible": False, "range": [0, 1]}, yaxis={"visible": False})
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    else:
        st.caption("Probabilités d'avant-match disponibles pour la saison de test 2025-26 "
                   "(page Prédiction pour la saison en cours).")

# ------------------------------------------------------------ face-à-face
with onglets[3]:
    duel = matchs[((matchs["dom"] == m.dom) & (matchs["ext"] == m.ext))
                  | ((matchs["dom"] == m.ext) & (matchs["ext"] == m.dom))] \
        .sort_values("date_match", ascending=False)
    gagnant = duel.apply(lambda r: r.dom if r.resultat == "D" else r.ext
                         if r.resultat == "E" else None, axis=1)
    v_dom, v_ext, nuls = (gagnant == m.dom).sum(), (gagnant == m.ext).sum(), gagnant.isna().sum()
    fig = go.Figure()
    for n, nom, couleur in ((v_dom, m.dom, ORANGE), (nuls, "Nuls", GRIS), (v_ext, m.ext, VERT)):
        fig.add_bar(x=[n], y=[""], orientation="h", marker_color=couleur,
                    text=f"{nom} · {n}", textposition="inside", insidetextanchor="middle",
                    textfont={"color": "white"}, hoverinfo="skip",
                    marker_line={"color": "white", "width": 2})
    fig.update_layout(barmode="stack", height=70, showlegend=False,
                      margin={"l": 0, "r": 0, "t": 0, "b": 0},
                      xaxis={"visible": False}, yaxis={"visible": False})
    st.markdown(f"**{len(duel)} confrontations en Ligue 1 depuis 2016**")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    tableau = duel.assign(Score=duel["buts_dom"].astype(int).astype(str) + " - "
                          + duel["buts_ext"].astype(int).astype(str))
    tableau = tableau.rename(columns={"date_match": "Date", "saison": "Saison",
                                      "dom": "Domicile", "ext": "Extérieur"})
    selection = st.dataframe(
        tableau[["Date", "Saison", "Domicile", "Score", "Extérieur"]], hide_index=True,
        on_select="rerun", selection_mode="single-row", key="face_a_face",
        column_config={"Date": st.column_config.DateColumn(format="DD/MM/YYYY")})
    st.caption("Cliquer sur une ligne pour ouvrir ce match.")
    if selection.selection.rows:
        autre = int(duel.iloc[selection.selection.rows[0]]["id_match"])
        if autre != id_match:
            st.query_params["match"] = str(autre)
            st.rerun()

st.caption(f"Déroulé : évènements API-Football ({SAISONS_EVENEMENTS}) ; seuls les cartons "
           "rouges y sont publiés de façon fiable. Scores : RSSSF, recoupés avec Wikipédia.")
pied_de_page()

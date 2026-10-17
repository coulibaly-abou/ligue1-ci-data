from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from commun import (
    GRIS,
    ORANGE,
    SAISONS_EVENEMENTS,
    cartes,
    charger,
    club_html,
    configurer,
    couleur_club,
    entete,
    nombre,
    note_html,
    pied_de_page,
    section,
)

configurer()
entete("Joueurs", "Qui fait gagner son équipe ? Buts, buts décisifs et note de contribution "
       f"offensive sur 10, pour chaque buteur des saisons {SAISONS_EVENEMENTS}.")

joueurs = charger("joueurs")
buts = charger("buts_match")
matchs = charger("matchs").set_index("id_match")
COMPOSANTES = {"buts": "Buts", "buts_decisifs": "Buts décisifs",
               "part_buts_club": "Poids dans l'attaque", "matchs_avec_but": "Régularité"}

# ------------------------------------------------------------- sélection
saisons = sorted(joueurs["saison"].unique(), reverse=True)
demande = st.query_params.get("saison")
if demande in saisons and demande != st.session_state.get("j_saison_url"):
    st.session_state["j_saison"] = demande
    st.session_state["j_saison_url"] = demande
a, b, c = st.columns([1, 1.4, 1.6])
saison = a.selectbox("Saison", saisons, key="j_saison")
s = joueurs[joueurs["saison"] == saison].copy()
for col in COMPOSANTES:  # rang-centile parmi les buteurs de la saison (0 à 100)
    s[f"pct_{col}"] = (s[col].rank(pct=True) * 100).round()
clubs = ["Tous les clubs"] + sorted(s["club"].unique())
club = b.selectbox("Club", clubs)
recherche = c.text_input("Rechercher un joueur", placeholder="ex. Kanté, Bedi…")
vue = s if club == clubs[0] else s[s["club"] == club]
if recherche:
    cible = recherche.lower()
    vue = vue[vue["nom"].str.lower().str.contains(cible, regex=False)
              | vue["nom_complet"].fillna("").str.lower().str.contains(cible, regex=False)]

total_saison = buts[buts["saison"] == saison]
cartes([("Buteurs", f"{len(s)}", f"au moins un but en {saison}"),
        ("Buts suivis", f"{len(total_saison)}",
         f"dont {int(total_saison['decisif'].sum())} décisifs (égalisent ou donnent l'avantage)"),
        ("Meilleur buteur", f"{int(s['buts'].max())}",
         s.loc[s["buts"].idxmax(), "nom"] + " · " + s.loc[s["buts"].idxmax(), "club"]),
        ("Note médiane", nombre(s["note"].median(), 1), "sur 10, parmi les buteurs")])

# -------------------------------------------------------------- podium
section("Classement", f"Les meilleurs joueurs offensifs — {saison}")
podium = vue.head(3)
for col, (i, j) in zip(st.columns(3), enumerate(podium.itertuples(), start=1), strict=False):
    with col.container(border=True):
        st.markdown(f"<div style='display:flex;justify-content:space-between;"
                    f"align-items:center'><div><div style='color:{ORANGE};font-weight:800'>"
                    f"#{i}</div><div style='font-size:1.15rem;font-weight:750'>{j.nom}</div>"
                    f"<div style='margin-top:.3rem'>{club_html(j.club, 22)}</div></div>"
                    f"{note_html(j.note, 54)}</div>"
                    f"<div style='color:#57606A;margin-top:.6rem'>{j.buts} buts · "
                    f"{int(j.buts_decisifs)} décisifs · {nombre(100 * j.part_buts_club, 0)} % "
                    "des buts du club</div>", unsafe_allow_html=True)

tableau = vue.assign(part=(100 * vue["part_buts_club"]).round(0),
                     poste=vue["poste"].fillna("—"))
selection = st.dataframe(
    tableau[["rang_saison", "note", "nom", "club", "poste", "buts", "buts_decisifs",
             "matchs_avec_but", "part", "penalties"]],
    hide_index=True, height=380, on_select="rerun", selection_mode="single-row",
    key=f"tableau_{saison}_{club}_{recherche}",  # sélection remise à zéro avec les filtres
    column_config={
        "rang_saison": st.column_config.NumberColumn("Rang", width="small"),
        "note": st.column_config.ProgressColumn("Note /10", min_value=0, max_value=10,
                                                format="%.1f"),
        "nom": "Joueur", "club": "Club", "poste": "Poste", "buts": "Buts",
        "buts_decisifs": "Décisifs", "matchs_avec_but": "Matchs avec but",
        "part": st.column_config.NumberColumn("% buts du club", format="%d %%"),
        "penalties": "Pen."})
st.caption("Cliquer sur une ligne pour ouvrir la fiche du joueur.")

# ------------------------------------------------------------ fiche joueur
cles = list(s["joueur"])
if selection.selection.rows:
    st.query_params["joueur"] = vue.iloc[selection.selection.rows[0]]["joueur"]
cle = st.query_params.get("joueur")
if cle not in cles:
    cle = vue["joueur"].iloc[0] if len(vue) else cles[0]
st.query_params["saison"] = saison
j = s.set_index("joueur").loc[cle]

section("Fiche joueur", j["nom_complet"] if pd.notna(j["nom_complet"]) else
        "Profil, note et buts de la saison")
infos = [j["poste"]] if pd.notna(j["poste"]) else []
if pd.notna(j["naissance"]):
    n = date.fromisoformat(j["naissance"])
    infos.append(f"{(date(int(saison[:4]) + 1, 1, 1) - n).days // 365} ans en {saison}")
if pd.notna(j["nationalite"]):
    infos.append(j["nationalite"])
puces = "".join(f"<span class='puce'>{x}</span>" for x in infos)
st.markdown(f"""
<div class="fiche">
  <span class="pastille" style="width:84px;height:84px;font-size:30px;
        background:{couleur_club(j['club'])}">{''.join(m[0] for m in j['nom'].split()[-2:])}</span>
  <div style="flex:1;min-width:220px">
    <div class="nom">{j['nom']}</div>
    <div class="sous">{club_html(j['club'], 22)}</div>
    <div>{puces}</div>
  </div>
  <div style="text-align:center">{note_html(j['note'], 78)}
    <div class="sous">{int(j['rang_saison'])}e sur {len(s)} buteurs</div></div>
</div>""", unsafe_allow_html=True)
st.write("")
cartes([("Buts", f"{j['buts']}", f"dont {j['penalties']} sur penalty"),
        ("Buts décisifs", f"{int(j['buts_decisifs'])}", "égalisent ou donnent l'avantage"),
        ("Poids dans l'attaque", f"{nombre(100 * j['part_buts_club'], 0)} %",
         f"des {int(j['buts_club'])} buts de {j['club']}"),
        ("Régularité", f"{j['matchs_avec_but']}", "matchs avec au moins un but")])

gauche, droite = st.columns(2)
with gauche:
    st.markdown("**Profil comparé aux buteurs de la saison**")
    axes = list(COMPOSANTES.values())
    valeurs = [j[f"pct_{c}"] for c in COMPOSANTES]
    fig = go.Figure()
    fig.add_scatterpolar(r=[50] * 5, theta=axes + axes[:1], mode="lines", name="Médiane",
                         line={"color": GRIS, "dash": "dot"}, hoverinfo="skip")
    fig.add_scatterpolar(r=valeurs + valeurs[:1], theta=axes + axes[:1], fill="toself",
                         name=j["nom"], line={"color": ORANGE, "width": 3},
                         fillcolor="rgba(224,112,0,.25)",
                         hovertemplate="%{theta} : meilleur que %{r:.0f} % des buteurs"
                                       "<extra></extra>")
    fig.update_layout(height=380, margin={"l": 90, "r": 90, "t": 30, "b": 20},
                      polar={"radialaxis": {"range": [0, 100], "ticksuffix": " %",
                                            "tickfont": {"size": 10}},
                             "bgcolor": "rgba(0,0,0,0)"},
                      legend={"orientation": "h", "y": -0.1})
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.caption("Rang-centile : 80 % = meilleur que 80 % des buteurs de la saison.")
with droite:
    st.markdown("**Quand marque-t-il ?**")
    tranches = ["0-15", "16-30", "31-45+", "46-60", "61-75", "76-90+"]

    def par_tranche(minutes: pd.Series) -> pd.Series:
        t = pd.cut(minutes.clip(upper=120), [0, 15, 30, 45.9, 60, 75, 130],
                   labels=tranches, include_lowest=True)
        return t.value_counts(normalize=True).reindex(tranches, fill_value=0)

    siens = buts[(buts["joueur"] == cle) & (buts["saison"] == saison)]
    ligue = buts[buts["saison"] == saison]
    fig = go.Figure()
    fig.add_bar(x=tranches, y=par_tranche(siens["minute"].dropna()), name=j["nom"],
                marker_color=ORANGE, hovertemplate="%{x}' : %{y:.0%} de ses buts<extra></extra>")
    fig.add_scatter(x=tranches, y=par_tranche(ligue["minute"].dropna()), name="Tous les buts",
                    mode="lines+markers", line={"color": GRIS, "dash": "dot"},
                    hovertemplate="%{x}' : %{y:.0%} des buts du championnat<extra></extra>")
    fig.update_layout(height=360, yaxis_tickformat=".0%", margin={"l": 0, "r": 0, "t": 20,
                                                                  "b": 0},
                      xaxis_title="Minute", legend={"orientation": "h", "y": 1.12})
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.caption("Remplace les zones d'activité : les positions sur le terrain ne sont pas "
               "publiées pour la Ligue 1 ivoirienne.")

st.markdown("**Ses buts, match par match**")
liste = siens.join(matchs[["date_match", "dom", "ext", "buts_dom", "buts_ext"]], on="id_match",
                   rsuffix="_m").sort_values(["date_match", "minute"])
for r in liste.itertuples():
    adversaire = r.ext if r.club == r.dom else r.dom
    lieu = "dom." if r.club == r.dom else "ext."
    texte = (f"{pd.Timestamp(r.date_match):%d/%m/%Y} · {int(r.minute) if pd.notna(r.minute) else '?'}"
             f"' contre {adversaire} ({lieu}) · score {int(r.score_dom)}-{int(r.score_ext)}"
             f"{' · penalty' if r.type_but == 'penalty' else ''}"
             f"{' · décisif' if r.decisif else ''}")
    st.page_link("vues/matchs.py", label=texte, icon=":material/sports_soccer:",
                 query_params={"match": str(r.id_match)})

autres = joueurs[(joueurs["joueur"] == cle) & (joueurs["saison"] != saison)]
if len(autres):
    st.markdown("**Ses autres saisons**")
    st.dataframe(autres[["saison", "club", "buts", "buts_decisifs", "note", "rang_saison"]]
                 .rename(columns={"saison": "Saison", "club": "Club", "buts": "Buts",
                                  "buts_decisifs": "Décisifs", "note": "Note /10",
                                  "rang_saison": "Rang"}), hide_index=True)

with st.expander("Comment est calculée la note sur 10 ?"):
    st.markdown(
        "La note mesure la **contribution offensive** d'un joueur dans sa saison, comparée "
        "aux autres buteurs de la même saison. Pour chaque critère, on calcule le "
        "rang-centile du joueur (0 = le plus faible, 1 = le meilleur), puis :\n\n"
        "**note = 10 × (35 % buts + 25 % buts décisifs + 20 % part des buts du club "
        "+ 20 % matchs avec un but) − 0,5 par carton rouge**\n\n"
        "- un **but décisif** égalise ou donne l'avantage à son équipe (calculé à partir "
        "du score minute par minute) ;\n"
        "- la **part des buts du club** mesure la dépendance de l'attaque au joueur.\n\n"
        "**Limites** : API-Football ne publie pour ce championnat ni le temps de jeu, ni "
        "les passes décisives, ni les actions défensives ; la note ne concerne donc que "
        "les buteurs et ne dit rien des défenseurs ou des gardiens. Le déroulé n'est publié "
        f"que pour une partie des matchs des saisons {SAISONS_EVENEMENTS} ; les buts sans "
        "nom de buteur ne sont attribués à personne. Profils (poste, âge, nationalité) "
        "retrouvés dans les effectifs API-Football quand le nom abrégé désigne un seul "
        "joueur du club.")
pied_de_page()

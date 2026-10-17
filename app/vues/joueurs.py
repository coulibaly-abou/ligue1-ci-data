from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from commun import (
    GRIS,
    ORANGE,
    ROUGE,
    SAISONS_EVENEMENTS,
    VERT,
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
from indicateurs import MALUS_ROUGE, POIDS, SEUIL_NOTE

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
a, b, p, c = st.columns([1, 1.3, 1, 1.5])
saison = a.selectbox("Saison", saisons, key="j_saison")
s = joueurs[joueurs["saison"] == saison].copy()
for col in COMPOSANTES:  # rang-centile parmi les buteurs de la saison (0 à 100)
    s[f"pct_{col}"] = (s[col].rank(pct=True) * 100).round()
s["poste"] = s["poste"].fillna("Non renseigné")
s["fiabilite"] = (s["buts"] >= SEUIL_NOTE).map({True: "Suffisante",
                                                False: f"Indicative (< {SEUIL_NOTE} buts)"})
clubs = ["Tous les clubs"] + sorted(s["club"].unique())
club = b.selectbox("Club", clubs)
postes = ["Tous les postes"] + sorted(set(s["poste"]) - {"Non renseigné"}) + ["Non renseigné"]
poste = p.selectbox("Poste", postes, help="Poste connu pour les joueurs retrouvés dans les "
                    "effectifs API-Football (environ 1 buteur sur 5).")
recherche = c.text_input("Rechercher un joueur", placeholder="ex. Kanté, Bedi…")
fiables = st.toggle(f"Seulement les notes fiables (au moins {SEUIL_NOTE} buts)")
vue = s if club == clubs[0] else s[s["club"] == club]
if poste != postes[0]:
    vue = vue[vue["poste"] == poste]
if fiables:
    vue = vue[vue["buts"] >= SEUIL_NOTE]
if recherche:
    cible = recherche.lower()
    vue = vue[vue["nom"].str.lower().str.contains(cible, regex=False)
              | vue["nom_complet"].fillna("").str.lower().str.contains(cible, regex=False)]
actifs = [x for x in (club, poste) if x not in (clubs[0], postes[0])] + \
    ([f"≥ {SEUIL_NOTE} buts"] if fiables else []) + ([f"« {recherche} »"] if recherche else [])
st.markdown(f"Filtres actifs : <span class='puce'>{saison}</span>"
            + "".join(f"<span class='puce'>{x}</span>" for x in actifs)
            + f" · <b>{len(vue)}</b> joueur(s)", unsafe_allow_html=True)
if vue.empty:
    st.info("Aucun joueur ne correspond à ces filtres.")
    st.stop()

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
             "matchs_avec_but", "part", "penalties", "fiabilite"]],
    hide_index=True, height=380, on_select="rerun", selection_mode="single-row",
    # sélection remise à zéro avec les filtres
    key=f"tableau_{saison}_{club}_{poste}_{fiables}_{recherche}",
    column_config={
        "rang_saison": st.column_config.NumberColumn("Rang", width="small"),
        "note": st.column_config.ProgressColumn("Note /10", min_value=0, max_value=10,
                                                format="%.1f"),
        "nom": "Joueur", "club": "Club", "poste": "Poste", "buts": "Buts",
        "buts_decisifs": "Décisifs", "matchs_avec_but": "Matchs avec but",
        "part": st.column_config.NumberColumn("% buts du club", format="%d %%"),
        "penalties": "Pen.", "fiabilite": "Fiabilité de la note"})
st.caption("Cliquer sur une ligne pour ouvrir la fiche du joueur. Trier : cliquer sur "
           "l'en-tête d'une colonne.")

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
infos = [j["poste"]] if j["poste"] != "Non renseigné" else ["Poste non renseigné"]
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
if j["buts"] < SEUIL_NOTE:
    st.warning(f"Données insuffisantes : avec {j['buts']} but(s), la note est indicative. "
               "Un seul but de plus ou de moins la ferait varier fortement.",
               icon=":material/info:")

# Pourquoi cette note : contribution de chaque critère (poids × rang-centile × 10)
st.markdown("**Pourquoi cette note ?**")
contrib = pd.DataFrame({"critere": list(COMPOSANTES.values()),
                        "points": [10 * POIDS[c] * j[f"pct_{c}"] / 100 for c in COMPOSANTES],
                        "max": [10 * POIDS[c] for c in COMPOSANTES]})
fig = go.Figure()
fig.add_bar(y=contrib["critere"], x=contrib["max"], orientation="h", name="Maximum possible",
            marker_color="#F1F2F3", hoverinfo="skip")
fig.add_bar(y=contrib["critere"], x=contrib["points"], orientation="h", name="Points obtenus",
            marker_color=ORANGE, text=[nombre(v, 1) for v in contrib["points"]],
            textposition="outside", cliponaxis=False,
            hovertemplate="%{y} : %{x:.1f} pt<extra></extra>")
if j["rouges"]:
    fig.add_bar(y=["Cartons rouges"], x=[-MALUS_ROUGE * j["rouges"]], orientation="h",
                name="Malus", marker_color=ROUGE, text=[f"-{MALUS_ROUGE * j['rouges']:.1f}"],
                textposition="outside")
fig.update_layout(barmode="overlay", height=230, margin={"l": 0, "r": 30, "t": 10, "b": 0},
                  xaxis_title="Points sur la note", yaxis={"autorange": "reversed"},
                  legend={"orientation": "h", "y": 1.2})
st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
st.caption(f"Somme des barres orange{' moins le malus' if j['rouges'] else ''} = "
           f"{nombre(j['note'], 1)} / 10 (arrondi). Les barres grises indiquent le maximum de "
           "chaque critère.")

autres_cles = [k for k in s.sort_values("note", ascending=False)["joueur"] if k != cle]
noms = s.set_index("joueur")
compare = st.selectbox("Comparer avec", [None] + autres_cles,
                       format_func=lambda k: "— aucun joueur —" if k is None else
                       f"{noms.loc[k, 'nom']} ({noms.loc[k, 'club']}, "
                       f"{nombre(noms.loc[k, 'note'], 1)})")
k2 = noms.loc[compare] if compare else None

gauche, droite = st.columns(2)
with gauche:
    st.markdown("**Profil comparé aux buteurs de la saison**")
    axes = [v.replace(" dans ", "<br>dans ") for v in COMPOSANTES.values()]
    valeurs = [j[f"pct_{c}"] for c in COMPOSANTES]
    fig = go.Figure()
    fig.add_scatterpolar(r=[50] * 5, theta=axes + axes[:1], mode="lines", name="Médiane",
                         line={"color": GRIS, "dash": "dot"}, hoverinfo="skip")
    fig.add_scatterpolar(r=valeurs + valeurs[:1], theta=axes + axes[:1], fill="toself",
                         name=j["nom"], line={"color": ORANGE, "width": 3},
                         fillcolor="rgba(224,112,0,.25)",
                         hovertemplate="%{theta} : meilleur que %{r:.0f} % des buteurs"
                                       "<extra></extra>")
    if k2 is not None:
        v2 = [k2[f"pct_{c}"] for c in COMPOSANTES]
        fig.add_scatterpolar(r=v2 + v2[:1], theta=axes + axes[:1], fill="toself",
                             name=k2["nom"], line={"color": VERT, "width": 3},
                             fillcolor="rgba(0,107,69,.18)",
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
    if k2 is not None:
        siens2 = buts[(buts["joueur"] == compare) & (buts["saison"] == saison)]
        fig.add_bar(x=tranches, y=par_tranche(siens2["minute"].dropna()), name=k2["nom"],
                    marker_color=VERT,
                    hovertemplate="%{x}' : %{y:.0%} de ses buts<extra></extra>")
    fig.add_scatter(x=tranches, y=par_tranche(ligue["minute"].dropna()), name="Tous les buts",
                    mode="lines+markers", line={"color": GRIS, "dash": "dot"},
                    hovertemplate="%{x}' : %{y:.0%} des buts du championnat<extra></extra>")
    fig.update_layout(height=360, yaxis_tickformat=".0%", margin={"l": 0, "r": 0, "t": 20,
                                                                  "b": 0},
                      xaxis_title="Minute", legend={"orientation": "h", "y": 1.12})
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.caption("Remplace les zones d'activité : les positions sur le terrain ne sont pas "
               "publiées pour la Ligue 1 ivoirienne.")

if k2 is not None:
    st.markdown(f"**{j['nom']} et {k2['nom']} côte à côte**")
    colonnes = {"note": "Note /10", "rang_saison": "Rang", "buts": "Buts",
                "penalties": "Penalties", "buts_decisifs": "Buts décisifs",
                "matchs_avec_but": "Matchs avec but", "part_buts_club": "Part des buts du club",
                "rouges": "Cartons rouges", "minute_moyenne": "Minute moyenne des buts"}
    face = pd.DataFrame({j["nom"]: j[list(colonnes)], k2["nom"]: k2[list(colonnes)]})
    face.index = list(colonnes.values())
    face.loc["Part des buts du club"] = face.loc["Part des buts du club"].map(
        lambda v: f"{100 * v:.0f} %")
    face.loc["Minute moyenne des buts"] = face.loc["Minute moyenne des buts"].map(
        lambda v: f"{v:.0f}'" if pd.notna(v) else "Non disponible")
    st.dataframe(face.astype(str), width="stretch")

st.markdown("**Au fil de la saison : buts cumulés**")
fil = siens.join(matchs[["date_match"]], on="id_match")
fig = go.Figure()
for donnees, nom, couleur in ((fil, j["nom"], ORANGE),) + (
        ((buts[(buts["joueur"] == compare) & (buts["saison"] == saison)]
          .join(matchs[["date_match"]], on="id_match"), k2["nom"], VERT),)
        if k2 is not None else ()):
    d = donnees.sort_values(["date_match", "minute"])
    fig.add_scatter(x=pd.to_datetime(d["date_match"]), y=list(range(1, len(d) + 1)),
                    name=nom, mode="lines+markers", line={"shape": "hv", "color": couleur,
                                                          "width": 3},
                    hovertemplate="%{x|%d/%m/%Y} : %{y} but(s)<extra>" + nom + "</extra>")
fig.update_layout(height=280, margin={"l": 0, "r": 0, "t": 10, "b": 0},
                  yaxis_title="Buts cumulés", legend={"orientation": "h", "y": 1.15})
st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

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

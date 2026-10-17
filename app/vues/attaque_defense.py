import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from commun import (
    GRIS,
    ORANGE,
    SAISONS_EVENEMENTS,
    VERT,
    cartes,
    charger,
    club_html,
    configurer,
    couleur_club,
    entete,
    nombre,
    parametre,
    pied_de_page,
    section,
)
from indicateurs import LIEUX, filtrer_resultats

configurer()
entete("Attaque & Défense", "Comment chaque club marque et encaisse : efficacité offensive, "
       "solidité défensive, saison par saison et minute par minute.")

resultats = charger("resultats_club")
buts = charger("buts_match")
matchs = charger("matchs").set_index("id_match")

lieu = st.segmented_control("Lieu des matchs", LIEUX, default="Tous", key="ad_lieu") or "Tous"
resultats = filtrer_resultats(resultats, lieu=lieu)
par_saison = resultats.groupby(["saison", "club"]).agg(
    matchs=("bp", "size"), bp=("bp", "mean"), bc=("bc", "mean"), points=("points", "mean"),
    clean_sheets=("bc", lambda s: (s == 0).mean()),
    sans_marquer=("bp", lambda s: (s == 0).mean())).reset_index()
par_saison = par_saison[par_saison["matchs"] >= 5]  # moins de 5 matchs : pas de moyenne
st.caption(("Tous les matchs" if lieu == "Tous" else f"Matchs à {lieu.lower()} seulement"
            .replace("à extérieur", "à l'extérieur"))
           + " · clubs avec au moins 5 matchs dans la sélection. Tirs, tirs cadrés et "
           "expected goals (xG) : non publiés pour ce championnat, donc absents (et non nuls).")

saisons = sorted(par_saison["saison"].unique(), reverse=True)
saison = st.selectbox("Saison", saisons,
                      index=saisons.index(parametre("saison", saisons, saisons[1])))
s = par_saison[par_saison["saison"] == saison].copy()
moy_bp, moy_bc = s["bp"].mean(), s["bc"].mean()

meilleure_att = s.loc[s["bp"].idxmax()]
meilleure_def = s.loc[s["bc"].idxmin()]
cartes([("Meilleure attaque", nombre(meilleure_att["bp"]),
         f"buts par match · {meilleure_att['club']}"),
        ("Meilleure défense", nombre(meilleure_def["bc"]),
         f"buts encaissés par match · {meilleure_def['club']}"),
        ("Buts par match", nombre(2 * moy_bp), f"moyenne du championnat en {saison}"),
        ("Matchs sans encaisser", f"{s['clean_sheets'].mean():.0%}".replace("%", " %"),
         "en moyenne par club")])

# ------------------------------------------------------------- quadrant
section("Profil", "Attaque contre défense",
        "Chaque point est un club. À droite : marque beaucoup ; en haut : encaisse peu. "
        "Taille du point : points par match.")
fig = go.Figure()
fig.add_vline(x=moy_bp, line_color=GRIS, line_dash="dot")
fig.add_hline(y=moy_bc, line_color=GRIS, line_dash="dot")
x_min, x_max = s["bp"].min() - .1, s["bp"].max() + .1
y_min, y_max = s["bc"].min() - .1, s["bc"].max() + .1
for x, y, texte, ancre in ((x_max, y_min, "Efficace et solide", "right"),
                           (x_min, y_min, "Solide, peu de buts", "left"),
                           (x_max, y_max, "Spectaculaire mais friable", "right"),
                           (x_min, y_max, "En difficulté", "left")):
    fig.add_annotation(x=x, y=y, text=texte, showarrow=False, xanchor=ancre,
                       font={"color": GRIS, "size": 12})
fig.add_scatter(
    x=s["bp"], y=s["bc"], mode="markers+text", text=s["club"], textposition="top center",
    textfont={"size": 11},
    marker={"size": 14 + 14 * s["points"], "color": [couleur_club(c) for c in s["club"]],
            "opacity": .9, "line": {"color": "white", "width": 2}},
    customdata=s[["points", "clean_sheets", "sans_marquer", "matchs"]],
    hovertemplate="<b>%{text}</b><br>%{x:.2f} buts marqués / match<br>%{y:.2f} encaissés / "
                  "match<br>%{customdata[0]:.2f} points / match<br>Sans encaisser : "
                  "%{customdata[1]:.0%} · sans marquer : %{customdata[2]:.0%}<br>"
                  "%{customdata[3]} matchs<extra></extra>")
fig.update_layout(height=620, showlegend=False, margin={"l": 0, "r": 0, "t": 10, "b": 0},
                  xaxis_title="Buts marqués par match",
                  yaxis={"title": "Buts encaissés par match", "autorange": "reversed"})
st.plotly_chart(fig, width="stretch")

tableau = s.sort_values("points", ascending=False)
st.dataframe(
    tableau[["club", "matchs", "bp", "bc", "clean_sheets", "sans_marquer", "points"]],
    hide_index=True, width="stretch",
    column_config={
        "club": "Club", "matchs": "Matchs",
        "bp": st.column_config.NumberColumn("Marqués / match", format="%.2f"),
        "bc": st.column_config.NumberColumn("Encaissés / match", format="%.2f"),
        "clean_sheets": st.column_config.ProgressColumn("Sans encaisser", min_value=0,
                                                        max_value=1, format="percent"),
        "sans_marquer": st.column_config.ProgressColumn("Sans marquer", min_value=0,
                                                        max_value=1, format="percent"),
        "points": st.column_config.NumberColumn("Points / match", format="%.2f")})

# --------------------------------------------------------- club en détail
section("Club", "Évolution d'un club, saison après saison")
clubs = sorted(s["club"])
club = st.selectbox("Club", clubs, index=clubs.index(parametre(
    "club", clubs, "ASEC Mimosas" if "ASEC Mimosas" in clubs else clubs[0])))
st.query_params.update({"saison": saison, "club": club})
c = par_saison[par_saison["club"] == club]
gauche, droite = st.columns([3, 2])
with gauche:
    fig = go.Figure()
    fig.add_scatter(x=c["saison"], y=c["bp"], name="Marqués / match", mode="lines+markers",
                    line={"color": VERT, "width": 3})
    fig.add_scatter(x=c["saison"], y=c["bc"], name="Encaissés / match", mode="lines+markers",
                    line={"color": ORANGE, "width": 3})
    moyenne = par_saison.groupby("saison")["bp"].mean()
    fig.add_scatter(x=moyenne.index, y=moyenne, name="Moyenne du championnat",
                    line={"color": GRIS, "dash": "dot"}, mode="lines")
    fig.update_layout(height=360, margin={"l": 0, "r": 0, "t": 10, "b": 0},
                      yaxis_title="Buts par match", legend={"orientation": "h", "y": 1.12},
                      hovermode="x unified")
    st.plotly_chart(fig, width="stretch")
with droite:
    r = resultats[(resultats["club"] == club) & (resultats["saison"] == saison)]
    lieux = r.groupby("a_domicile")[["bp", "bc"]].mean().rename(
        index={True: "Domicile", False: "Extérieur"})
    st.markdown(club_html(club, 28), unsafe_allow_html=True)
    st.markdown(f"**{saison} · domicile et extérieur**")
    fig = go.Figure()
    fig.add_bar(x=lieux.index, y=lieux["bp"], name="Marqués", marker_color=VERT,
                text=[nombre(v) for v in lieux["bp"]], textposition="outside")
    fig.add_bar(x=lieux.index, y=lieux["bc"], name="Encaissés", marker_color=ORANGE,
                text=[nombre(v) for v in lieux["bc"]], textposition="outside")
    fig.update_layout(barmode="group", height=300, margin={"l": 0, "r": 0, "t": 10, "b": 0},
                      yaxis_title="Buts par match", legend={"orientation": "h", "y": 1.15})
    st.plotly_chart(fig, width="stretch")

# ------------------------------------------------------ minute par minute
section("Minute par minute", "À quel moment le club marque et encaisse",
        f"Matchs dont le déroulé est publié (saisons {SAISONS_EVENEMENTS}).")
tranches = ["0-15", "16-30", "31-45+", "46-60", "61-75", "76-90+"]
b = buts.dropna(subset=["minute"]).join(matchs[["dom", "ext"]], on="id_match")
b = b[(b["dom"] == club) | (b["ext"] == club)] if lieu == "Tous" else \
    b[b["dom" if lieu == "Domicile" else "ext"] == club]
saisons_ev = sorted(b["saison"].unique())
if not saisons_ev:
    st.info(f"Pas de déroulé publié pour {club} sur les saisons {SAISONS_EVENEMENTS}.")
else:
    b["tranche"] = pd.cut(b["minute"].clip(upper=120), [0, 15, 30, 45.9, 60, 75, 130],
                          labels=tranches, include_lowest=True)
    marques = b[b["club"] == club].groupby("tranche", observed=False).size()
    encaisses = b[b["club"] != club].groupby("tranche", observed=False).size()
    fig = go.Figure()
    fig.add_bar(y=tranches, x=marques.reindex(tranches), orientation="h", name="Marqués",
                marker_color=VERT, hovertemplate="%{y}' : %{x} buts marqués<extra></extra>")
    fig.add_bar(y=tranches, x=-encaisses.reindex(tranches), orientation="h",
                name="Encaissés", marker_color=ORANGE, customdata=encaisses.reindex(tranches),
                hovertemplate="%{y}' : %{customdata} buts encaissés<extra></extra>")
    limite = max(marques.max(), encaisses.max()) + 2
    fig.update_layout(barmode="relative", height=340, margin={"l": 0, "r": 0, "t": 10, "b": 0},
                      yaxis={"autorange": "reversed", "title": "Minute"},
                      xaxis={"range": [-limite, limite], "title": "← encaissés · marqués →"},
                      legend={"orientation": "h", "y": 1.12})
    st.plotly_chart(fig, width="stretch")
    fin = b["tranche"].isin(["76-90+"])
    st.caption(f"{len(b[b['club'] == club])} buts marqués et {len(b[b['club'] != club])} "
               f"encaissés sur {b['id_match'].nunique()} matchs ({', '.join(saisons_ev)}). "
               f"Dans le dernier quart d'heure : {int((fin & (b['club'] == club)).sum())} "
               f"marqués, {int((fin & (b['club'] != club)).sum())} encaissés.")
pied_de_page()

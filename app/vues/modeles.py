import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from commun import (
    GRIS,
    NOMS_MODELES,
    ORANGE,
    VERT,
    charger_modele,
    configurer,
    metriques,
    pied_de_page,
)

configurer()
st.title("Comparaison des modèles de prédiction")

m = metriques()
if m is None:
    st.warning("Résultats absents : lancer `make train` puis `make export`.")
    st.stop()
proto = m["protocole"]
st.markdown(f"""
**Cible** : résultat du match en 3 classes — victoire domicile (D), nul (N), victoire
extérieur (E). **{proto['n_variables']} variables** calculées uniquement avec l'information
disponible *avant* le match : score Elo, forme sur 5 et 10 matchs, buts marqués/encaissés
glissants, points et rang dans la saison, forme à domicile / à l'extérieur, jours de repos.

**Protocole temporel** (jamais de mélange aléatoire) : 2016-17 sert à initialiser l'Elo ;
validation glissante — chaque saison 2021-22 → 2025-26 est prédite par un modèle entraîné
sur les saisons précédentes ({proto['n_glissante']} matchs prédits au total). Modèle
retenu : **le plus simple** parmi ceux à moins de 0,002 de log-loss du meilleur sur
2021-2024 (écart négligeable devant l'incertitude). **Test final : saison 2025-26**
({proto['n_test']} matchs), jamais utilisée pour un choix.
""")

glis = charger_modele("validation_glissante")
glis["Modèle"] = glis["modele"].map(NOMS_MODELES)
moy = glis.groupby("Modèle")[["accuracy", "log_loss", "rps"]].mean().sort_values("log_loss")
test = {r["modele"]: r for r in m["resultats_test"]}
naif_glis = moy.loc[NOMS_MODELES["naif"]]

st.subheader("Résultats moyens de la validation glissante (5 saisons)")
c = st.columns(3)
meilleur = moy.index[0]
c[0].metric("Meilleur modèle", meilleur)
c[1].metric("Précision", f"{moy.iloc[0]['accuracy']:.1%}",
            f"{moy.iloc[0]['accuracy'] - naif_glis['accuracy']:+.1%} vs naïf")
c[2].metric("Log-loss", f"{moy.iloc[0]['log_loss']:.4f}",
            f"{moy.iloc[0]['log_loss'] - naif_glis['log_loss']:+.4f} vs naïf",
            delta_color="inverse")

gauche, droite = st.columns(2)
with gauche:
    d = moy.reset_index().sort_values("log_loss", ascending=False)
    couleurs = [GRIS if n == NOMS_MODELES["naif"] else ORANGE for n in d["Modèle"]]
    fig = go.Figure(go.Bar(x=d["log_loss"], y=d["Modèle"], orientation="h",
                           marker_color=couleurs, text=d["log_loss"].round(4)))
    fig.update_layout(height=340, xaxis={"title": "Log-loss moyenne (plus bas = mieux)",
                                         "range": [d["log_loss"].min() - 0.01,
                                                   d["log_loss"].max() + 0.005]},
                      margin={"l": 0, "r": 0, "t": 10, "b": 0})
    st.plotly_chart(fig, width="stretch")
with droite:
    fig = px.line(glis, x="saison_test", y="log_loss", color="Modèle", markers=True)
    fig.update_layout(height=340, xaxis={"title": "Saison prédite", "dtick": 1},
                      yaxis_title="Log-loss", margin={"l": 0, "r": 0, "t": 10, "b": 0},
                      legend={"font": {"size": 10}})
    st.plotly_chart(fig, width="stretch")

st.subheader("Test final — saison 2025-2026")
tab = pd.DataFrame(m["resultats_test"])
tab = tab[["libelle", "accuracy", "log_loss", "brier", "rps"]].sort_values("log_loss")
tab.columns = ["Modèle", "Précision", "Log-loss", "Brier", "RPS"]
st.dataframe(tab.style.format({"Précision": "{:.1%}", "Log-loss": "{:.4f}",
                               "Brier": "{:.4f}", "RPS": "{:.4f}"})
             .highlight_min(subset=["Log-loss", "Brier", "RPS"], color="#FFE0B8")
             .highlight_max(subset=["Précision"], color="#FFE0B8"),
             hide_index=True, width="stretch")
rep = m["repartition_test"]
st.caption(f"Saison de test atypique : {rep['E']:.0%} de victoires à l'extérieur contre "
           f"{rep['D']:.0%} à domicile — d'où la faible précision de « toujours domicile ».")

boot = m["bootstrap_vs_naif"]
lignes = []
for nom, b in boot.items():
    for cadre in ("glissante", "test"):
        lignes.append({"Modèle": NOMS_MODELES[nom], "cadre": cadre,
                       "écart": b[cadre]["ecart_moyen"], "bas": b[cadre]["ic95"][0],
                       "haut": b[cadre]["ic95"][1]})
bt = pd.DataFrame(lignes)
st.subheader("Le gain sur la référence naïve est-il réel ?")
st.caption("Écart de log-loss avec la référence naïve et intervalle de confiance à 95 % "
           "(bootstrap). En dessous de 0 = mieux que le naïf ; si l'intervalle ne touche pas "
           "0, le gain est significatif.")
fig = go.Figure()
for cadre, couleur, nom in (
        ("glissante", ORANGE, f"Validation glissante ({proto['n_glissante']} matchs)"),
        ("test", VERT, f"Test 2025-26 ({proto['n_test']} matchs)")):
    s = bt[bt["cadre"] == cadre]
    fig.add_scatter(x=s["écart"], y=s["Modèle"], mode="markers", name=nom,
                    marker={"size": 11, "color": couleur},
                    error_x={"type": "data", "symmetric": False,
                             "array": s["haut"] - s["écart"],
                             "arrayminus": s["écart"] - s["bas"]})
fig.add_vline(x=0, line_dash="dash", line_color=GRIS)
fig.update_layout(height=360, xaxis_title="Écart de log-loss vs naïf",
                  margin={"l": 0, "r": 0, "t": 10, "b": 0}, legend={"orientation": "h", "y": 1.1})
st.plotly_chart(fig, width="stretch")

gauche, droite = st.columns(2)
with gauche:
    st.subheader("Matrice de confusion (test)")
    choix = st.selectbox("Modèle", list(m["confusions"]), format_func=NOMS_MODELES.get,
                         index=list(m["confusions"]).index(m["modele_retenu"]))
    cm = pd.DataFrame(m["confusions"][choix])
    fig = px.imshow(cm, text_auto=True,
                    color_continuous_scale=["#FFFFFF", ORANGE])
    fig.update_layout(height=360, margin={"l": 0, "r": 0, "t": 10, "b": 0},
                      coloraxis_showscale=False)
    st.plotly_chart(fig, width="stretch")
    predits_n = int(cm["prédit N"].sum())
    bons_n = int(cm.loc["réel N", "prédit N"])
    st.caption(f"Lignes = résultat réel, colonnes = prédiction. Nuls prédits : {predits_n} "
               f"fois sur {int(cm.to_numpy().sum())}, dont {bons_n} justes — le nul est la "
               "classe la plus difficile.")
with droite:
    st.subheader("Calibration des probabilités")
    cal = charger_modele("calibration")
    choix_cal = st.selectbox("Modèle ", sorted(cal["modele"].unique()),
                             format_func=NOMS_MODELES.get,
                             index=sorted(cal["modele"].unique()).index(m["modele_retenu"]))
    cal = cal[cal["modele"] == choix_cal]
    fig = px.line(cal, x="proba_moyenne", y="frequence_observee", color="classe",
                  markers=True, color_discrete_map={"D": ORANGE, "N": GRIS, "E": VERT})
    fig.add_scatter(x=[0.1, 0.6], y=[0.1, 0.6], mode="lines", name="parfait",
                    line={"dash": "dash", "color": "black", "width": 1})
    fig.update_layout(height=360, xaxis_title="Probabilité prédite",
                      yaxis_title="Fréquence observée", margin={"l": 0, "r": 0, "t": 10, "b": 0})
    st.plotly_chart(fig, width="stretch")

st.subheader("Quelles variables comptent ?")
imp = charger_modele("importance_variables")
choix_imp = st.radio("Modèle", ["logreg", "foret", "mlp"], format_func=NOMS_MODELES.get,
                     horizontal=True)
i = imp[imp["modele"] == choix_imp].head(12).iloc[::-1]
fig = go.Figure(go.Bar(x=i["hausse_log_loss"], y=i["variable"], orientation="h",
                       marker_color=ORANGE, error_x={"type": "data", "array": i["ecart_type"]}))
fig.update_layout(height=420, xaxis_title="Hausse de la log-loss quand la variable est mélangée",
                  margin={"l": 0, "r": 0, "t": 10, "b": 0})
st.plotly_chart(fig, width="stretch")
st.caption("Importance par permutation sur la saison de test (30 répétitions).")

courbe = charger_modele("courbe_apprentissage_mlp")
if courbe is not None:
    with st.expander("Courbe d'apprentissage du réseau de neurones (arrêt anticipé)"):
        fig = px.line(courbe, x="epoque", y=["perte_entrainement", "perte_validation"],
                      color_discrete_sequence=[ORANGE, VERT])
        fig.update_layout(height=320, yaxis_title="Entropie croisée",
                          margin={"l": 0, "r": 0, "t": 10, "b": 0})
        st.plotly_chart(fig, width="stretch")
pied_de_page()

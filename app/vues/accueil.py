"""Page d'accueil : identité, carte des clubs, objectifs, méthodologie, résultats clés."""
import streamlit as st
from commun import (
    AUTEUR,
    FORMATION,
    NOMS_MODELES,
    PAGES,
    RECHERCHE,
    ROLE,
    carte_clubs,
    charger,
    configurer,
    kpis,
    lire_json,
    metriques,
    pied_de_page,
    section,
    villes_carte,
)

configurer()

matchs = charger("matchs")
joues = matchs[matchs["statut"] == "joue"]
palmares = charger("palmares")
clubs = charger("clubs")
resultats = charger("resultats_club")
mouvements = charger("reseau_mouvements")
m = metriques()
sources = lire_json("sources")

saisons_completes = int((joues.groupby("saison").size() >= 90).sum())
saisons_jouees = joues.groupby("saison").size()
premiere = saisons_jouees.index.min()
derniere = saisons_jouees[saisons_jouees >= 90].index.max()
en_cours = saisons_jouees.index.max()

# ------------------------------------------------------------------ bannière
st.markdown(f"""
<div class="hero">
  <div class="barre"></div>
  <div class="auteur">{AUTEUR}</div>
  <div class="role">{ROLE}</div>
  <div class="profil">{FORMATION}</div>
  <div class="titre">LIGUE 1 CÔTE D'IVOIRE</div>
  <div class="tag">Data · Statistics · Machine Learning</div>
  <div class="accroche">Une étude complète du championnat ivoirien : {saisons_completes}
  saisons collectées automatiquement, analysées et modélisées pour comprendre les
  performances des clubs et estimer le résultat des matchs.</div>
  <div class="recherche">{RECHERCHE}</div>
</div>""", unsafe_allow_html=True)

# --------------------------------------------------------------------- carte
section("Introduction", "Cartographie des clubs de la Ligue 1 Côte d'Ivoire",
        "Une première lecture géographique des clubs permet de visualiser leur "
        "répartition sur le territoire ivoirien.")
villes = villes_carte(clubs, resultats)
gauche, droite = st.columns([3, 1])
with gauche:
    st.plotly_chart(carte_clubs(villes, hauteur=760), width="stretch",
                    config={"displayModeBar": False, "scrollZoom": False})
with droite:
    st.markdown(f"**{len(clubs)} clubs · {len(villes)} villes**")
    for v in villes.sort_values(["n_clubs", "matchs"], ascending=False).itertuples():
        st.markdown(f"<div style='display:flex;justify-content:space-between;"
                    f"border-bottom:1px solid #EEE;padding:4px 0'><span>{v.ville}</span>"
                    f"<span style='color:#57606A'>{v.n_clubs} club"
                    f"{'s' if v.n_clubs > 1 else ''}</span></div>", unsafe_allow_html=True)
    st.caption("Survoler un point pour voir les clubs et leurs matchs. Coordonnées : "
               "articles Wikipédia des villes, collectés et contrôlés par le pipeline.")

# ------------------------------------------------------------ problématique
section("Problématique", "La question de départ")
st.markdown("<div class='question'>Que peuvent révéler les données publiques, dispersées, "
            "sur la Ligue 1 ivoirienne ? Et peut-on prédire le résultat d'un match mieux "
            "qu'une règle naïve ?</div>", unsafe_allow_html=True)

# --------------------------------------------------------------- objectifs
section("Objectifs de l'étude", "Ce que cherche à établir l'étude",
        "Analyser les performances des clubs de Ligue 1 Côte d'Ivoire, identifier les "
        "dynamiques sportives et construire des modèles statistiques et de Machine "
        "Learning permettant notamment d'étudier et de prédire les résultats des matchs.")
axes = [
    ("Analyse du championnat", "Classements recalculés, hiérarchie, équilibre, palmarès."),
    ("Performances des clubs", "Bilans, points par match, buts, évolution par saison."),
    ("Résultats et forme", "Forme récente, séries, avantage du terrain."),
    ("Réseau clubs et joueurs", "Mouvements de joueurs, centralité, communautés."),
    ("Prédiction des matchs", "Probabilités victoire / nul / défaite avant le match."),
    ("Comparaison des modèles", "Six modèles évalués en validation temporelle."),
    ("Variables importantes", "Ce qui pèse vraiment dans la prédiction."),
    ("Joueurs et matchs", "Fiches joueurs notées sur 10, déroulé minute par minute."),
]
for debut in (0, 4):
    rangee = enumerate(axes[debut:debut + 4], start=debut + 1)
    for col, (i, (nom, texte)) in zip(st.columns(4), rangee, strict=True):
        col.markdown(f"<div class='carte-axe'><div class='num'>{i:02d}</div>"
                     f"<div class='nom'>{nom}</div><div class='txt'>{texte}</div></div>",
                     unsafe_allow_html=True)
    st.write("")

# ------------------------------------------------------ pour qui (impact)
par_lieu = resultats.groupby(["club", "a_domicile"])["points"].mean().unstack()
par_lieu = par_lieu[resultats.groupby("club").size() >= 120]
club_ecart = (par_lieu[True] - par_lieu[False]).idxmin()
departs = mouvements[mouvements["depart_ligue1"].astype(bool)
                     & ~mouvements["arrivee_ligue1"].astype(bool)]
part_asec = (departs["depart"] == "ASEC Mimosas").mean()
titres_asec = int((palmares["champion"] == "ASEC Mimosas").sum())
pct_nuls = (joues["resultat"] == "N").mean()

section("Pourquoi c'est utile", "Des décisions fondées sur des faits",
        "Les données du championnat sont dispersées et presque jamais analysées : "
        "chaque usage ci-dessous s'appuie sur un constat mesuré.")
impacts = [
    ("Clubs et entraîneurs", "Mesurer sa performance",
     (f"{club_ecart} prend moins de points à domicile "
     f"({par_lieu.loc[club_ecart, True]:.2f} par match) qu'à l'extérieur "
     f"({par_lieu.loc[club_ecart, False]:.2f}).")),
    ("Joueurs et recruteurs", "Rendre visibles les talents",
     (f"{len(departs)} départs suivis vers {departs['arrivee'].nunique()} clubs hors "
     f"Ligue 1, dont {part_asec:.0%} depuis la seule ASEC.")),
    ("Médias et supporters", "Débattre avec des chiffres vérifiés",
     "Scores recoupés entre trois sources, écarts signalés, probabilités expliquées."),
    ("Ligue et Fédération", "Piloter l'équilibre du championnat",
     f"{titres_asec} titres sur {len(palmares)} pour l'ASEC, {pct_nuls:.0%} de nuls."),
]
for col, (public, but, fait) in zip(st.columns(4), impacts, strict=True):
    col.markdown(f"<div class='carte-axe'><div class='nom'>{public}</div>"
                 f"<div class='num' style='font-weight:700'>{but}</div>"
                 f"<div class='txt' style='margin-top:.4rem'>{fait}</div></div>",
                 unsafe_allow_html=True)
st.caption("Ce tableau de bord n'est pas un outil de paris : les probabilités servent à "
           "comprendre le championnat, pas à miser.")

# ------------------------------------------------------------ méthodologie
section("Données et méthodologie", "De la collecte web à la prédiction")
volumes = sources["collections"] if sources else {}
a, b, c = st.columns(3)
with a.container(border=True, height="stretch"):
    st.markdown("**Données**")
    st.markdown(
        f"{len(joues):,}".replace(",", " ")
        + f" matchs joués de {premiere} à {derniere} (plus le début de {en_cours}), "
        "collectés sur RSSSF, Wikipédia, Futbol24 et API-Football."
        + (f" {volumes['raw_pages']['documents']} pages archivées avec URL et date."
           if "raw_pages" in volumes else ""))
with b.container(border=True, height="stretch"):
    st.markdown("**Traitement**")
    st.markdown("MongoDB (données brutes) → ETL avec recoupement des sources → "
                "PostgreSQL (modèle relationnel, 10 requêtes SQL, vues matérialisées).")
with c.container(border=True, height="stretch"):
    st.markdown("**Validation**")
    if m:
        p = m["protocole"]
        st.markdown(f"Validation temporelle glissante : chaque saison est prédite avec les "
                    f"seules saisons précédentes ({p['n_glissante']} matchs prédits). "
                    f"Test final sur 2025-26.")
st.page_link("vues/methodologie.py", label="Voir les données et la méthodologie en détail",
             icon=":material/arrow_forward:")

# ---------------------------------------------------------- résultats clés
section("Résultats clés", "Ce que montrent les données")
kpis([(f"{saisons_completes}", "saisons complètes analysées"),
      (f"{len(joues):,}".replace(",", " "), "matchs analysés"),
      (f"{len(clubs)}", "clubs de Ligue 1"),
      (f"{len(m['resultats_test']) if m else '—'}", "modèles comparés")])
st.write("")
if m:
    glis = m["validation_glissante_moyenne"]
    meilleur = min((n for n in glis if n != "naif"), key=lambda n: glis[n]["log_loss"])
    kpis([(f"{pct_nuls:.0%}", "des matchs se terminent par un nul"),
          (f"{(joues['buts_dom'] + joues['buts_ext']).mean():.2f}".replace(".", ","),
           "buts par match en moyenne"),
          (f"{titres_asec} / {len(palmares)}", "titres pour l'ASEC Mimosas"),
          (f"{glis[meilleur]['accuracy']:.1%}".replace(".", ","),
           f"de bons pronostics ({NOMS_MODELES[meilleur]}) contre "
           f"{glis['naif']['accuracy']:.1%} pour la référence naïve".replace(".", ","))])

# ---------------------------------------------------------------- explorer
section("Explorer l'étude", "Les pages de l'application")
descriptions = {
    "vues/championnat.py": "Classements, évolution par journée, palmarès, avantage du terrain.",
    "vues/club.py": "Bilan d'un club : résultats, buts, rang, forme récente.",
    "vues/attaque_defense.py": "Attaque contre défense, domicile / extérieur, minute par minute.",
    "vues/matchs.py": "Fiche de chaque match : déroulé, contexte, face-à-face.",
    "vues/joueurs.py": "Classement et fiches des buteurs, note de contribution sur 10.",
    "vues/reseau.py": "Mouvements de joueurs, clubs centraux, communautés.",
    "vues/prediction.py": "Probabilités des prochains matchs et simulateur d'affiche.",
    "vues/modeles.py": "Comparaison des six modèles, calibration, variables importantes.",
    "vues/methodologie.py": "Sources, volumes, pipeline et protocole de validation.",
}
cols = st.columns(3)
for i, (chemin, texte) in enumerate(descriptions.items()):
    titre, icone = PAGES[chemin]
    with cols[i % 3].container(border=True, height="stretch"):
        st.page_link(chemin, label=f"**{titre}**", icon=icone)
        st.caption(texte)
pied_de_page()

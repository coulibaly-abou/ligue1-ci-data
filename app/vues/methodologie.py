"""Données & méthodologie : sources, volumes, pipeline, contrôles, protocole, limites."""
import pandas as pd
import streamlit as st
from commun import (
    FIGURES,
    NOMS_MODELES,
    charger,
    configurer,
    entete,
    lire_json,
    metriques,
    pied_de_page,
    section,
)

configurer()
entete("Données & Méthodologie",
       "D'où viennent les données, comment elles sont traitées, et comment les modèles "
       "sont évalués — pour pouvoir juger la fiabilité de chaque résultat.")

sources = lire_json("sources") or {}
m = metriques()
matchs = charger("matchs")
joues = matchs[matchs["statut"] == "joue"]

section("Sources", "Quatre sources, chacune pour ce qu'elle fait le mieux")
st.dataframe(pd.DataFrame([
    ("RSSSF", "tous les matchs (journée, date, score), classements officiels", "2016-17 → 2025-26"),
    ("Wikipédia (fr / en)", ("stades, villes, buteurs, grilles de résultats, ≈ 460 carrières "
     "de joueurs, coordonnées des villes"), "2016-17 → 2026-27"),
    ("Futbol24", "résultats datés et calendrier de la saison en cours", "2026-27"),
    ("API-Football", "matchs, équipes, effectifs, transferts, événements", "2022-23 → 2024-25"),
], columns=["Source", "Données", "Couverture"]), hide_index=True, width="stretch")
st.caption("Sources écartées après audit (CGU ou robots.txt) : Soccerway/Flashscore, "
           "Transfermarkt (championnat non suivi), Wikidata (SPARQL interdit).")

volumes = sources.get("collections", {})
if volumes:
    section("Volumes collectés", "Zone brute MongoDB")
    lignes = [{"Collection": nom, "Documents": v["documents"],
               "Détail par source": " · ".join(f"{s} {n}" for s, n in v["sources"].items())}
              for nom, v in volumes.items()]
    st.dataframe(pd.DataFrame(lignes), hide_index=True, width="stretch")
    if sources.get("derniere_collecte"):
        st.caption(f"Dernière page collectée : {sources['derniere_collecte'][:16]} (UTC). "
                   "Chaque page est archivée avec son URL, sa date et une empreinte SHA-256.")

section("Pipeline", "De la collecte au tableau de bord")
architecture = FIGURES / "00_architecture.png"
if architecture.exists():
    st.image(str(architecture), width="stretch")
st.markdown("""
| Étape | Outils | Rôle |
|---|---|---|
| Collecte | Python, requests, BeautifulSoup | robots.txt respecté, 2 s entre requêtes, collecte quotidienne planifiée |
| Zone brute | MongoDB | HTML archivé et documents tels que collectés, par source |
| Zone analytique | PostgreSQL | modèle relationnel (Merise), 10 requêtes SQL, vues matérialisées |
| Réseau | networkx | graphe des carrières et transferts : PageRank, communautés |
| Modèles | scikit-learn, PyTorch | Elo, régression logistique, forêt, boosting, réseau de neurones |
| Restitution | Streamlit, Plotly | cette application |
""")

section("Contrôles de qualité", "Ce qui est vérifié à chaque chargement")
alias = sources.get("alias_clubs")
anomalies = sources.get("anomalies_etl", {})
controles = []
if alias:
    controles.append(f"Noms de clubs harmonisés : {alias['variantes']} variantes "
                     f"d'écriture ramenées à {alias['clubs']} clubs.")
ecarts = sum(n for d, n in anomalies.items() if d.startswith("score différent"))
if anomalies:
    controles.append(f"Scores recoupés entre RSSSF, Wikipédia et API-Football : {ecarts} "
                     f"écarts sur {len(joues):_} matchs, tous journalisés."
                     .replace("_", " "))
controles.append("Classements recalculés à partir des matchs et comparés aux classements "
                 "officiels publiés.")
controles.append(f"Coordonnées des villes : {sources.get('villes_geolocalisees', '—')} "
                 "villes géolocalisées depuis leur article Wikipédia, tout point hors du "
                 "territoire ivoirien étant rejeté.")
for c in controles:
    st.markdown(f"- {c}")

if m:
    p = m["protocole"]
    section("Protocole de validation", "Évaluer comme en conditions réelles")
    st.markdown(f"""
- **Cible** : résultat du match en trois classes — victoire domicile, nul, victoire
  extérieur.
- **{p['n_variables']} variables** calculées uniquement avec l'information disponible
  *avant* le match (Elo, forme, buts glissants, classement, repos).
- **Aucun mélange aléatoire** : la saison {p['chauffe']}-{p['chauffe'] + 1} initialise
  l'Elo ; chaque saison de {p['saisons_glissantes'][0]}-{p['saisons_glissantes'][0] + 1}
  à {p['saisons_glissantes'][-1]}-{p['saisons_glissantes'][-1] + 1} est prédite par un
  modèle entraîné sur les seules saisons précédentes ({p['n_glissante']} matchs prédits).
- **Choix du modèle** : le plus simple parmi ceux dont la log-loss moyenne
  2021 → 2024 est à moins de {m['regle_selection']['tolerance']} de la meilleure —
  modèle retenu : **{NOMS_MODELES[m['modele_retenu']]}**.
- **Test final** : saison {p['test']}-{p['test'] + 1} ({p['n_test']} matchs), jamais
  utilisée pour un choix.
""")

section("Limites", "Ce que les données ne permettent pas")
st.markdown("""
- Environ 240 matchs par saison : les écarts entre modèles sont du même ordre que
  l'incertitude d'une saison.
- Aucune source légale ne publie les buteurs et cartons match par match avant 2022.
- Le réseau ne suit que les joueurs ayant un article Wikipédia ou un transfert déclaré à
  API-Football : il est biaisé vers les grands clubs.
- 2019-20 (arrêt Covid) et 2020-21 (poules + play-off) : classements recalculés
  approximatifs.
""")
pied_de_page()

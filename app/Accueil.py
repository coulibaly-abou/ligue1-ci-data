"""Tableau de bord de la Ligue 1 Côte d'Ivoire — point d'entrée et navigation.

    streamlit run app/Accueil.py
"""
from pathlib import Path

import streamlit as st
from commun import AUTEUR, CSS, FORMATION, ORANGE, PAGES, RECHERCHE, SECTIONS, charger, liens_html

st.set_page_config(page_title="Ligue 1 Côte d'Ivoire — Data Science · Aboubakar Coulibaly",
                   page_icon=str(Path(__file__).parent / "icone.png"), layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"<div class='marque'><div class='n'>{AUTEUR}</div>"
                f"<div class='r'>{FORMATION}</div>"
                f"<div class='p'>{RECHERCHE}.</div>"
                f"<div class='p'>{liens_html()}</div>"
                f"<div class='p'>Ligue 1 Côte d'Ivoire · Data Science & "
                f"<span style='color:{ORANGE}'>Machine Learning</span></div></div>",
                unsafe_allow_html=True)

# Chemins relatifs au dossier de ce fichier (règle de st.Page) ; pages groupées par section
ACCUEIL = next(iter(PAGES))


def page(chemin: str) -> st.Page:
    titre, icone = PAGES[chemin]
    return st.Page(chemin, title=titre, icon=icone, default=chemin == ACCUEIL,
                   url_path=None if chemin == ACCUEIL else Path(chemin).stem)


navigation = st.navigation({section: [page(c) for c in chemins]
                            for section, chemins in SECTIONS.items()}, position="top")

# Recherche globale : un club ou un joueur, sur toutes les pages
with st.sidebar:
    requete = st.text_input("Rechercher", placeholder="Joueur ou club", key="recherche",
                            icon=":material/search:").strip().lower()
    if len(requete) >= 2:
        clubs = [c for c in charger("clubs")["club"] if requete in c.lower()]
        joueurs = charger("joueurs")
        trouves = joueurs[joueurs["nom"].str.lower().str.contains(requete, regex=False)
                          | joueurs["nom_complet"].fillna("").str.lower()
                          .str.contains(requete, regex=False)]
        trouves = trouves.sort_values("saison").groupby("joueur").tail(1) \
            .sort_values("note", ascending=False)
        for c in clubs[:5]:
            st.page_link("vues/club.py", label=c, icon=":material/shield:",
                         query_params={"club": c})
        for j in trouves.head(8).itertuples():
            st.page_link("vues/joueurs.py", label=f"{j.nom} · {j.club} ({j.saison[:4]})",
                         icon=":material/person:",
                         query_params={"saison": j.saison, "joueur": j.joueur})
        if not clubs and trouves.empty:
            st.caption("Aucun club ni joueur ne correspond.")
        elif len(trouves) > 8:
            st.caption(f"{len(trouves) - 8} autre(s) joueur(s) : préciser la recherche.")

navigation.run()

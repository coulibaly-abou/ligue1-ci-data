"""Tableau de bord de la Ligue 1 Côte d'Ivoire — point d'entrée et navigation.

    streamlit run app/Accueil.py
"""
from pathlib import Path

import streamlit as st
from commun import AUTEUR, CSS, FORMATION, ORANGE, PAGES, RECHERCHE, SECTIONS, liens_html

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
navigation.run()

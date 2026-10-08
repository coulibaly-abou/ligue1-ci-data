"""Tableau de bord de la Ligue 1 ivoirienne — point d'entrée et navigation.

    streamlit run app/Accueil.py
"""
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Ligue 1 ivoirienne — tableau de bord",
                   page_icon=str(Path(__file__).parent / "icone.png"), layout="wide")

# Chemins relatifs au dossier de ce fichier (règle de st.Page)
navigation = st.navigation([
    st.Page("vues/accueil.py", title="Accueil", default=True),
    st.Page("vues/championnat.py", title="Championnat", url_path="championnat"),
    st.Page("vues/club.py", title="Fiche club", url_path="club"),
    st.Page("vues/reseau.py", title="Réseau des clubs", url_path="reseau"),
    st.Page("vues/prediction.py", title="Prédiction", url_path="prediction"),
    st.Page("vues/modeles.py", title="Modèles", url_path="modeles"),
])
navigation.run()

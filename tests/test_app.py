"""Tableau de bord : chaque page s'exécute, et les filtres modifient vraiment l'affichage.

Utilise les données réelles de app/data/ ; sauté si Streamlit n'est pas installé (CI).
"""
import re
import sys
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

APP = Path(__file__).parent.parent / "app"
sys.path.insert(0, str(APP))
PAGES = ["accueil", "championnat", "club", "attaque_defense", "matchs", "joueurs",
         "reseau", "prediction", "modeles", "methodologie"]


def ouvrir(page: str, **params) -> AppTest:
    at = AppTest.from_file(str(APP / "Accueil.py"), default_timeout=120)
    at.run()
    at.switch_page(f"vues/{page}.py")
    for cle, valeur in params.items():
        at.query_params[cle] = valeur
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def carte(at: AppTest, libelle: str) -> tuple[str, str]:
    for m in at.markdown:
        x = re.search(rf"<div class='lib'>{libelle}</div><div class='val'>([^<]*)</div>"
                      r"<div class='det'>([^<]*)", m.value)
        if x:
            return x.groups()
    raise AssertionError(f"carte {libelle} absente")


@pytest.mark.parametrize("page", PAGES)
def test_page_sans_erreur(page):
    ouvrir(page)


def test_filtres_du_tableau_de_bord_club():
    at = ouvrir("club", club="ASEC Mimosas")
    tous = carte(at, "Matchs")
    at.button_group(key="c_lieu").set_value("Domicile").run()
    domicile = carte(at, "Matchs")
    assert int(domicile[0]) < int(tous[0])
    at.selectbox(key="c_saison").set_value("Toutes les saisons").run()
    assert carte(at, "Classement")[0] == "—"  # pas de classement toutes saisons confondues
    next(b for b in at.button if b.label == "Réinitialiser").click().run()
    assert carte(at, "Matchs") == tous and at.session_state["c_lieu"] == "Tous"


def test_match_precedent_suivant_et_statistiques_non_publiees():
    at = ouvrir("matchs", match="1000")
    next(b for b in at.button if b.label == "Match suivant").click().run()
    assert at.selectbox(key="m_match").value != 1000
    next(b for b in at.button if b.label == "Match précédent").click().run()
    assert at.selectbox(key="m_match").value == 1000
    stats = at.dataframe[0].value.set_index("Statistique")
    assert (stats.loc["Possession"].iloc[:2] == "Non publié").all()


def test_filtres_joueurs():
    at = ouvrir("joueurs", saison="2023-2024")

    def nombre():
        texte = "".join(m.value for m in at.markdown)
        return int(re.search(r"<b>(\d+)</b> joueur", texte).group(1))

    tous = nombre()
    at.toggle[0].set_value(True).run()
    fiables = nombre()
    assert 0 < fiables < tous


def test_recherche_globale():
    at = ouvrir("accueil")
    at.sidebar.text_input(key="recherche").input("asec").run()
    assert any("ASEC" in str(p.label) for p in at.sidebar.get("page_link"))

from pathlib import Path

import pytest

from src.collecte.parsers.rsssf import construire_date, parse_page
from src.collecte.parsers.wikipedia import parse_buteurs, parse_clubs

FIXTURES = Path(__file__).parent / "fixtures"


def lire(nom: str) -> str:
    return (FIXTURES / nom).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def saison_2023_2024():
    return parse_page(lire("rsssf_2023-2024.html"), "2023-2024", "url")


@pytest.fixture(scope="module")
def saison_2020_2021():
    return parse_page(lire("rsssf_2020-2021.html"), "2020-2021", "url")


# --- RSSSF -----------------------------------------------------------------

def test_page_vide_ne_renvoie_rien():
    assert parse_page("<html></html>", "2024-2025", "url") == ([], [])


@pytest.mark.parametrize(
    "mois, jour, attendu",
    [("Sep", "20", "2024-09-20"), ("Aug", "3", "2024-08-03"), ("May", "18", "2025-05-18"),
     ("Feb", "30", None), ("Foo", "1", None)],
)
def test_construire_date(mois, jour, attendu):
    assert construire_date("2024-2025", mois, jour) == attendu


def test_saison_complete(saison_2023_2024):
    matchs, classements = saison_2023_2024
    equipes = {m["equipe_dom"] for m in matchs} | {m["equipe_ext"] for m in matchs}
    assert len(equipes) == 16
    assert len(matchs) == 241  # 240 + un match arrêté puis rejoué
    assert all(m["date"] and m["journee"] for m in matchs)
    final = [c for c in classements if c["type_tableau"] == "final table"]
    assert len(final) == 16  # le tableau répété en bas de page n'est pas dupliqué
    assert final[0]["equipe"] == "San-Pédro FC (San Pédro)"


def test_premier_match(saison_2023_2024):
    premier = saison_2023_2024[0][0]
    assert premier["journee"] == 1
    assert premier["statut"] == "joue"
    assert isinstance(premier["buts_dom"], int)
    assert premier["url_source"] == "url"


def test_tapis_vert_et_note_sur_deux_lignes(saison_2023_2024):
    match = next(m for m in saison_2023_2024[0] if m["statut"] == "tapis_vert")
    assert (match["equipe_dom"], match["equipe_ext"]) == ("Racing Club", "Bouaké")
    assert (match["buts_dom"], match["buts_ext"]) == (0, 3)
    assert match["note"].endswith("Racing walked off;")


def test_nom_equipe_sans_texte_de_note(saison_2023_2024):
    equipes = {m["equipe_ext"] for m in saison_2023_2024[0]}
    assert "ASI Abengourou" in equipes
    assert not any("walked" in e for e in equipes)


def test_match_abandonne_sans_score(saison_2023_2024):
    match = next(m for m in saison_2023_2024[0] if m["statut"] == "abandonne")
    assert match["buts_dom"] is None and match["buts_ext"] is None


def test_poules_et_playoff(saison_2020_2021):
    matchs, classements = saison_2020_2021
    assert {m["phase"] for m in matchs} == {"Group Stage", "Championship Playoff (Super Division)"}
    assert not any(m["statut"] == "exempt" for m in matchs)  # lignes "bye" ignorées
    groupes = {c["groupe"] for c in classements if c["phase"] == "Group Stage"}
    assert groupes == {"A", "B"}
    playoff = [m for m in matchs if m["phase"].startswith("Championship")]
    assert playoff[0]["date"] == "2021-06-06"  # date sur la même ligne que "Round 1"


# --- Wikipédia -------------------------------------------------------------

PAGE_WIKI = """
<table><tr><th>Club</th><th>Ville</th><th>Stade</th><th>Capacité</th></tr>
<tr><td>ASEC Mimosas</td><td>Abidjan</td><td>Stade Félix-Houphouët-Boigny[2]</td>
<td>45 000</td></tr></table>
<table><tr><th>#</th><th>Buteur</th><th>Club</th><th>Buts</th></tr>
<tr><td>1</td><td>Aristide Bancé</td><td>ASEC Mimosas</td><td>13</td></tr></table>
"""


def test_wikipedia_clubs():
    clubs = parse_clubs(PAGE_WIKI, "2016-2017", "url")
    assert clubs == [{
        "saison": "2016-2017", "club": "ASEC Mimosas", "ville": "Abidjan",
        "stade": "Stade Félix-Houphouët-Boigny", "capacite": 45000,
        "url_source": "url", "source": "wikipedia",
    }]


def test_wikipedia_buteurs():
    buteurs = parse_buteurs(PAGE_WIKI, "2016-2017", "url")
    assert buteurs[0]["joueur"] == "Aristide Bancé"
    assert buteurs[0]["buts"] == 13


def test_wikipedia_sans_tableau():
    assert parse_clubs("<p>rien</p>", "2016-2017", "url") == []
    assert parse_buteurs("<p>rien</p>", "2016-2017", "url") == []

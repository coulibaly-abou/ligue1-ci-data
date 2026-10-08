import pytest

from src.etl.nettoyage import (
    anomalies_match,
    capacite_plausible,
    normaliser,
    resoudre_club,
    resoudre_stade,
    resultat,
    table_alias,
)


@pytest.mark.parametrize(
    "brut, attendu",
    [("Stade (Abidjan)", "stade"), ("ES d’Agboville", "es d agboville"),
     ("  Séwé  Sport ", "sewe sport"), ("", ""), (None, "")],
)
def test_normaliser(brut, attendu):
    assert normaliser(brut) == attendu


@pytest.mark.parametrize(
    "brut, officiel",
    [
        ("Stade", "Stade d'Abidjan"),                 # abréviation RSSSF
        ("Stade (Abidjan)", "Stade d'Abidjan"),       # ville entre parenthèses
        ("SOAT", "SO Armée"),                         # lettre de note collée
        ("ASEC MimosasTC", "ASEC Mimosas"),           # deux lettres collées
        ("ASEC Mimosas T C", "ASEC Mimosas"),
        ("Bouaké FCP", "Bouaké FC"),                  # « FC » + note « P »
        ("SC Adjamé", "Stella Club d'Adjamé"),        # nouveau nom du club
        ("SOFC Abobo", "SOL FC"),
        ("OSA", "FC Olympic Sport d'Abobo"),          # à ne pas confondre avec SOL FC
        ("SC Gagnoa", "SC Gagnoa"),
        ("ES d’Agboville", "ES Agboville"),           # apostrophe typographique
        ("Racing d'Abidjan", "Racing Club d'Abidjan"),
    ],
)
def test_resoudre_club(brut, officiel):
    assert resoudre_club(brut) == officiel


def test_club_inconnu():
    assert resoudre_club("Mainz 05") is None
    assert resoudre_club("") is None
    assert resoudre_club(None) is None


def test_alias_sans_conflit():
    table = table_alias()
    assert len(set(table.values())) == 31
    assert table["asec mimosas"] == "ASEC Mimosas"


@pytest.mark.parametrize("dom, ext, attendu", [(2, 1, "D"), (1, 1, "N"), (0, 3, "E"),
                                                (None, 1, None)])
def test_resultat(dom, ext, attendu):
    assert resultat(dom, ext) == attendu


MATCH_OK = {"club_dom": 1, "club_ext": 2, "buts_dom": 2, "buts_ext": 0,
            "statut": "joue", "date": "2024-10-12", "saison": "2024-2025"}


def test_match_coherent():
    assert anomalies_match(MATCH_OK) == []


@pytest.mark.parametrize(
    "modif, attendu",
    [
        ({"club_ext": None}, "club non reconnu"),
        ({"club_ext": 1}, "un club joue contre lui-même"),
        ({"buts_dom": 45}, "buts_dom invraisemblable : 45"),
        ({"buts_ext": None}, "match joué sans score"),
        ({"date": "2023-10-12"}, "date 2023-10-12 hors de la saison 2024-2025"),
    ],
)
def test_match_incoherent(modif, attendu):
    assert attendu in anomalies_match({**MATCH_OK, **modif})


def test_match_a_jouer_sans_score_accepte():
    a_jouer = {**MATCH_OK, "statut": "a_jouer", "buts_dom": None, "buts_ext": None}
    assert anomalies_match(a_jouer) == []


@pytest.mark.parametrize(
    "brut, retenu",
    [("Robert Champroux Stadium", "Stade Robert-Champroux"),
     ("Complex Sportif Yopougon", "Complexe sportif de Yopougon"),
     ("Stade Laurent Pokou", "Stade Laurent Pokou"),   # sans alias : nom d'origine
     ("", None), (None, None)],
)
def test_resoudre_stade(brut, retenu):
    assert resoudre_stade(brut) == retenu


@pytest.mark.parametrize("capacite, attendu", [(20000, 20000), (100000, None), (0, None),
                                                (None, None)])
def test_capacite_plausible(capacite, attendu):
    assert capacite_plausible(capacite) == attendu

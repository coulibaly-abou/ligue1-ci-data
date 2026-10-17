import pandas as pd

from src.restitution.joueurs import (
    cle_joueur,
    derouler_buts,
    notes_joueurs,
    rapprocher_profils,
)

MATCHS = pd.DataFrame({"id_match": [1, 2], "dom": ["A", "A"], "ext": ["B", "C"],
                       "buts_dom": [2, 1], "buts_ext": [1, 0]})


def _buts():
    # Match 1 : B ouvre (10'), A égalise (30'), A prend l'avantage (80') -> 2-1 complet
    # Match 2 : score final 1-0 mais déroulé vide d'un but -> incomplet
    return pd.DataFrame({
        "id_match": [1, 1, 1, 2, 2], "minute": [80, 10, 30, 5, 60],
        "club": ["A", "B", "A", "A", "C"], "saison": ["s"] * 5,
        "type_but": ["normal", "normal", "penalty", "normal", "normal"],
        "buteur": ["X", "Y", "X", "Z", "W"], "api_joueur_id": [1, 2, 1, None, 4]})


def test_derouler_buts_score_et_decisif():
    b = derouler_buts(_buts(), MATCHS).set_index(["id_match", "minute"])
    assert list(b.loc[1, ["score_dom", "score_ext"]].itertuples(index=False)) == \
        [(0, 1), (1, 1), (2, 1)]
    assert b.loc[1, "decisif"].tolist() == [True, True, True]  # ouvre, égalise, avantage
    assert not b.loc[2, "complet"].any()
    assert not b.loc[2, "decisif"].any()


def test_but_qui_creuse_l_ecart_n_est_pas_decisif():
    matchs = pd.DataFrame({"id_match": [1], "dom": ["A"], "ext": ["B"],
                           "buts_dom": [2], "buts_ext": [0]})
    buts = pd.DataFrame({"id_match": [1, 1], "minute": [10, 20], "club": ["A", "A"]})
    assert derouler_buts(buts, matchs)["decisif"].tolist() == [True, False]


def test_notes_joueurs():
    b = derouler_buts(_buts(), MATCHS)
    cartons = pd.DataFrame({"saison": ["s"], "joueur": ["Y"], "api_joueur_id": [2],
                            "club": ["B"], "couleur": ["rouge"]})
    club = pd.DataFrame({"saison": ["s"] * 3, "club": ["A", "B", "C"], "bp": [10, 4, 2]})
    n = notes_joueurs(b, cartons, club).set_index("joueur")
    assert n.loc["api1", "buts"] == 2 and n.loc["api1", "penalties"] == 1
    assert n.loc["api1", "rang_saison"] == 1
    assert n.loc["api2", "rouges"] == 1
    assert n["note"].between(0, 10).all()
    assert "Z|A" in n.index  # sans id API : nom abrégé + club


def test_cle_joueur():
    assert cle_joueur(12.0, "A. B", "ASEC") == "api12"
    assert cle_joueur(None, "A. B", "ASEC") == "A. B|ASEC"


def test_rapprocher_profils():
    effectifs = pd.DataFrame({"saison": ["s"] * 3, "club": ["A"] * 3, "api_joueur_id": [1, 2, 3],
                              "prenom": ["Kouassi", "Jean", "Aboubacar"],
                              "nom_famille": ["Abissa", "Koné", "Koné"]})
    notes = pd.DataFrame({"saison": ["s"] * 4, "club": ["A", "A", "A", "B"],
                          "nom": ["K. Abissa", "J. Kone", "Kone", "K. Abissa"]})
    # « Kone » sans initiale désigne deux joueurs : non rapproché ; club B : effectif inconnu
    assert rapprocher_profils(notes, effectifs).tolist() == [1, 2, pd.NA, pd.NA]

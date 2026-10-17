"""Calculs du tableau de bord (app/indicateurs.py) : filtres, bilans, classement, navigation."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "app"))
import indicateurs as ind


@pytest.fixture
def resultats():
    # Club A : V 2-0 (dom), N 1-1 (ext), D 0-1 (dom), V 3-1 (ext) ; club B en face
    lignes = []
    for i, (dom, bp, bc) in enumerate([(True, 2, 0), (False, 1, 1), (True, 0, 1),
                                       (False, 3, 1)], start=1):
        issue = "V" if bp > bc else "N" if bp == bc else "D"
        pts = {"V": 3, "N": 1, "D": 0}[issue]
        inverse = {"V": "D", "N": "N", "D": "V"}[issue]
        lignes.append({"id_match": i, "saison": "s", "date_match": f"2024-01-0{i}",
                       "a_domicile": dom, "club": "A", "adversaire": "B", "bp": bp, "bc": bc,
                       "points": pts, "issue": issue, "journee_club": i})
        lignes.append({"id_match": i, "saison": "s", "date_match": f"2024-01-0{i}",
                       "a_domicile": not dom, "club": "B", "adversaire": "A", "bp": bc,
                       "bc": bp, "points": {"V": 3, "N": 1, "D": 0}[inverse],
                       "issue": inverse, "journee_club": i})
    return pd.DataFrame(lignes)


def test_bilan(resultats):
    b = ind.bilan(resultats[resultats["club"] == "A"])
    assert (b.matchs, b.victoires, b.nuls, b.defaites) == (4, 2, 1, 1)
    assert (b.buts_pour, b.buts_contre, b.difference, b.points) == (6, 3, 3, 7)
    assert (b.sans_encaisser, b.sans_marquer) == (1, 1)
    assert b.par_match(b.points) == 1.75


def test_bilan_vide_ne_donne_pas_zero(resultats):
    b = ind.bilan(resultats.iloc[0:0])
    assert b.matchs == 0 and b.par_match(b.points) is None and b.taux(0) is None


def test_filtres(resultats):
    a = resultats[resultats["club"] == "A"]
    assert len(ind.filtrer_resultats(a, lieu="Domicile")) == 2
    assert ind.bilan(ind.filtrer_resultats(a, lieu="Extérieur")).points == 4
    assert list(ind.filtrer_resultats(a, journees=(2, 3))["id_match"]) == [2, 3]
    assert ind.filtrer_resultats(a, saison="autre").empty


def test_classement(resultats):
    t = ind.classement(resultats, "s")
    assert list(t.index) == ["A", "B"]
    assert t.loc["A", "Pts"] == 7 and t.loc["B", "Pts"] == 4
    assert t.loc["B", "Diff"] == -3
    # À domicile seulement : A 3 pts (V 2-0, D 0-1), B 1 pt (N 1-1, D 1-3)
    dom = ind.classement(resultats, "s", lieu="Domicile")
    assert dom.loc["A", "Pts"] == 3 and dom.loc["B", "Pts"] == 1 and dom.loc["B", "J"] == 2


def test_tendance(resultats):
    a = resultats[resultats["club"] == "A"]
    assert ind.tendance(a, n=5) is None  # moins de 2 x 5 matchs
    t = ind.tendance(a, n=2)
    assert t["recent"] == 1.5 and t["avant"] == 2.0 and t["ecart"] == -0.5


def test_bilan_adversaires(resultats):
    t = ind.bilan_adversaires(resultats[resultats["club"] == "A"])
    assert t.loc["B", "matchs"] == 4 and t.loc["B", "ppm"] == 1.75


def test_voisins_et_prochains():
    matchs = pd.DataFrame({
        "id_match": [1, 2, 3, 4, 5], "saison": ["s"] * 5,
        "date_match": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", None],
        "dom": ["A", "C", "B", "A", "A"], "ext": ["B", "D", "A", "C", "D"],
        "statut": ["joue", "joue", "joue", "a_jouer", "a_jouer"]})
    assert ind.voisins(matchs, 2) == (1, 3)
    assert ind.voisins(matchs, 1, club="A") == (None, 3)
    assert ind.voisins(matchs, 3, club="A") == (1, None)
    assert list(ind.prochains_matchs(matchs, "A")["id_match"]) == [4, 5]


def test_phase():
    assert ind.phase("Regular Stage") == ind.phase("Saison reguliere") == "Saison régulière"


def test_poids_identiques_au_calcul_de_la_note():
    from src.restitution import joueurs

    assert ind.POIDS == joueurs.POIDS and ind.MALUS_ROUGE == joueurs.MALUS_ROUGE
    assert abs(sum(ind.POIDS.values()) - 1) < 1e-9

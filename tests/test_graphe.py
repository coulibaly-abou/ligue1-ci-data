"""Tests de la préparation du graphe Neo4j (fonctions pures, sans serveur Neo4j)."""
import math

import pandas as pd
import pytest

from src.graphe.chargement_neo4j import (
    en_lots,
    noeuds_clubs,
    noeuds_personnes,
    relations_mouvements,
    relations_passages,
    valeur_propre,
)


def test_valeur_propre_remplace_les_manquants_par_none():
    assert valeur_propre(float("nan")) is None
    assert valeur_propre(pd.NaT) is None
    assert valeur_propre(None) is None


def test_valeur_propre_convertit_les_types_numpy_et_dates():
    entier = pd.Series([3], dtype="Int64").iloc[0]
    assert valeur_propre(entier) == 3 and type(valeur_propre(entier)) is int
    assert valeur_propre(pd.Series([True]).iloc[0]) is True
    assert valeur_propre(pd.Timestamp("2024-07-01")) == "2024-07-01"


def test_noeuds_clubs_sans_manquants():
    clubs = pd.DataFrame({"nom": ["ASEC Mimosas", "Raja"], "est_ligue1": [True, False],
                          "ville": ["Abidjan", None]})
    assert noeuds_clubs(clubs) == [
        {"nom": "ASEC Mimosas", "est_ligue1": True, "ville": "Abidjan"},
        {"nom": "Raja", "est_ligue1": False, "ville": None},
    ]


def test_noeuds_personnes_garde_l_identifiant_entier():
    personnes = pd.DataFrame({"id_personne": [7], "nom": ["Kessié"], "nationalite": [math.nan],
                              "poste": ["Milieu"], "est_joueur": [True],
                              "est_entraineur": [False]})
    (noeud,) = noeuds_personnes(personnes)
    assert noeud["id_personne"] == 7 and noeud["nationalite"] is None


def _passages():
    return pd.DataFrame({
        "id_personne": [1, 1, 2, 3],
        "club": ["ASEC Mimosas", "Africa Sports", "Stella Club", None],
        "role": ["jeunes", "senior", "entraineur", "selection"],
        "annee_debut": [2010, 2014, 2020, 2015],
        "annee_fin": [2013, math.nan, 2022, 2016],
        "pret": [False, True, False, False],
        "matchs": [math.nan, 40, math.nan, 3],
        "buts": [math.nan, 5, math.nan, 0],
    })


def test_relations_passages_regroupe_par_type_de_relation():
    rel = relations_passages(_passages())
    assert set(rel) == {"FORME_A", "A_JOUE_POUR", "A_ENTRAINE"}
    (joue,) = rel["A_JOUE_POUR"]
    assert joue == {"id_personne": 1, "club": "Africa Sports", "annee_debut": 2014,
                    "annee_fin": None, "pret": True, "matchs": 40, "buts": 5}


def test_relations_passages_ignore_selections_et_clubs_inconnus():
    rel = relations_passages(_passages())
    clubs = [r["club"] for lignes in rel.values() for r in lignes]
    assert None not in clubs and len(clubs) == 3


def test_relations_passages_ne_modifie_pas_l_entree():
    passages = _passages()
    copie = passages.copy()
    relations_passages(passages)
    pd.testing.assert_frame_equal(passages, copie)


def test_relations_mouvements():
    mvts = pd.DataFrame({"depart": ["ASEC Mimosas"], "arrivee": ["Raja"], "annee": [2019.0],
                         "pret": [False], "source": ["carrieres_wikipedia"],
                         "depart_ligue1": [True], "arrivee_ligue1": [False]})
    assert relations_mouvements(mvts) == [{"depart": "ASEC Mimosas", "arrivee": "Raja",
                                           "annee": 2019, "pret": False,
                                           "source": "carrieres_wikipedia"}]


def test_en_lots_decoupe_sans_perte():
    assert list(en_lots(list(range(7)), 3)) == [[0, 1, 2], [3, 4, 5], [6]]


def test_en_lots_refuse_une_taille_nulle():
    with pytest.raises(ValueError):
        list(en_lots([1], 0))


def test_les_cinq_requetes_ont_leurs_parametres_par_defaut():
    from src.graphe.requetes import PARAMETRES_DEFAUT, fichiers_requetes, parametres_requis

    fichiers = fichiers_requetes()
    assert len(fichiers) == 5
    for fichier in fichiers:
        assert parametres_requis(fichier.read_text(encoding="utf-8")) <= set(PARAMETRES_DEFAUT)


def test_parametres_requis_ignore_les_commentaires():
    from src.graphe.requetes import parametres_requis

    texte = "// Paramètre : $ignore\nMATCH (c:Club {nom: $club}) WHERE c.x > $seuil RETURN c"
    assert parametres_requis(texte) == {"club", "seuil"}


def test_contraintes_decoupees_en_instructions():
    from src.graphe.chargement_neo4j import FICHIER_CONTRAINTES, instructions_cypher

    instructions = instructions_cypher(FICHIER_CONTRAINTES)
    assert len(instructions) == 2 and all(i.startswith("CREATE CONSTRAINT")
                                          for i in instructions)


def test_cypher_passages_formate_sans_accolade_residuelle():
    from src.graphe.chargement_neo4j import CYPHER_PASSAGES, RELATION_PAR_ROLE

    for relation in RELATION_PAR_ROLE.values():
        cypher = CYPHER_PASSAGES.format(relation=relation)
        assert f"[:{relation} {{annee_debut" in cypher
        assert "{relation}" not in cypher and "{{" not in cypher


def test_relations_passages_ne_produit_que_des_types_connus():
    from src.graphe.chargement_neo4j import RELATION_PAR_ROLE

    passages = _passages().assign(role=["jeunes", "senior", "inconnu", "selection"])
    assert set(relations_passages(passages)) <= set(RELATION_PAR_ROLE.values())


def test_verifier_sources_refuse_une_table_vide():
    from src.graphe.chargement_neo4j import verifier_sources

    verifier_sources(clubs=pd.DataFrame({"nom": ["A"]}))
    with pytest.raises(ValueError, match="personnes"):
        verifier_sources(clubs=pd.DataFrame({"nom": ["A"]}), personnes=pd.DataFrame())


def test_ouvrir_driver_sans_identifiants(monkeypatch):
    from src.graphe import chargement_neo4j

    monkeypatch.setattr(chargement_neo4j, "NEO4J_PASSWORD", None)
    with pytest.raises(chargement_neo4j.ConnexionImpossible, match="NEO4J_PASSWORD"):
        chargement_neo4j.ouvrir_driver()

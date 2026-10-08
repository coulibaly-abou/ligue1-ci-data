from pathlib import Path

from src.collecte.parsers.wikipedia import parse_classements, parse_grille
from src.collecte.parsers.wikipedia_personnes import (
    _annees,
    _stats,
    parse_membres,
    parse_personne,
    parse_sous_categories,
)

FIXTURES = Path(__file__).parent / "fixtures"
URL_FR = "https://fr.wikipedia.org/wiki/x"


def lire(nom: str) -> str:
    return (FIXTURES / nom).read_text(encoding="utf-8")


# --- Saison : classement et grille ----------------------------------------

GRILLE = """<table>
<tr><td>Résultats (▼dom., ►ext.)</td><td>ASEC</td><td>SOA</td><td>ZFC</td></tr>
<tr><td>ASEC Mimosas</td><td></td><td>2-1</td><td>-</td></tr>
<tr><td>SOA</td><td>0–0</td><td></td><td>-</td></tr>
<tr><td>Zoman FC</td><td>-</td><td>1-3</td><td></td></tr>
<tr><td>Victoire à domicile</td><td>Victoire à domicile</td><td></td><td></td></tr>
</table>"""


def test_grille_matchs_joues_et_a_jouer():
    joues, a_jouer = parse_grille(GRILLE, "2026-2027", URL_FR)
    scores = {(m["equipe_dom"], m["equipe_ext"]): (m["buts_dom"], m["buts_ext"]) for m in joues}
    assert scores == {("ASEC Mimosas", "SOA"): (2, 1), ("SOA", "ASEC Mimosas"): (0, 0),
                      ("Zoman FC", "SOA"): (1, 3)}
    assert {(m["equipe_dom"], m["equipe_ext"]) for m in a_jouer} == {
        ("ASEC Mimosas", "Zoman FC"), ("SOA", "Zoman FC"), ("Zoman FC", "ASEC Mimosas")}
    assert all(m["source"] == "wikipedia" for m in joues + a_jouer)


def test_page_sans_grille():
    assert parse_grille("<table><tr><td>a</td></tr></table>", "2026-2027", URL_FR) == ([], [])


def test_classement():
    html = """<table><tr><th>Rang</th><th>Équipe</th><th>Pts</th><th>J</th><th>G</th>
    <th>N</th><th>P</th><th>Bp</th><th>Bc</th><th>Diff</th></tr>
    <tr><td>1</td><td>SOA</td><td>4</td><td>2</td><td>1</td><td>1</td><td>0</td>
    <td>3</td><td>2</td><td>+1</td></tr></table>"""
    (ligne,) = parse_classements(html, "2026-2027", URL_FR)
    assert (ligne["rang"], ligne["equipe"], ligne["pts"], ligne["bp"]) == (1, "SOA", 4, 3)


# --- Joueurs : catégories et infobox --------------------------------------

def test_sous_categories_ignore_les_outils():
    html = """<div id="mw-subcategories"><ul>
    <li><a href="/wiki/Category:ASEC_Mimosas_players" title="Category:ASEC Mimosas players">
    ASEC Mimosas players</a></li>
    <li><a href="https://petscan.wmflabs.org/" title="PetScan">PetScan</a></li></ul></div>"""
    cats = parse_sous_categories(html, "https://en.wikipedia.org/wiki/Category:X")
    assert cats == [{"categorie": "ASEC Mimosas players",
                     "url": "https://en.wikipedia.org/wiki/Category:ASEC_Mimosas_players"}]


def test_membres_et_page_suivante():
    html = """<div id="mw-pages"><a href="/w/index.php?title=Category:X&pagefrom=K">next page</a>
    <ul><li><a href="/wiki/Aristide_Banc%C3%A9">Aristide Bancé</a></li>
    <li><a href="https://petscan.wmflabs.org/?categories=X">PetScan</a></li>
    <li><a href="/wiki/Sp%C3%A9cial:Suivi_des_liens/Cat%C3%A9gorie:X">Suivi</a></li></ul></div>"""
    membres, suivante = parse_membres(html, "https://en.wikipedia.org/wiki/Category:X")
    assert [m["url"] for m in membres] == ["https://en.wikipedia.org/wiki/Aristide_Banc%C3%A9"]
    assert suivante.endswith("pagefrom=K")


def test_annees():
    assert _annees("2007–2008") == (2007, 2008)
    assert _annees("2002 - 2003") == (2002, 2003)
    assert _annees("2016") == (2016, 2016)
    assert _annees("2019–") == (2019, None)
    assert _annees("0000 –2000") == (None, 2000)


def test_stats_avec_cles_de_tri_cachees():
    assert _stats(["33", "(8)"]) == (33, 8)
    assert _stats(["0 26 0 (13)"]) == (26, 13)
    assert _stats([]) == (None, None)


def test_infobox_anglaise():
    fiche = parse_personne(lire("wiki_en_joueur.html"), "url", "en")
    assert fiche["nom"] == "Aristide Bancé"
    assert fiche["naissance"] == "1984-09-19"
    assert fiche["url_autre_langue"].startswith("https://fr.wikipedia.org/")
    asec = next(p for p in fiche["passages"] if p["club"] == "ASEC Mimosas")
    assert (asec["type"], asec["debut"], asec["fin"], asec["matchs"], asec["buts"]) == (
        "senior", 2016, 2017, 22, 13)
    pret = next(p for p in fiche["passages"] if p["club"] == "Germinal Beerschot")
    assert pret["pret"] is True
    assert any(p["type"] == "selection" for p in fiche["passages"])


def test_infobox_francaise():
    fiche = parse_personne(lire("wiki_fr_joueur.html"), "url", "fr")
    assert fiche["poste"] == "Avant-centre"
    asec = next(p for p in fiche["passages"] if p["club"] == "ASEC Mimosas")
    assert (asec["matchs"], asec["buts"]) == (26, 13)
    entraineur = [p for p in fiche["passages"] if p["type"] == "entraineur"]
    assert entraineur[0]["club"] == "Williamsville AC"


def test_page_sans_infobox():
    assert parse_personne("<html><h1 id='firstHeading'>X</h1></html>", "url", "en") is None


# --- Futbol24 : calendrier et résultats datés ------------------------------

def test_futbol24_calendrier():
    from src.collecte.parsers.futbol24 import parse_matchs

    joues, a_jouer = parse_matchs(lire("futbol24_calendrier.html"), "2026-2027", "url")
    assert joues == [] and len(a_jouer) == 50
    premier = a_jouer[0]
    assert (premier["equipe_dom"], premier["date"]) == ("FC Mouna", "2026-10-06")
    assert premier["horaire_provisoire"] is False
    assert any(m["horaire_provisoire"] for m in a_jouer)  # date fictive « xx:59 »


def test_futbol24_resultats():
    from src.collecte.parsers.futbol24 import parse_matchs

    joues, a_jouer = parse_matchs(lire("futbol24_resultats.html"), "2025-2026", "url")
    assert a_jouer == [] and len(joues) == 50
    assert (joues[0]["equipe_dom"], joues[0]["buts_dom"], joues[0]["buts_ext"]) == (
        "ASEC Mimosas", 0, 1)
    assert len({m["slug_futbol24"] for m in joues}) == 50  # pas de doublon


def test_futbol24_page_sans_donnees():
    from src.collecte.parsers.futbol24 import parse_matchs

    assert parse_matchs("<html></html>", "2026-2027", "url") == ([], [])

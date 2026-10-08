"""Coordonnées des villes : extraction depuis la page Wikipédia et contrôle du territoire."""
from src.collecte.scrapers.wikipedia_villes import (
    en_cote_divoire,
    parse_coordonnees,
    urls_candidates,
)


def test_parse_coordonnees():
    html = '<script>RLCONF={"wgCoordinates":{"lat":5.336389,"lon":-4.026667},"x":1}</script>'
    assert parse_coordonnees(html) == (5.336389, -4.026667)


def test_parse_coordonnees_absentes():
    assert parse_coordonnees("<html>pas de coordonnées</html>") is None


def test_controle_territoire():
    assert en_cote_divoire(5.34, -4.03)          # Abidjan
    assert not en_cote_divoire(14.85, -15.88)    # Touba (Sénégal) : homonyme rejeté


def test_titre_ivoirien_essaye_en_premier():
    urls = urls_candidates("Touba")
    assert "C%C3%B4te_d%27Ivoire" in urls[0] and urls[1].endswith("/Touba")

"""Joueurs et entraîneurs : pages de catégories et infobox des articles Wikipédia.

Catégorie « Joueurs de l'ASEC Mimosas » -> liste d'articles de joueurs.
Infobox d'un joueur -> identité + parcours daté, club par club :

    en : <th>2007–2008</th><td>→ Germinal Beerschot (loan)</td><td>9</td><td>(0)</td>
    fr : <td>2016 - 2017</td><td>ASEC Mimosas</td><td>0 26 0 (13)</td>
         (les « 0 » sont des clés de tri invisibles)
"""
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

# Titre de section de l'infobox -> type de passage
SECTIONS = {
    "youth career": "jeunes",
    "senior career": "senior",
    "international career": "selection",
    "teams managed": "entraineur",
    "managerial career": "entraineur",
    "parcours junior": "jeunes",
    "parcours amateur": "senior",
    "parcours senior": "senior",
    "parcours professionnel": "senior",
    "sélections en équipe nationale": "selection",
    "parcours entraîneur": "entraineur",
    "carrière d'entraîneur": "entraineur",
}
RE_ANNEES = re.compile(r"^\s*(?:\d{4}|–|-)")
RE_PRET = re.compile(r"\((?:loan|prêt)\)|→", re.IGNORECASE)


# --- Pages de catégories ---------------------------------------------------

def parse_sous_categories(html: str, url: str) -> list[dict]:
    """Sous-catégories (une par club) d'une catégorie « joueurs par club »."""
    soup = BeautifulSoup(html, "lxml")
    return [
        {"categorie": a.get_text(strip=True), "url": urljoin(url, a["href"])}
        for a in soup.select("#mw-subcategories li a[href]")
        # garde les vraies catégories, écarte les liens d'outils (PetScan, Spécial:...)
        if re.search(r"/wiki/(Category|Cat%C3%A9gorie|Catégorie):", a["href"])
    ]


def parse_membres(html: str, url: str) -> tuple[list[dict], str | None]:
    """Articles d'une catégorie, et URL de la page suivante (catégories > 200 articles)."""
    soup = BeautifulSoup(html, "lxml")
    membres = [
        {"titre": a.get_text(strip=True), "url": urljoin(url, a["href"])}
        for a in soup.select("#mw-pages li a[href]")
        # articles seulement : écarte PetScan, vcat, Spécial:... (liens d'outils)
        if re.match(r"^/wiki/[^:]+$", a["href"])
    ]
    suivante = soup.select_one("#mw-pages a[href*='pagefrom']")
    return membres, urljoin(url, suivante["href"]) if suivante else None


# --- Infobox ---------------------------------------------------------------

def _propre(texte: str) -> str:
    texte = re.sub(r"\[\s*\d+\s*\]|\[note \d+\]", "", texte)  # renvois [1]
    return re.sub(r"\s+", " ", texte).strip()


def _annees(texte: str) -> tuple[int | None, int | None]:
    """'2007–2008' -> (2007, 2008) ; '2019–' -> (2019, None) ; '0000 –2000' -> (None, 2000)."""
    texte = texte.replace("0000", "").strip()
    nombres = [int(n) for n in re.findall(r"\d{4}", texte)]
    if not nombres:
        return None, None
    if len(nombres) >= 2:
        return nombres[0], nombres[-1]
    if re.match(r"^[–-]", texte):
        return None, nombres[0]
    if re.search(r"[–-]\s*$", texte):
        return nombres[0], None  # passage en cours
    return nombres[0], nombres[0]


def _stats(cellules: list[str]) -> tuple[int | None, int | None]:
    """Matchs et buts : '33', '(8)' ou '0 33 0 (8)' -> (33, 8)."""
    texte = " ".join(cellules)
    buts = re.findall(r"\((\d+)\)", texte)
    avant = texte.split("(")[0]
    matchs = [int(n) for n in re.findall(r"\d+", avant)]
    return (max(matchs) if matchs else None), (int(buts[-1]) if buts else None)


def _section(texte: str) -> str | None:
    texte = re.sub(r"[\d*‡†]+$", "", texte.lower()).strip()
    return next((v for k, v in SECTIONS.items() if texte.startswith(k)), None)


def _date_naissance(infobox) -> str | None:
    balise = infobox.select_one("span.bday") or infobox.select_one("time[datetime]")
    if not balise:
        return None
    valeur = balise.get("datetime") or balise.get_text(strip=True)
    return valeur if re.match(r"^\d{4}-\d{2}-\d{2}$", valeur) else None


def _champ(infobox, *libelles: str) -> str | None:
    for tr in infobox.find_all("tr"):
        th, td = tr.find("th"), tr.find("td")
        if th and td and _propre(th.get_text(" ")).lower().startswith(libelles):
            return _propre(td.get_text(" "))
    return None


def parse_personne(html: str, url: str, langue: str) -> dict | None:
    """Identité et parcours d'un joueur ou entraîneur ; None si pas d'infobox."""
    soup = BeautifulSoup(html, "lxml")
    infobox = soup.select_one("table.infobox, table.infobox_v2, table.infobox_v3")
    if infobox is None:
        return None

    passages, section = [], None
    for tr in infobox.find_all("tr"):
        cellules = tr.find_all(["th", "td"], recursive=False)
        textes = [_propre(c.get_text(" ")) for c in cellules]
        if len(cellules) == 1 and cellules[0].name == "th":
            section = _section(textes[0])
        elif section and len(textes) >= 2 and RE_ANNEES.match(textes[0]) and textes[1]:
            debut, fin = _annees(textes[0])
            club = re.sub(RE_PRET, "", textes[1]).strip(" ()")
            matchs, buts = _stats(textes[2:])
            passages.append({
                "type": section,
                "debut": debut,
                "fin": fin,
                "club": club,
                "pret": bool(RE_PRET.search(textes[0] + " " + textes[1])),
                "matchs": matchs,
                "buts": buts,
                "ligne_brute": " | ".join(textes),
            })

    titre = soup.select_one("#firstHeading")
    autres = {a.get("lang"): a.get("href") for a in soup.select("a.interlanguage-link-target")}
    return {
        "url": url,
        "langue": langue,
        "nom": _propre(titre.get_text(" ")) if titre else None,
        "nom_complet": _champ(infobox, "full name", "nom complet"),
        "naissance": _date_naissance(infobox),
        "lieu_naissance": _champ(infobox, "place of birth"),
        "nationalite": _champ(infobox, "nationalité", "nationality"),
        "poste": _champ(infobox, "position", "poste"),
        "passages": passages,
        "url_autre_langue": autres.get("fr" if langue == "en" else "en"),
        "source": f"wikipedia_{langue}",
    }

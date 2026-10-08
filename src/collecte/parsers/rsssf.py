"""Extraction des matchs et classements de la Ligue 1 depuis une page RSSSF.

La page est du texte préformaté (<pre>) qui contient aussi la coupe et la Ligue 2 :
on ne garde que la section <a name="ligue1"> jusqu'au titre <h4> suivant.

Exemple de lignes rencontrées :
    Round 1                     -> journée
    Round 1 [Jun 6]             -> journée et date sur la même ligne
    [Sep 21]                    -> date des matchs qui suivent
    SOL              1-1 Stella -> match joué
    SOA              awd Africa Sports    [awarded 3-0; ...]  -> tapis vert
    Moossou          abd Africa Sports    [abandoned ...]     -> match arrêté
    AFAD Djékanou    bye Racing Club      -> exempts (ignoré)
     1.Stade (Abidjan)   30  19  5  6  47-26  62  Champions -> ligne de classement
"""
import html as html_lib
import re
from datetime import date

MOIS = {
    m: i
    for i, m in enumerate(
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        start=1,
    )
}

RE_SECTION = re.compile(r'<a name="ligue1">.*?(?=<h4|\Z)', re.DOTALL | re.IGNORECASE)
RE_PHASE_HTML = re.compile(r"<b>\s*<a name=\"[^\"]*\">(.*?)</a>\s*</b>", re.DOTALL | re.IGNORECASE)
RE_JOURNEE = re.compile(r"^Round (\d+)\s*(?:\[(\w{3}) (\d{1,2})\])?")
RE_DATE = re.compile(r"^\[(\w{3}) (\d{1,2})\]")
RE_TABLEAU = re.compile(r"^(Final Tables?|Halfway Table|Table at abandonment)", re.IGNORECASE)
RE_GROUPE = re.compile(r"^(?:Groupe|Poule) (\w+)\s*$")
RE_LIGNE_CLASSEMENT = re.compile(
    r"^\s*(?P<rang>\d+)\.(?P<equipe>.+?)\s+(?P<j>\d+)\s+(?P<g>\d+)\s+(?P<n>\d+)\s+(?P<p>\d+)"
    r"\s+(?P<bp>\d+)-\s*(?P<bc>\d+)\s+(?P<pts>\d+)\s*(?P<mention>.*)$"
)
# Les noms d'équipe ne contiennent jamais deux espaces de suite : ce qui suit
# l'équipe extérieure après 2 espaces ou plus est une note (ou la suite d'une note).
RE_MATCH = re.compile(
    r"^(?P<dom>\S.*?)\s+(?P<res>\d+-\d+|awd|abd|ppd|canc|n/p|bye)\s+(?P<ext>[^\[]*?)"
    r"(?:\s{2,}|\s*(?=\[)|$)(?P<reste>.*?)\s*$"
)
RE_SCORE_NOTE = re.compile(r"(?:awarded|at) (\d+)-(\d+)")

STATUTS = {"awd": "tapis_vert", "abd": "abandonne", "ppd": "reporte", "canc": "annule"}


def extraire_section_ligue1(html: str) -> list[str]:
    """Renvoie les lignes de texte de la section Ligue 1 (phases marquées par '## ')."""
    m = RE_SECTION.search(html)
    if not m:
        return []
    bloc = RE_PHASE_HTML.sub(lambda p: "\n## " + p.group(1).strip() + "\n", m.group(0))
    bloc = re.sub(r"<[^>]+>", "", bloc)
    return html_lib.unescape(bloc).splitlines()


def construire_date(saison: str, mois: str, jour: str) -> str | None:
    """'2024-2025', 'Sep', '20' -> '2024-09-20'. Août-décembre = 1re année de la saison."""
    if mois not in MOIS:
        return None
    annee_debut, annee_fin = (int(a) for a in saison.split("-"))
    n_mois = MOIS[mois]
    annee = annee_debut if n_mois >= 8 else annee_fin
    try:
        return date(annee, n_mois, int(jour)).isoformat()
    except ValueError:
        return None


def _note(reste: str) -> str:
    return reste.strip().strip("[]").strip()


def _match(m: re.Match, contexte: dict, saison: str, url: str, ligne: str) -> dict | None:
    res = m.group("res")
    note = _note(m.group("reste")) if m.group("reste").startswith("[") else ""
    if res in ("bye", "n/p"):
        return None
    buts_dom = buts_ext = None
    if "-" in res:
        statut = "joue"
        buts_dom, buts_ext = (int(b) for b in res.split("-"))
    else:
        statut = STATUTS[res]
        score = RE_SCORE_NOTE.search(note)
        if res == "awd" and score:
            buts_dom, buts_ext = int(score.group(1)), int(score.group(2))
    return {
        "saison": saison,
        "phase": contexte["phase"],
        "journee": contexte["journee"],
        "date": contexte["date"],
        "equipe_dom": m.group("dom").strip(),
        "equipe_ext": m.group("ext").strip(),
        "buts_dom": buts_dom,
        "buts_ext": buts_ext,
        "statut": statut,
        "note": note or None,
        "ligne_brute": ligne.rstrip(),
        "url_source": url,
        "source": "rsssf",
    }


def parse_page(html: str, saison: str, url: str) -> tuple[list[dict], list[dict]]:
    """Renvoie (matchs, classements) de la Ligue 1 pour une page RSSSF."""
    matchs, classements = [], []
    ctx = {"phase": "Saison reguliere", "journee": None, "date": None,
           "tableau": None, "groupe": None}
    deja_vus = set()

    for ligne in extraire_section_ligue1(html):
        texte = ligne.strip()
        if not texte:
            continue
        if texte.startswith("## "):
            ctx.update(phase=texte[3:], journee=None, date=None, tableau=None, groupe=None)
        elif m := RE_TABLEAU.match(texte):
            ctx.update(tableau=m.group(1).rstrip("s").lower(), groupe=None)
        elif m := RE_GROUPE.match(texte):
            ctx["groupe"] = m.group(1)
        elif m := RE_LIGNE_CLASSEMENT.match(ligne):
            if not ctx["tableau"]:
                continue
            cle = (ctx["phase"], ctx["tableau"], ctx["groupe"], int(m.group("rang")))
            if cle in deja_vus:  # RSSSF répète le classement final en bas de section
                continue
            deja_vus.add(cle)
            classements.append({
                "saison": saison,
                "phase": ctx["phase"],
                "type_tableau": ctx["tableau"],
                "groupe": ctx["groupe"],
                "rang": int(m.group("rang")),
                "equipe": m.group("equipe").strip(),
                **{k: int(m.group(k)) for k in ("j", "g", "n", "p", "bp", "bc", "pts")},
                "mention": m.group("mention").strip() or None,
                "url_source": url,
                "source": "rsssf",
            })
        elif m := RE_JOURNEE.match(texte):
            ctx.update(journee=int(m.group(1)), tableau=None)
            if m.group(2):
                ctx["date"] = construire_date(saison, m.group(2), m.group(3))
        elif m := RE_DATE.match(texte):
            ctx["date"] = construire_date(saison, m.group(1), m.group(2))
        elif ctx["journee"] is not None and not ligne.startswith(" ") and (
            m := RE_MATCH.match(texte)
        ):
            reste = m.group("reste")
            if reste and not reste.startswith("[") and matchs and matchs[-1]["note"]:
                matchs[-1]["note"] += " " + _note(reste)  # note sur deux lignes
            match = _match(m, ctx, saison, url, ligne)
            if match:
                matchs.append(match)

    return matchs, classements

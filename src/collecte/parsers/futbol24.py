"""Futbol24 : calendrier et résultats datés de la saison en cours.

Les matchs sont dans le JSON Nuxt intégré à la page (<script id="__NUXT_DATA__">),
au format « devalue » : une liste plate où les objets pointent vers d'autres
éléments par leur indice.

Un match non encore programmé porte une date fictive (ex. 2026-12-30T15:59) :
on le signale par horaire_provisoire = True.
"""
import json
import re

RE_NUXT = re.compile(r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL)
ENVELOPPES = ("Reactive", "ShallowReactive", "Ref", "ShallowRef")


def _donnees(html: str) -> list:
    m = RE_NUXT.search(html)
    return json.loads(m.group(1)) if m else []


def _resoudre(donnees: list, valeur, profondeur: int = 0):
    """Remplace récursivement les indices par les valeurs qu'ils désignent."""
    if profondeur > 8 or isinstance(valeur, bool) or not isinstance(valeur, int):
        return valeur
    if not 0 <= valeur < len(donnees):
        return valeur
    cible = donnees[valeur]
    if isinstance(cible, dict):
        return {k: _resoudre(donnees, v, profondeur + 1) for k, v in cible.items()}
    if isinstance(cible, list):
        if cible and cible[0] in ENVELOPPES:
            return _resoudre(donnees, cible[1], profondeur + 1)
        return [_resoudre(donnees, v, profondeur + 1) for v in cible]
    return cible


def parse_matchs(html: str, saison: str, url: str) -> tuple[list[dict], list[dict]]:
    """Renvoie (matchs joués, matchs à jouer) avec leur date et heure (UTC)."""
    donnees = _donnees(html)
    joues, a_jouer, vus = [], [], set()
    for i, element in enumerate(donnees):
        if not (isinstance(element, dict) and "team1Score" in element):
            continue
        match = _resoudre(donnees, i)
        if match["slug"] in vus:  # le même match peut apparaître deux fois dans le JSON
            continue
        vus.add(match["slug"])
        date_heure = match.get("date") or ""
        base = {
            "saison": saison,
            "equipe_dom": match["team1"]["name"],
            "equipe_ext": match["team2"]["name"],
            "date": date_heure[:10] or None,
            "date_heure_utc": date_heure or None,
            "slug_futbol24": match["slug"],
            "url_source": url,
            "source": "futbol24",
        }
        buts_dom, buts_ext = str(match["team1Score"]), str(match["team2Score"])
        if buts_dom.isdigit() and buts_ext.isdigit():
            joues.append({**base, "phase": "Saison reguliere", "journee": None,
                          "buts_dom": int(buts_dom), "buts_ext": int(buts_ext),
                          "statut": "joue", "note": None, "ligne_brute": match.get("score1")})
        else:
            a_jouer.append({**base, "horaire_provisoire": date_heure[14:16] == "59"})
    return joues, a_jouer

"""Dessine le MLD (schéma relationnel) de docs/modele_donnees.md en PNG et SVG.

    python docs/scripts/dessiner_mld.py

Tables : clé primaire soulignée, clés étrangères précédées de « # ».
Chaque clé étrangère est reliée par une flèche à la table qu'elle référence.
La disposition reprend celle du MCD (docs/mcd.png) pour faciliter la lecture.
"""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

SORTIE = Path(__file__).resolve().parents[1]

# table : (x, y du centre, clé primaire, colonnes, clés étrangères)
TABLES = {
    "saison": (330, 1950, "id_saison", ["libelle", "annee_debut", "annee_fin", "nb_clubs",
                                         "format", "statut"], []),
    "ville": (850, 1900, "id_ville", ["nom"], []),
    "stade": (850, 1450, "id_stade", ["nom", "capacite"], ["id_ville"]),
    "classement": (2350, 1800, "id_classement", ["phase", "groupe", "type_tableau", "rang",
                                                  "joues, gagnes, nuls, perdus",
                                                  "buts_pour, buts_contre", "points",
                                                  "mention", "source"],
                   ["id_saison", "id_club"]),
    "club": (1350, 1080, "id_club", ["nom", "est_ligue1", "api_id"],
             ["id_ville", "id_stade"]),
    "stat_buteur": (2350, 1080, "id_stat", ["joueur", "buts", "matchs", "source"],
                    ["id_saison", "id_club", "id_personne"]),
    "match": (330, 640, "id_match", ["phase", "journee", "date_match", "buts_dom",
                                      "buts_ext", "statut", "arbitre", "note", "source",
                                      "api_fixture_id"],
              ["id_saison", "id_club_dom", "id_club_ext", "id_stade"]),
    "passage": (1500, 640, "id_passage", ["role", "annee_debut", "annee_fin", "pret",
                                           "matchs", "buts", "club_brut", "source"],
                ["id_personne", "id_club"]),
    "but": (330, 130, "id_but", ["minute", "type_but", "buteur", "passeur"],
            ["id_match", "id_club", "id_personne"]),
    "carton": (1000, 130, "id_carton", ["minute", "couleur", "joueur"],
               ["id_match", "id_club", "id_personne"]),
    "personne": (1700, 130, "id_personne", ["nom", "nom_complet", "date_naissance",
                                             "nationalite", "poste", "est_joueur",
                                             "est_entraineur", "url_wikipedia", "api_id"], []),
    "transfert": (2450, 150, "id_transfert", ["joueur", "date_transfert", "type_transfert",
                                               "source"],
                  ["id_personne", "id_club_depart", "id_club_arrivee"]),
}

# (table, clé étrangère, table référencée, point de passage du lien)
# Les points de passage sont ceux des associations du MCD.
CLES_ETRANGERES = [
    ("match", "id_saison", "saison", (330, 1300)),
    ("stade", "id_ville", "ville", (850, 1690)),
    ("club", "id_ville", "ville", (1300, 1700)),
    ("club", "id_stade", "stade", (1080, 1280)),
    ("match", "id_stade", "stade", (650, 1150)),
    ("match", "id_club_dom", "club", (850, 960)),
    ("match", "id_club_ext", "club", (850, 800)),
    ("classement", "id_saison", "saison", (1500, 2090)),
    ("classement", "id_club", "club", (1850, 1450)),
    ("stat_buteur", "id_saison", "saison", (2850, 2330)),
    ("stat_buteur", "id_club", "club", (1900, 1150)),
    ("stat_buteur", "id_personne", "personne", (2760, -200)),
    ("but", "id_match", "match", (240, 345)),
    ("but", "id_club", "club", (700, 470)),
    ("carton", "id_match", "match", (720, 320)),
    ("carton", "id_club", "club", (1150, 560)),
    ("but", "id_personne", "personne", (1100, -230)),
    ("carton", "id_personne", "personne", (1360, 110)),
    ("passage", "id_club", "club", (1480, 905)),
    ("passage", "id_personne", "personne", (1600, 395)),
    ("transfert", "id_club_depart", "club", (2000, 680)),
    ("transfert", "id_club_arrivee", "club", (2330, 830)),
    ("transfert", "id_personne", "personne", (2080, 160)),
]

LARGEUR, LIGNE, ENTETE = 300, 26, 40
BLEU, VERT, ROUGE = "#1f4e79", "#1e7b4a", "#b03a2e"


def lignes(nom):
    _, _, cle, colonnes, etrangeres = TABLES[nom]
    return [cle, *colonnes, *("#" + fk for fk in etrangeres)]


def boite(nom):
    x, y, *_ = TABLES[nom]
    hauteur = ENTETE + LIGNE * len(lignes(nom)) + 10
    return x - LARGEUR / 2, y - hauteur / 2, LARGEUR, hauteur


def y_ligne(nom, texte):
    _, y0, _, h = boite(nom)
    return y0 + h - ENTETE - LIGNE * (lignes(nom).index(texte) + 0.7)


def bord(nom, vers):
    """Point où le segment centre -> `vers` sort du rectangle de la table."""
    x0, y0, w, h = boite(nom)
    cx, cy = x0 + w / 2, y0 + h / 2
    dx, dy = vers[0] - cx, vers[1] - cy
    t = min(w / 2 / abs(dx) if dx else float("inf"), h / 2 / abs(dy) if dy else float("inf"))
    return cx + dx * t, cy + dy * t


def depart(nom, colonne, vers):
    """Départ du lien : sur le côté, à hauteur de la colonne clé étrangère, si la
    destination est plutôt horizontale ; sinon par le haut ou le bas de la table."""
    x0, _, w, _ = boite(nom)
    cote = x0 + w if vers[0] > x0 + w / 2 else x0
    y = y_ligne(nom, "#" + colonne)
    if x0 <= vers[0] <= x0 + w or abs(vers[1] - y) > abs(vers[0] - cote):
        return bord(nom, vers)
    return cote, y


def dessiner_table(ax, nom):
    x0, y0, w, h = boite(nom)
    ax.add_patch(FancyBboxPatch((x0, y0), w, h, boxstyle="round,pad=0,rounding_size=6",
                                fc="white", ec=BLEU, lw=2, zorder=3))
    ax.add_patch(FancyBboxPatch((x0, y0 + h - ENTETE), w, ENTETE,
                                boxstyle="round,pad=0,rounding_size=6", fc=BLEU, ec=BLEU,
                                lw=2, zorder=4))
    ax.text(x0 + w / 2, y0 + h - ENTETE / 2, nom, ha="center", va="center", color="white",
            fontsize=15, fontweight="bold", zorder=5)
    for i, texte in enumerate(lignes(nom)):
        y = y_ligne(nom, texte)
        cle_primaire, etrangere = i == 0, texte.startswith("#")
        ax.text(x0 + 14, y, texte, ha="left", va="center", fontsize=12, zorder=5,
                fontweight="bold" if cle_primaire or etrangere else "normal",
                color=VERT if etrangere else "black")
        if cle_primaire:
            ax.plot([x0 + 14, x0 + 14 + len(texte) * 7.0], [y - 10, y - 10], color="black",
                    lw=1.2, zorder=5)


def dessiner_lien(ax, table, colonne, cible, passage):
    x1, y1 = depart(table, colonne, passage)
    x2, y2 = bord(cible, passage)
    ax.plot([x1, passage[0]], [y1, passage[1]], color=VERT, lw=1.4, zorder=1)
    ax.add_patch(FancyArrowPatch(passage, (x2, y2), arrowstyle="-|>", mutation_scale=22,
                                 color=VERT, lw=1.4, zorder=2, shrinkA=0, shrinkB=0))
    ax.text(passage[0], passage[1], colonne, ha="center", va="center", fontsize=10.5,
            color=VERT, fontstyle="italic", zorder=6,
            bbox={"fc": "white", "ec": VERT, "boxstyle": "round,pad=0.25", "lw": 0.8})


def main():
    fig, ax = plt.subplots(figsize=(29, 26), dpi=100)
    for lien in CLES_ETRANGERES:
        dessiner_lien(ax, *lien)
    for nom in TABLES:
        dessiner_table(ax, nom)
    ax.text(-40, 2330, "Légende :  id_xxx souligné = clé primaire   ·   #id_xxx (vert) = clé "
            "étrangère   ·   flèche = référence vers la table", fontsize=14, color="#333333",
            ha="left", va="center")
    ax.set_xlim(-60, 2960)
    ax.set_ylim(-300, 2400)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("MLD — Plateforme d'analyse de la Ligue 1 ivoirienne", fontsize=24,
                 fontweight="bold", pad=10)
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(SORTIE / f"mld.{ext}", facecolor="white", bbox_inches="tight")
    print("MLD écrit dans", SORTIE / "mld.png")


if __name__ == "__main__":
    main()

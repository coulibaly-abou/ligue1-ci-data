"""Dessine le MCD (notation Merise) de docs/modele_donnees.md en PNG et SVG.

    python docs/scripts/dessiner_mcd.py

Entités : rectangles (identifiant souligné). Associations : ovales.
Cardinalités : écrites sur chaque lien, du côté de l'entité.
"""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, FancyBboxPatch

SORTIE = Path(__file__).resolve().parents[1]

# nom : (x, y du centre, identifiant, propriétés)
ENTITES = {
    "SAISON": (330, 1950, "id_saison", ["libelle", "annee_debut", "annee_fin", "nb_clubs",
                                         "format", "statut"]),
    "VILLE": (850, 1900, "id_ville", ["nom"]),
    "STADE": (850, 1450, "id_stade", ["nom", "capacite"]),
    "CLASSEMENT": (2350, 1800, "id_classement", ["phase", "groupe", "type_tableau", "rang",
                                                  "joues, gagnes, nuls, perdus",
                                                  "buts_pour, buts_contre", "points",
                                                  "mention", "source"]),
    "CLUB": (1350, 1080, "id_club", ["nom", "est_ligue1", "api_id"]),
    "STAT_BUTEUR": (2350, 1080, "id_stat", ["joueur", "buts", "matchs", "source"]),
    "MATCH": (330, 640, "id_match", ["phase", "journee", "date_match", "buts_dom",
                                      "buts_ext", "statut", "arbitre", "note", "source",
                                      "api_fixture_id"]),
    "PASSAGE": (1500, 640, "id_passage", ["role", "annee_debut", "annee_fin", "pret",
                                           "matchs", "buts", "club_brut", "source"]),
    "BUT": (330, 130, "id_but", ["minute", "type_but", "buteur", "passeur"]),
    "CARTON": (1000, 130, "id_carton", ["minute", "couleur", "joueur"]),
    "PERSONNE": (1700, 130, "id_personne", ["nom", "nom_complet", "date_naissance",
                                             "nationalite", "poste", "est_joueur",
                                             "est_entraineur", "url_wikipedia", "api_id"]),
    "TRANSFERT": (2450, 150, "id_transfert", ["joueur", "date_transfert",
                                               "type_transfert", "source"]),
}

# (association, position, [(entité, cardinalité[, décalage latéral de l'étiquette]), ...])
ASSOCIATIONS = [
    ("APPARTENIR", (330, 1300), [("MATCH", "1,1"), ("SAISON", "0,n")]),
    ("SITUER_STADE", (850, 1690), [("STADE", "0,1"), ("VILLE", "0,n")]),
    ("SITUER_CLUB", (1300, 1700), [("CLUB", "0,1"), ("VILLE", "0,n")]),
    ("DOMICILIER", (1080, 1280), [("CLUB", "0,1"), ("STADE", "0,n")]),
    ("SE_JOUER", (650, 1150), [("MATCH", "0,1"), ("STADE", "0,n")]),
    ("RECEVOIR", (850, 960), [("MATCH", "1,1"), ("CLUB", "0,n")]),
    ("SE_DÉPLACER", (850, 800), [("MATCH", "1,1"), ("CLUB", "0,n")]),
    ("CLASSER_SAISON", (1500, 2090), [("CLASSEMENT", "1,1"), ("SAISON", "0,n", -18)]),
    ("CLASSER_CLUB", (1850, 1450), [("CLASSEMENT", "1,1"), ("CLUB", "0,n")]),
    ("CONCERNER_SAISON", (2700, 2330), [("STAT_BUTEUR", "1,1"), ("SAISON", "0,n", 18)]),
    ("REPRÉSENTER", (1900, 1150), [("STAT_BUTEUR", "0,1"), ("CLUB", "0,n")]),
    ("COMPTABILISER", (2760, -60), [("STAT_BUTEUR", "0,1"), ("PERSONNE", "0,n")]),
    ("CONCERNER_BUT", (240, 345), [("BUT", "1,1"), ("MATCH", "0,n")]),
    ("MARQUER_POUR", (700, 470), [("BUT", "1,1"), ("CLUB", "0,n")]),
    ("CONCERNER_CARTON", (720, 320), [("CARTON", "1,1"), ("MATCH", "0,n")]),
    ("SANCTIONNER", (1150, 560), [("CARTON", "1,1"), ("CLUB", "0,n")]),
    ("MARQUER", (1100, -230), [("BUT", "0,1"), ("PERSONNE", "0,n")]),
    ("RECEVOIR_CARTON", (1360, 110), [("CARTON", "0,1"), ("PERSONNE", "0,n")]),
    ("SE_DÉROULER", (1480, 905), [("PASSAGE", "0,1"), ("CLUB", "0,n")]),
    ("EFFECTUER", (1600, 395), [("PASSAGE", "1,1"), ("PERSONNE", "1,n")]),
    ("QUITTER", (2000, 680), [("TRANSFERT", "0,1"), ("CLUB", "0,n")]),
    ("REJOINDRE", (2330, 830), [("TRANSFERT", "0,1"), ("CLUB", "0,n")]),
    ("TRANSFÉRER", (2080, 160), [("TRANSFERT", "0,1"), ("PERSONNE", "0,n")]),
]

LARGEUR, LIGNE, ENTETE = 300, 30, 44
COULEUR_ENTITE, COULEUR_ENTETE = "#ffffff", "#1f4e79"
COULEUR_ASSO, COULEUR_TRAIT = "#fdf2d0", "#555555"


def boite(nom):
    x, y, _, props = ENTITES[nom]
    hauteur = ENTETE + LIGNE * (len(props) + 1) + 10
    return x - LARGEUR / 2, y - hauteur / 2, LARGEUR, hauteur


def bord(nom, vers):
    """Point où le segment centre -> `vers` sort du rectangle de l'entité."""
    x0, y0, w, h = boite(nom)
    cx, cy = x0 + w / 2, y0 + h / 2
    dx, dy = vers[0] - cx, vers[1] - cy
    if dx == dy == 0:
        return cx, cy
    t = min(w / 2 / abs(dx) if dx else float("inf"), h / 2 / abs(dy) if dy else float("inf"))
    return cx + dx * t, cy + dy * t


def dessiner_entite(ax, nom):
    x0, y0, w, h = boite(nom)
    _, _, ident, props = ENTITES[nom]
    ax.add_patch(FancyBboxPatch((x0, y0), w, h, boxstyle="round,pad=0,rounding_size=8",
                                fc=COULEUR_ENTITE, ec=COULEUR_ENTETE, lw=2, zorder=3))
    ax.add_patch(FancyBboxPatch((x0, y0 + h - ENTETE), w, ENTETE,
                                boxstyle="round,pad=0,rounding_size=8",
                                fc=COULEUR_ENTETE, ec=COULEUR_ENTETE, lw=2, zorder=4))
    ax.text(x0 + w / 2, y0 + h - ENTETE / 2, nom, ha="center", va="center", color="white",
            fontsize=15, fontweight="bold", zorder=5)
    y = y0 + h - ENTETE - LIGNE * 0.8
    ax.text(x0 + 14, y, ident, ha="left", va="center", fontsize=12.5, fontweight="bold",
            zorder=5)
    largeur_txt = len(ident) * 7.1
    ax.plot([x0 + 14, x0 + 14 + largeur_txt], [y - 11, y - 11], color="black", lw=1.2,
            zorder=5)
    for i, prop in enumerate(props, start=1):
        ax.text(x0 + 14, y - i * LIGNE, prop, ha="left", va="center", fontsize=12.5, zorder=5)


def dessiner_association(ax, nom, pos, liens):
    largeur = max(190, len(nom) * 11 + 30)
    for entite, cardinalite, *decalage in liens:
        bx, by = bord(entite, pos)
        ax.plot([bx, pos[0]], [by, pos[1]], color=COULEUR_TRAIT, lw=1.4, zorder=1)
        # cardinalité à 42 px du bord de l'entité, le long du lien
        dx, dy = pos[0] - bx, pos[1] - by
        d = max((dx * dx + dy * dy) ** 0.5, 1)
        lx, ly = bx + dx / d * 42, by + dy / d * 42
        if decalage:  # écarte l'étiquette perpendiculairement au lien (liens voisins)
            lx, ly = lx - dy / d * decalage[0], ly + dx / d * decalage[0]
        ax.text(lx, ly, cardinalite, ha="center", va="center", fontsize=12.5,
                fontweight="bold", color="#b03a2e", zorder=6,
                bbox={"fc": "white", "ec": "none", "pad": 1.5})
    ax.add_patch(Ellipse(pos, largeur, 62, fc=COULEUR_ASSO, ec="#b7950b", lw=1.8, zorder=2))
    ax.text(pos[0], pos[1], nom, ha="center", va="center", fontsize=11.5,
            fontweight="bold", zorder=3)


def main():
    fig, ax = plt.subplots(figsize=(29, 26), dpi=100)
    for nom, pos, liens in ASSOCIATIONS:
        dessiner_association(ax, nom, pos, liens)
    for nom in ENTITES:
        dessiner_entite(ax, nom)
    ax.set_xlim(-60, 2900)
    ax.set_ylim(-300, 2400)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("MCD — Plateforme d'analyse de la Ligue 1 ivoirienne", fontsize=24,
                 fontweight="bold", pad=10)
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(SORTIE / f"mcd.{ext}", facecolor="white", bbox_inches="tight")
    print("MCD écrit dans", SORTIE / "mcd.png")


if __name__ == "__main__":
    main()

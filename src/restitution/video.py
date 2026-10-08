"""Diapositives (PNG 1920x1080) et vidéo MP4 de présentation pour LinkedIn.

    python -m src.restitution.video          # ou : make video  (après make figures)

Sortie : docs/linkedin/diapos/*.png (importables dans Canva, PowerPoint...) et
docs/linkedin/video_ligue1.mp4 (≈ 75 s, sans son : ajouter la voix off du script
docs/linkedin/script_video.md ou une musique dans Canva / CapCut).
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from config.settings import RACINE

FIG = RACINE / "docs" / "figures"
CAPTURES = RACINE / "docs" / "captures"
SORTIE = RACINE / "docs" / "linkedin"
L, H = 1920, 1080
ORANGE, VERT, ENCRE, ENCRE_2, FOND = "#E07000", "#006B45", "#1F2328", "#57606A", "#FFFFFF"
NOMS = {"naif": "Référence naïve", "elo": "Elo", "logreg": "Régression logistique",
        "foret": "Forêt aléatoire", "boosting": "Gradient boosting",
        "mlp": "Réseau de neurones"}


def _police(gras: bool, taille: int):
    for nom in (("segoeuib.ttf" if gras else "segoeui.ttf"),
                ("DejaVuSans-Bold.ttf" if gras else "DejaVuSans.ttf")):
        for dossier in (Path("C:/Windows/Fonts"), Path("/usr/share/fonts/truetype/dejavu")):
            if (dossier / nom).exists():
                return ImageFont.truetype(str(dossier / nom), taille)
    return ImageFont.load_default(taille)


def _cadre(numero: int, total: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (L, H), FOND)
    d = ImageDraw.Draw(img)
    # bandeau aux couleurs de la Côte d'Ivoire
    d.rectangle([0, 0, L // 3, 12], fill=ORANGE)
    d.rectangle([L // 3, 0, 2 * L // 3, 12], fill="#FFFFFF")
    d.rectangle([2 * L // 3, 0, L, 12], fill=VERT)
    d.text((80, H - 60), "Ligue 1 ivoirienne · data science", font=_police(False, 26),
           fill=ENCRE_2)
    d.text((L - 80, H - 60), f"{numero}/{total}", font=_police(False, 26), fill=ENCRE_2,
           anchor="ra")
    return img, d


def _texte_centre(d, y, texte, taille, couleur=ENCRE, gras=True):
    d.text((L // 2, y), texte, font=_police(gras, taille), fill=couleur, anchor="mm")


def _coller(img, source: Path | Image.Image, boite: tuple[int, int, int, int]) -> None:
    """Colle une image (ou un fichier) dans la boîte (x0, y0, x1, y1), proportions gardées."""
    fig = source if isinstance(source, Image.Image) else Image.open(source).convert("RGB")
    x0, y0, x1, y1 = boite
    ratio = min((x1 - x0) / fig.width, (y1 - y0) / fig.height)
    fig = fig.resize((int(fig.width * ratio), int(fig.height * ratio)), Image.LANCZOS)
    img.paste(fig, (x0 + (x1 - x0 - fig.width) // 2, y0 + (y1 - y0 - fig.height) // 2))


def diapo_titre(titre, sous_titre, image, n, total, legende=None):
    img, d = _cadre(n, total)
    d.text((80, 60), titre, font=_police(True, 58), fill=ENCRE)
    if sous_titre:
        d.text((80, 140), sous_titre, font=_police(False, 34), fill=ENCRE_2)
    _coller(img, image, (80, 220, L - 80, H - 120 if not legende else H - 170))
    if legende:
        _texte_centre(d, H - 135, legende, 30, ORANGE)
    return img


def diapo_message(lignes, n, total):
    """Grand message centré : [(texte, taille, couleur), ...]."""
    img, d = _cadre(n, total)
    hauteur = sum(t for _, t, _ in lignes) * 1.6
    y = (H - hauteur) / 2
    for texte, taille, couleur in lignes:
        y += taille * 0.8
        _texte_centre(d, y, texte, taille, couleur)
        y += taille * 0.8
    return img


def diapo_chiffres(titre, chiffres, n, total):
    img, d = _cadre(n, total)
    _texte_centre(d, 200, titre, 58)
    largeur = (L - 160) // len(chiffres)
    for i, (valeur, libelle) in enumerate(chiffres):
        x = 80 + i * largeur + largeur // 2
        d.rounded_rectangle([x - largeur // 2 + 20, 360, x + largeur // 2 - 20, 760],
                            radius=24, fill="#FFF3E6")
        d.text((x, 500), valeur, font=_police(True, 110), fill=ORANGE, anchor="mm")
        for k, ligne in enumerate(libelle.split("\n")):
            d.text((x, 640 + k * 44), ligne, font=_police(False, 34), fill=ENCRE, anchor="mm")
    return img


def construire_diapos() -> list[tuple[Image.Image, float]]:
    json.loads((RACINE / "docs" / "resultats" / "metriques.json")
                   .read_text(encoding="utf-8"))
    matchs = pd.read_parquet(RACINE / "app" / "data" / "matchs.parquet")
    joues = matchs[matchs["statut"] == "joue"]
    pct = joues["resultat"].value_counts(normalize=True) * 100
    glis = pd.read_csv(RACINE / "docs" / "resultats" / "validation_glissante.csv")
    moy = glis.groupby("modele")[["accuracy", "log_loss"]].mean().sort_values("log_loss")
    meilleur = moy.drop("naif").index[0]
    scores = pd.read_parquet(RACINE / "app" / "data" / "scores.parquet")
    part4 = scores.head(4)["pct"].sum()
    saisons = int((joues.groupby("saison").size() >= 90).sum())

    T = 12
    d = [
        (diapo_message([("J'ai essayé de prédire", 80, ENCRE),
                        ("la Ligue 1 ivoirienne", 80, ORANGE),
                        ("avec la data et l'IA", 80, ENCRE),
                        ("Voici ce que j'ai appris.", 40, ENCRE_2)], 1, T), 4.5),
        (diapo_chiffres("Un championnat peu documenté, des données dispersées",
                        [(f"{saisons}", "saisons\n2016 → 2026"),
                         (f"{len(joues):,}".replace(",", " "), "matchs\ncollectés"),
                         ("4", "sources web\net API"),
                         ("6", "modèles\ncomparés")], 2, T), 5.5),
        (diapo_titre("Une vraie plateforme de données", "Collecte automatique → 3 bases → "
                     "modèles → tableau de bord", FIG / "00_architecture.png", 3, T,
                     "Python · MongoDB · PostgreSQL · PyTorch · Streamlit"), 6.5),
        (diapo_titre(f"Constat n°1 : {pct['N']:.0f} % de matchs nuls",
                     "≈ 25 % en Europe — et à peine 2 buts par match",
                     FIG / "01_resultats_par_saison.png", 4, T), 6.5),
        (diapo_titre(f"4 scores = {part4:.0f} % des matchs", "1-1, 1-0, 0-0, 0-1 : un "
                     "championnat très fermé", FIG / "02_scores.png", 5, T), 5.0),
        (diapo_titre("Le score Elo raconte la hiérarchie", "Recalculé après chacun des "
                     f"{len(joues):,} matchs".replace(",", " "), FIG / "03_elo.png", 6, T,
                     "L'ASEC Mimosas domine la décennie"), 6.5),
        (diapo_titre("Le réseau des transferts", "961 mouvements de joueurs · PageRank · "
                     "communautés de Louvain", FIG / "05_reseau.png", 7, T,
                     "L'ASEC, plaque tournante vers l'Europe (Beveren…)"), 6.5),
        (diapo_titre("6 modèles, une validation honnête", "Découpage temporel : chaque "
                     "saison prédite avec les précédentes uniquement",
                     FIG / "06_comparaison_modeles.png", 8, T), 7.0),
        (diapo_titre("Le gain est-il réel ?", "Bootstrap : intervalles de confiance à 95 %",
                     FIG / "08_bootstrap.png", 9, T,
                     "Tous battent le hasard… mais une seule saison ne suffit pas à trancher"),
         6.5),
        (diapo_message([("La leçon", 46, ENCRE_2),
                        (f"Un modèle {NOMS[meilleur]} simple", 74, ORANGE),
                        ("fait aussi bien qu'un réseau de neurones", 60, ENCRE),
                        ((f"{moy.loc[meilleur, 'accuracy']:.0%} de bons pronostics contre "
                         f"{moy.loc['naif', 'accuracy']:.0%} pour « toujours domicile »"),
                         40, ENCRE_2),
                        ("Avec peu de données, l'évaluation compte plus que l'algorithme.",
                         40, VERT)], 10, T), 6.5),
    ]
    capture = CAPTURES / "Prediction.png"
    if capture.exists():
        img, dr = _cadre(11, T)
        dr.text((80, 60), "Un tableau de bord en ligne", font=_police(True, 58), fill=ENCRE)
        dr.text((80, 140), "Classements, fiches clubs, réseau, prédictions des prochains "
                "matchs", font=_police(False, 34), fill=ENCRE_2)
        cap = Image.open(capture).convert("RGB")
        cap = cap.crop((0, 0, cap.width, int(cap.width * 0.55)))
        _coller(img, cap, (80, 220, L - 80, H - 110))
        d.append((img, 6.0))
    d.append((diapo_message([("Code, rapport et démo", 64, ENCRE),
                             ("lien en commentaire", 50, ORANGE),
                             ("Python · SQL · MongoDB · PostgreSQL · PyTorch · Streamlit", 36,
                              ENCRE_2),
                             ("Aboubakar Coulibaly — BUT3 Science des données", 36, VERT)],
                            len(d) + 1, T), 5.0))
    return d


def _image_animee(img: Image.Image, t: float) -> np.ndarray:
    """Léger zoom avant (effet Ken Burns) : t de 0 à 1."""
    z = 1 + 0.025 * t
    w, h = int(L / z), int(H / z)
    x, y = (L - w) // 2, (H - h) // 2
    return np.asarray(img.crop((x, y, x + w, y + h)).resize((L, H), Image.BILINEAR))


def main(fps: int = 25, fondu: float = 0.5) -> None:
    import imageio.v2 as imageio

    (SORTIE / "diapos").mkdir(parents=True, exist_ok=True)
    diapos = construire_diapos()
    for i, (img, _) in enumerate(diapos, start=1):
        img.save(SORTIE / "diapos" / f"{i:02d}.png")
    ecrivain = imageio.get_writer(SORTIE / "video_ligue1.mp4", fps=fps, codec="libx264",
                                  quality=8, pixelformat="yuv420p", macro_block_size=8)
    precedente = None
    for img, duree in diapos:
        n = int(duree * fps)
        for k in range(n):
            cadre = _image_animee(img, k / n)
            if precedente is not None and k < fondu * fps:
                a = k / (fondu * fps)
                cadre = (cadre * a + precedente * (1 - a)).astype(np.uint8)
            ecrivain.append_data(cadre)
        precedente = _image_animee(img, 1.0)
    ecrivain.close()
    total = sum(d for _, d in diapos)
    print(f"{len(diapos)} diapos, vidéo de {total:.0f} s -> {SORTIE / 'video_ligue1.mp4'}")


if __name__ == "__main__":
    main()

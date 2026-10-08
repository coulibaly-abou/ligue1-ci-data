"""Vidéo LinkedIn (≈ 75 s, 1920x1080) : présentation du projet et du site en fonctionnement.

    streamlit run app/Accueil.py --server.port 8599     # dans un autre terminal
    python -m src.restitution.video                    # ou : make video

Sept scènes : identité, carte des clubs (apparition progressive), objectifs, analyses,
Machine Learning, prédiction, conclusion. Les écrans du site sont capturés en direct
(Microsoft Edge sans interface) ; tous les chiffres affichés sont lus dans les résultats
du projet (app/data/). Sortie : docs/linkedin/video_ligue1.mp4, une image clé par scène
dans docs/linkedin/diapos/ et les captures dans docs/linkedin/captures_hd/.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from config.settings import RACINE

sys.path.insert(0, str(RACINE / "app"))
from commun import AUTEUR, NOMS_MODELES, ROLE, carte_clubs, villes_carte

DATA = RACINE / "app" / "data"
SORTIE = RACINE / "docs" / "linkedin"
CAPTURES = SORTIE / "captures_hd"
URL = "http://localhost:8599"
EDGE = Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")
L, H, FPS = 1920, 1080, 25
ORANGE, VERT, ENCRE, ENCRE_2, FOND = "#E07000", "#006B45", "#14211B", "#57606A", "#FFFFFF"
SOMBRE = "#10241B"
TITRE_PROJET = "Ligue 1 Côte d'Ivoire — Data Science & Machine Learning"


# ----------------------------------------------------------------- outils
def police(gras: bool, taille: int):
    for nom in (("segoeuib.ttf" if gras else "segoeui.ttf"),
                ("DejaVuSans-Bold.ttf" if gras else "DejaVuSans.ttf")):
        for dossier in (Path("C:/Windows/Fonts"), Path("/usr/share/fonts/truetype/dejavu")):
            if (dossier / nom).exists():
                return ImageFont.truetype(str(dossier / nom), taille)
    return ImageFont.load_default(taille)


def lisse(t: float) -> float:
    """Courbe d'animation douce, t borné à [0, 1]."""
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def progression(t: float, debut: float, duree: float = 0.7) -> float:
    return lisse((t - debut) / duree)


def texte(img, xy, contenu, taille, couleur=ENCRE, gras=True, alpha=1.0, ancre="la",
          decalage=0):
    """Texte avec fondu (alpha) et légère montée (decalage en pixels)."""
    if alpha <= 0:
        return
    calque = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(calque)
    r, g, b = Image.new("RGB", (1, 1), couleur).getpixel((0, 0))
    d.text((xy[0], xy[1] + decalage), contenu, font=police(gras, taille),
           fill=(r, g, b, int(255 * alpha)), anchor=ancre)
    img.alpha_composite(calque)


def bandeau_drapeau(img, y=0, hauteur=10, largeur=L):
    d = ImageDraw.Draw(img)
    for i, c in enumerate((ORANGE, "#FFFFFF", VERT)):
        d.rectangle([i * largeur // 3, y, (i + 1) * largeur // 3, y + hauteur], fill=c)


def vignette(img, contenu: str, sous: str | None = None, alpha=1.0):
    """Étiquette de scène (fond sombre, accent orange)."""
    if alpha <= 0:
        return
    calque = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(calque)
    f1, f2 = police(True, 38), police(False, 26)
    largeur = max(d.textlength(contenu, font=f1), d.textlength(sous or "", font=f2)) + 70
    hauteur = 120 if sous else 78
    y = H - 60 - hauteur  # en bas à gauche : ne masque pas les titres des pages
    d.rounded_rectangle([40, y, 40 + largeur, y + hauteur], radius=16,
                        fill=(16, 36, 27, int(235 * alpha)))
    d.rectangle([40, y, 48, y + hauteur], fill=(224, 112, 0, int(255 * alpha)))
    d.text((75, y + 16), contenu, font=f1, fill=(255, 255, 255, int(255 * alpha)))
    if sous:
        d.text((75, y + 66), sous, font=f2, fill=(220, 228, 224, int(255 * alpha)))
    img.alpha_composite(calque)


def encadre(img, boite, etiquette, alpha=1.0, dessous=False):
    """Cadre orange autour d'une zone de l'écran + étiquette."""
    if alpha <= 0:
        return
    calque = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(calque)
    a = int(255 * alpha)
    d.rounded_rectangle(boite, radius=14, outline=(224, 112, 0, a), width=6)
    f = police(True, 28)
    w = d.textlength(etiquette, font=f) + 36
    x0, y0 = boite[0], (boite[3] + 10) if dessous else max(boite[1] - 58, 0)
    d.rounded_rectangle([x0, y0, x0 + w, y0 + 48], radius=10, fill=(224, 112, 0, a))
    d.text((x0 + 18, y0 + 8), etiquette, font=f, fill=(255, 255, 255, a))
    img.alpha_composite(calque)


def plan(capture: Image.Image, y_css: float, t: float, zoom=0.03, dy_css=0.0):
    """Fenêtre 16:9 de la capture (largeur entière), avec léger zoom et défilement."""
    echelle = capture.width / 1600  # captures en 1600 px CSS
    hauteur = capture.width * 9 / 16
    y = (y_css + dy_css * lisse(t)) * echelle
    z = 1 + zoom * lisse(t)
    w, h = capture.width / z, hauteur / z
    x0 = (capture.width - w) / 2
    y0 = min(max(y + (hauteur - h) / 2, 0), capture.height - h)
    vue = capture.crop((int(x0), int(y0), int(x0 + w), int(y0 + h)))
    return vue.resize((L, H), Image.LANCZOS).convert("RGBA")


# ------------------------------------------------------------- captures
def capturer(page: str, sortie: Path, largeur=1600, hauteur=4400, echelle=1.5):
    """Capture d'une page du site avec Edge sans interface (2 passages : cache chaud)."""
    for _ in range(2):
        subprocess.run([str(EDGE), "--headless=new", "--hide-scrollbars",
                        f"--force-device-scale-factor={echelle}",
                        f"--window-size={largeur},{hauteur}", "--virtual-time-budget=60000",
                        f"--screenshot={sortie}", f"{URL}/{page}"],
                       check=False, capture_output=True, timeout=180)


def captures_site(reutiliser: bool = False) -> dict[str, Image.Image]:
    CAPTURES.mkdir(parents=True, exist_ok=True)
    pages = {"accueil": "", "championnat": "championnat", "club": "club",
             "prediction": "prediction", "modeles": "modeles"}
    for nom, page in pages.items():
        if not (reutiliser and (CAPTURES / f"{nom}.png").exists()):
            capturer(page, CAPTURES / f"{nom}.png")
    return {nom: Image.open(CAPTURES / f"{nom}.png").convert("RGB") for nom in pages}


def images_carte(villes: pd.DataFrame, reutiliser: bool = False
                 ) -> tuple[list[Image.Image], pd.DataFrame]:
    """Carte avec 0, 1, 2… villes : les clubs apparaissent du moins au plus représenté."""
    dossier = CAPTURES / "carte"
    dossier.mkdir(parents=True, exist_ok=True)
    ordre = villes.sort_values(["n_clubs", "matchs"]).reset_index(drop=True)
    images = []
    for k in range(len(ordre) + 1):
        fig = carte_clubs(ordre.head(k) if k else ordre.head(1).iloc[0:0], hauteur=1000)
        fig.update_layout(width=1080, height=1000, paper_bgcolor="white")
        html = dossier / f"carte_{k:02d}.html"
        fig.write_html(html, include_plotlyjs="cdn", config={"displayModeBar": False})
        png = dossier / f"carte_{k:02d}.png"
        if reutiliser and png.exists():
            images.append(Image.open(png).convert("RGB").crop((0, 0, 1080, 1000)))
            continue
        subprocess.run([str(EDGE), "--headless=new", "--hide-scrollbars",
                        "--window-size=1100,1020", "--virtual-time-budget=15000",
                        f"--screenshot={png}", html.as_uri()],
                       check=False, capture_output=True, timeout=120)
        images.append(Image.open(png).convert("RGB").crop((0, 0, 1080, 1000)))
    return images, ordre


# ----------------------------------------------------------------- scènes
def scene_intro(t, duree):
    img = Image.new("RGBA", (L, H), FOND)
    a = progression(t, 0.3)
    texte(img, (L // 2, 400), AUTEUR, 96, ENCRE, alpha=a, ancre="mm",
          decalage=int(30 * (1 - a)))
    b = progression(t, 1.0)
    texte(img, (L // 2, 500), ROLE, 54, ORANGE, alpha=b, ancre="mm",
          decalage=int(20 * (1 - b)))
    c = progression(t, 2.2, 0.9)
    if c > 0:
        largeur = int(560 * c)
        d = ImageDraw.Draw(img)
        x0 = L // 2 - largeur // 2
        for i, col in enumerate((ORANGE, "#E9E6DF", VERT)):
            d.rectangle([x0 + i * largeur // 3, 575, x0 + (i + 1) * largeur // 3, 581],
                        fill=col)
    e = progression(t, 2.9)
    texte(img, (L // 2, 650), TITRE_PROJET, 46, ENCRE_2, gras=False, alpha=e, ancre="mm",
          decalage=int(20 * (1 - e)))
    return img


def scene_carte(t, duree, cartes, ordre, total_clubs):
    img = Image.new("RGBA", (L, H), FOND)
    debut, fin = 1.0, duree - 3.0
    k = int(np.clip((t - debut) / (fin - debut), 0, 1) * (len(cartes) - 1) + 0.5)
    img.paste(cartes[k], (60, 50))
    a = progression(t, 0.2)
    texte(img, (1200, 250), "INTRODUCTION", 26, ORANGE, alpha=a)
    texte(img, (1200, 295), "Cartographier les clubs", 54, ENCRE, alpha=a)
    texte(img, (1200, 360), "de Ligue 1 Côte d'Ivoire", 54, ENCRE, alpha=a)
    vues = ordre.head(k)
    texte(img, (1200, 470), f"{int(vues['n_clubs'].sum())}", 120, ORANGE, alpha=a)
    texte(img, (1200, 610), f"clubs sur {total_clubs}  ·  {len(vues)} villes", 34,
          ENCRE_2, gras=False, alpha=a)
    if k:
        derniere = vues.iloc[-1]
        texte(img, (1200, 690), f"{derniere['ville']} : {int(derniere['n_clubs'])} club"
              f"{'s' if derniere['n_clubs'] > 1 else ''}", 36, ENCRE, alpha=a)
    texte(img, (1200, 900), "Coordonnées : articles Wikipédia des villes", 24, ENCRE_2,
          gras=False, alpha=a)
    return img


def scene_objectifs(t, duree):
    img = Image.new("RGBA", (L, H), FOND)
    bandeau_drapeau(img, 0, 8)
    a = progression(t, 0.1)
    texte(img, (200, 150), "OBJECTIFS DE L'ÉTUDE", 30, ORANGE, alpha=a)
    texte(img, (200, 200), "Ce que l'étude cherche à établir", 64, ENCRE, alpha=a)
    objectifs = ["Analyser les performances des clubs",
                 "Étudier les dynamiques du championnat",
                 "Identifier les facteurs liés aux résultats",
                 "Analyser le réseau des clubs et des joueurs",
                 "Comparer plusieurs modèles prédictifs",
                 "Prédire les résultats des matchs"]
    for i, o in enumerate(objectifs):
        b = progression(t, 1.0 + i * 0.8)
        y = 360 + i * 105
        if b > 0:
            d = ImageDraw.Draw(img)
            d.rounded_rectangle([200, y + 8, 216, y + 24], radius=4, fill=ORANGE)
        texte(img, (250, y), o, 46, ENCRE, gras=False, alpha=b, decalage=int(18 * (1 - b)))
    return img


def scene_plan(t, duree, capture, y_css, titre, sous, boite=None, etiquette=None,
               dy_css=0.0):
    img = plan(capture, y_css, t / duree, dy_css=dy_css)
    vignette(img, titre, sous, alpha=progression(t, 0.3))
    if boite:
        encadre(img, boite, etiquette, alpha=progression(t, 1.3))
    return img


def scene_ml(t, duree, capture, y_css, m):
    if t < 4.5:
        img = Image.new("RGBA", (L, H), FOND)
        a = progression(t, 0.1)
        texte(img, (L // 2, 300), "Machine Learning", 92, ENCRE, alpha=a, ancre="mm")
        texte(img, (L // 2, 385), "six modèles comparés avec le même protocole temporel", 36,
              ENCRE_2, gras=False, alpha=a, ancre="mm")
        modeles = ["elo", "logreg", "foret", "boosting", "mlp"]
        f = police(True, 36)
        largeurs = [ImageDraw.Draw(img).textlength(NOMS_MODELES[x], font=f) + 60
                    for x in modeles]
        x = (L - sum(largeurs) - 24 * (len(modeles) - 1)) / 2
        for i, (nom, w) in enumerate(zip(modeles, largeurs, strict=True)):
            b = progression(t, 0.9 + i * 0.45, 0.5)
            if b > 0:
                calque = Image.new("RGBA", img.size, (0, 0, 0, 0))
                d = ImageDraw.Draw(calque)
                y = 520 + int(20 * (1 - b))
                d.rounded_rectangle([x, y, x + w, y + 80], radius=40,
                                    fill=(255, 243, 230, int(255 * b)),
                                    outline=(224, 112, 0, int(255 * b)), width=3)
                d.text((x + w / 2, y + 40), NOMS_MODELES[nom], font=f, anchor="mm",
                       fill=(20, 33, 27, int(255 * b)))
                img.alpha_composite(calque)
            x += w + 24
        return img
    t2, d2 = t - 4.5, duree - 4.5
    glis = m["validation_glissante_moyenne"]
    retenu = m["modele_retenu"]
    img = plan(capture, y_css, t2 / d2)
    vignette(img, "Comparaison des modèles",
             f"validation glissante · {m['protocole']['n_glissante']} matchs prédits",
             alpha=progression(t2, 0.2))
    encadre(img, (440, 455, 1810, 790),
            f"{NOMS_MODELES[retenu]} : {glis[retenu]['accuracy']:.1%} de bons pronostics "
            f"contre {glis['naif']['accuracy']:.1%} (référence naïve)".replace(".", ","),
            alpha=progression(t2, 1.2), dessous=True)
    return img


def scene_prediction(t, duree, capture, y_css, match):
    img = plan(capture, y_css, t / duree, zoom=0.02)
    vignette(img, "Prédiction", "probabilités calculées avant le match",
             alpha=progression(t, 0.2))
    a = progression(t, 1.0)
    if a <= 0:
        return img
    calque = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(calque)
    x0, y0, x1, y1 = 1050, 300, 1860, 960
    d.rounded_rectangle([x0, y0 + int(30 * (1 - a)), x1, y1 + int(30 * (1 - a))], radius=22,
                        fill=(255, 255, 255, int(248 * a)),
                        outline=(224, 112, 0, int(255 * a)), width=4)
    img.alpha_composite(calque)
    dy = int(30 * (1 - a))
    texte(img, (x0 + 45, y0 + 40 + dy), "MATCH À VENIR · SAISON 2026-2027", 24, ORANGE,
          alpha=a)
    texte(img, (x0 + 45, y0 + 80 + dy), f"{match['dom']} – {match['ext']}", 44, ENCRE,
          alpha=a)
    lignes = [("Victoire domicile", match["p_dom"], ORANGE),
              ("Match nul", match["p_nul"], "#9A9A94"),
              ("Victoire extérieur", match["p_ext"], VERT)]
    for i, (lib, p, couleur) in enumerate(lignes):
        b = progression(t, 1.8 + i * 0.5, 0.9)
        y = y0 + 200 + i * 135 + dy
        # valeur exacte affichée d'emblée : seule la barre est animée
        texte(img, (x0 + 45, y), f"{lib} : {p * 100:.0f} %", 38, ENCRE, alpha=a)
        d2 = ImageDraw.Draw(img)
        d2.rounded_rectangle([x0 + 45, y + 58, x1 - 45, y + 82], radius=12, fill="#EEF0EE")
        if b > 0:
            d2.rounded_rectangle([x0 + 45, y + 58, x0 + 45 + int((x1 - x0 - 90) * p * b),
                                  y + 82], radius=12, fill=couleur)
    return img


def scene_fin(t, duree, capture):
    fond = plan(capture, 0, 0.0, zoom=0.0).convert("RGB").filter(ImageFilter.GaussianBlur(6))
    voile = Image.new("RGB", (L, H), SOMBRE)
    img = Image.blend(fond, voile, 0.86).convert("RGBA")
    etapes = ["Data", "Analyse", "Modélisation", "Prédiction"]
    f = police(True, 64)
    d = ImageDraw.Draw(img)
    fleche = "  →  "
    morceaux = []
    for i, e in enumerate(etapes):
        morceaux.append((e, i))
        if i < len(etapes) - 1:
            morceaux.append((fleche, i + 0.5))
    largeur = sum(d.textlength(x, font=f) for x, _ in morceaux)
    x = (L - largeur) / 2
    for contenu, rang in morceaux:
        a = progression(t, 0.3 + rang * 0.6, 0.5)
        couleur = "#F5A04A" if contenu.strip() == "→" else "#FFFFFF"
        texte(img, (x, 300), contenu, 64, couleur, alpha=a, decalage=int(15 * (1 - a)))
        x += d.textlength(contenu, font=f)
    b = progression(t, 3.4)
    texte(img, (L // 2, 560), AUTEUR, 88, "#FFFFFF", alpha=b, ancre="mm",
          decalage=int(20 * (1 - b)))
    texte(img, (L // 2, 650), ROLE, 50, "#F5A04A", alpha=b, ancre="mm")
    c = progression(t, 4.4)
    texte(img, (L // 2, 760), "Ligue 1 Côte d'Ivoire — Data Science Project", 38,
          "#C8D3CD", gras=False, alpha=c, ancre="mm")
    bandeau_drapeau(img, H - 10, 10)
    return img


# ---------------------------------------------------------------- montage
def main(reutiliser: bool = False, apercu: bool = False) -> None:
    """reutiliser : garder les captures existantes ; apercu : images clés seulement."""
    import imageio.v2 as imageio

    m = json.loads((DATA / "modele" / "metriques.json").read_text(encoding="utf-8"))
    clubs = pd.read_parquet(DATA / "clubs.parquet")
    resultats = pd.read_parquet(DATA / "resultats_club.parquet")
    prochains = pd.read_parquet(DATA / "modele" / "predictions_a_venir.parquet")
    villes = villes_carte(clubs, resultats)
    # Match illustré : affiche réelle restant à jouer, celle du simulateur par défaut
    match = prochains[(prochains["dom"] == "ASEC Mimosas")
                      & (prochains["ext"] == "AFAD Djékanou")]
    match = (match if len(match) else prochains).iloc[0]

    ecrans = captures_site(reutiliser)
    cartes, ordre = images_carte(villes, reutiliser)

    scenes = [
        ("01_intro", 6.0, scene_intro, {}),
        ("02_carte", 11.0, scene_carte, {"cartes": cartes, "ordre": ordre,
                                         "total_clubs": len(clubs)}),
        ("03_objectifs", 8.5, scene_objectifs, {}),
        ("04a_championnat", 6.0, scene_plan, {
            "capture": ecrans["championnat"], "y_css": 170,
            "titre": "Analyse du championnat", "sous": "classement recalculé et évolution",
            "boite": (1000, 420, 1830, 1060), "etiquette": "Évolution du rang par journée"}),
        ("04b_rangs", 5.5, scene_plan, {
            "capture": ecrans["championnat"], "y_css": 1330,
            "titre": "Performances par saison", "sous": "rang final de chaque club",
            "dy_css": 120}),
        ("04c_club", 6.0, scene_plan, {
            "capture": ecrans["club"], "y_css": 0,
            "titre": "Performances des clubs", "sous": "bilan, forme et évolution",
            "boite": (395, 300, 1880, 640), "etiquette": "Bilan calculé sur tous les matchs"}),
        ("05_ml", 12.0, scene_ml, {"capture": ecrans["modeles"], "y_css": 330, "m": m}),
        ("06_prediction", 10.0, scene_prediction, {
            "capture": ecrans["prediction"], "y_css": 0, "match": match}),
        ("07_fin", 8.0, scene_fin, {"capture": ecrans["accueil"]}),
    ]

    (SORTIE / "diapos").mkdir(parents=True, exist_ok=True)
    for ancien in (SORTIE / "diapos").glob("*.png"):
        ancien.unlink()
    if apercu:
        for nom, duree, fonction, args in scenes:
            fonction(duree * 0.85, duree, **args).convert("RGB").save(
                SORTIE / "diapos" / f"{nom}.png")
        print("Aperçu : images clés dans docs/linkedin/diapos/")
        return
    ecrivain = imageio.get_writer(SORTIE / "video_ligue1.mp4", fps=FPS, codec="libx264",
                                  quality=8, pixelformat="yuv420p", macro_block_size=8)
    precedente, fondu = None, int(0.4 * FPS)
    for nom, duree, fonction, args in scenes:
        n = int(duree * FPS)
        for k in range(n):
            cadre = np.asarray(fonction(k / FPS, duree, **args).convert("RGB"))
            if precedente is not None and k < fondu:
                a = k / fondu
                cadre = (cadre * a + precedente * (1 - a)).astype(np.uint8)
            ecrivain.append_data(cadre)
            if k == int(n * 0.85):  # image clé de la scène, animations terminées
                Image.fromarray(cadre).save(SORTIE / "diapos" / f"{nom}.png")
        precedente = cadre
    ecrivain.close()
    total = sum(d for _, d, _, _ in scenes)
    print(f"{len(scenes)} scènes, vidéo de {total:.0f} s -> {SORTIE / 'video_ligue1.mp4'}")


if __name__ == "__main__":
    main(reutiliser="--reutiliser" in sys.argv, apercu="--apercu" in sys.argv)

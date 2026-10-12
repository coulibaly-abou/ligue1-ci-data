"""Vidéo LinkedIn narrée (≈ 90 s, 1920x1080, MP4 H.264 + AAC) : profil, contexte,
problématique et objectifs, données et méthodes, résultats, conclusion.

    streamlit run app/Accueil.py --server.port 8599     # dans un autre terminal
    python -m src.restitution.video_pro                # ou : make video-pro
    python -m src.restitution.video_pro --reutiliser   # garder captures et voix existantes
    python -m src.restitution.video_pro --apercu       # images clés seulement (rapide)
    python -m src.restitution.video_pro --sans-voix    # musique + sous-titres (voix à enregistrer)
    python -m src.restitution.video_pro --sans-voix --sans-musique   # muette, sous-titres seuls

La version muette d'origine reste produite par src/restitution/video.py.

- Voix off : voix françaises de Windows (hors ligne, tts_windows.ps1).
- Musique : générée par ce script (accords et arpèges synthétisés) : aucun droit d'auteur.
- Sous-titres : incrustés dans l'image et fournis à part (.srt) pour LinkedIn.
- Chiffres : lus dans app/data/ ; verifier_narration() bloque le montage si un chiffre
  prononcé ne correspond plus aux résultats (pipeline relancé).
Sorties dans docs/linkedin/ : video_ligue1_pro.mp4, video_ligue1_pro.srt, audio/,
diapos_pro/ (une image clé par séquence).
"""
import hashlib
import json
import re
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw

from src.restitution import video as v
from src.restitution.video import (
    ENCRE,
    ENCRE_2,
    FPS,
    ORANGE,
    VERT,
    H,
    L,
    bandeau_drapeau,
    capturer,
    chiffres_pipeline,
    images_carte,
    plan,
    police,
    progression,
    texte,
)

sys.path.insert(0, str(v.RACINE / "app"))
from commun import FORMATION, LIENS, NOMS_MODELES, villes_carte

DATA = v.DATA
SORTIE = v.SORTIE
AUDIO = SORTIE / "audio"
DIAPOS = SORTIE / "diapos_pro"
FICHIER = SORTIE / "video_ligue1_pro.mp4"
TTS = Path(__file__).with_name("tts_windows.ps1")
VOIX, VITESSE = "Paul", 1.2
SR = 44_100
SOMBRE_1, SOMBRE_2 = (10, 34, 25), (20, 33, 27)
CLAIR = "#F5A04A"
Y_SOUS_TITRES = 935  # tout le contenu des séquences reste au-dessus de cette ligne

NOM = "ABOUBAKAR COULIBALY"
DOMAINES = "Data Science  •  Statistique  •  Machine Learning"
DOMAINES_FIN = "Data Science | Data Analysis | Modélisation statistique"
RECHERCHE = "À la recherche d'un stage et d'une alternance"


# ------------------------------------------------------------------ narration
def P(affiche: str, dit: str | None = None) -> tuple[str, str | None]:
    """Phrase de narration : sous-titre affiché, texte prononcé s'il diffère (sigles
    épelés, nombres en lettres)."""
    return affiche, dit


NARRATION = {
    "01_profil": [
        P("Aboubakar Coulibaly, étudiant en BUT 3 Science des Données, parcours "
         "Exploration et Modélisation Statistique.",
         "Aboubakar Coulibaly, étudiant en B U T 3 Science des Données, parcours "
         "Exploration et Modélisation Statistique."),
        P("Il recherche un stage et une alternance en Data Science.", None),
    ],
    "02_contexte": [
        P("La Ligue 1 ivoirienne forme des joueurs pour l'Afrique et l'Europe.", None),
        P("Pourtant, ses données sont dispersées et presque jamais analysées.", None),
        P("Ce projet rassemble dix saisons : 31 clubs, répartis dans 17 villes.",
         "Ce projet rassemble dix saisons : trente et un clubs, répartis dans dix-sept "
         "villes."),
    ],
    "03_objectifs": [
        P("Problématique : que révèlent les données publiques sur ce championnat ?", None),
        P("Et peut-on prédire un match mieux qu'une règle naïve ?", None),
        P("Quatre objectifs : constituer une base fiable, analyser les performances "
         "des clubs,", None),
        P("étudier le réseau des mouvements de joueurs, et comparer six modèles de "
         "prédiction.", None),
    ],
    "04_methodes": [
        P("Quatre sources web sont collectées en Python et archivées dans MongoDB.",
         "Quatre sources web sont collectées en Python et archivées dans Mongo D B."),
        P("Un ETL recoupe les scores et harmonise 102 noms en 31 clubs : 1 934 matchs dans "
          "PostgreSQL.",
          "Un E T L recoupe les scores et harmonise cent deux noms en trente et un clubs : "
          "mille neuf cent trente-quatre matchs dans Postgre S Q L."),
        P("Méthodes : requêtes SQL, analyse de réseau, et Machine Learning en validation "
         "temporelle.",
         "Méthodes : requêtes S Q L, analyse de réseau, et Machine Learning en validation "
         "temporelle."),
    ],
    "05a_constats": [
        P("Premiers constats : 30 % de matchs nuls, à peine 2 buts par match,",
         "Premiers constats : trente pour cent de matchs nuls, à peine deux buts par "
         "match,"),
        P("et 6 titres sur 10 pour l'ASEC Mimosas.",
         "et six titres sur dix pour l'Asec Mimosas."),
    ],
    "05b_modeles": [
        P("Chaque saison est prédite avec les seules saisons précédentes : 1 141 matchs.",
         "Chaque saison est prédite avec les seules saisons précédentes : mille cent "
         "quarante et un matchs."),
        P("Un simple modèle Elo atteint 43,7 % de bons pronostics, contre 35,4 % pour la "
         "référence naïve.",
         "Un simple modèle Élo atteint quarante-trois virgule sept pour cent de bons "
         "pronostics, contre trente-cinq virgule quatre pour cent pour la référence naïve."),
        P("Le gain est significatif, mais les modèles restent trop proches pour être "
         "départagés.", None),
    ],
    "05c_prediction": [
        P("L'application Streamlit donne ensuite les probabilités de chaque match à venir.",
         None),
    ],
    "06_conclusion": [
        P("De la collecte web au Machine Learning : un projet complet.", None),
        P("Aboubakar Coulibaly recherche un stage et une alternance.", None),
    ],
}
DEBUT_VOIX, PAUSE, FIN_MIN = 0.6, 0.25, 0.9  # secondes
DUREE_MIN = {"01_profil": 7.0, "06_conclusion": 10.0}


def faits() -> dict:
    """Tous les chiffres de la vidéo, recalculés à partir des résultats du projet."""
    m = json.loads((DATA / "modele" / "metriques.json").read_text(encoding="utf-8"))
    matchs = pd.read_parquet(DATA / "matchs.parquet")
    joues = matchs[matchs["statut"] == "joue"]
    palmares = pd.read_parquet(DATA / "palmares.parquet")
    clubs = pd.read_parquet(DATA / "clubs.parquet")
    mouvements = pd.read_parquet(DATA / "reseau_mouvements.parquet")
    departs = mouvements[mouvements["depart_ligue1"].astype(bool)
                         & ~mouvements["arrivee_ligue1"].astype(bool)]
    sources = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
    glis = m["validation_glissante_moyenne"]
    test = {r["modele"]: r for r in m["resultats_test"]}
    boot = m["bootstrap_vs_naif"][m["modele_retenu"]]
    return {
        "m": m, "glis": glis, "retenu": m["modele_retenu"],
        "matchs": len(joues), "clubs": len(clubs), "villes": clubs["ville"].nunique(),
        "saisons": len(palmares), "nuls": (joues["resultat"] == "N").mean(),
        "buts": (joues["buts_dom"] + joues["buts_ext"]).mean(),
        "titres_asec": int((palmares["champion"] == "ASEC Mimosas").sum()),
        "mouvements": len(mouvements), "departs": len(departs),
        "part_asec": (departs["depart"] == "ASEC Mimosas").mean(),
        "n_glissante": m["protocole"]["n_glissante"], "n_test": m["protocole"]["n_test"],
        "variantes": sources["alias_clubs"]["variantes"],
        "test_retenu": test[m["modele_retenu"]]["accuracy"], "test_naif": test["naif"]["accuracy"],
        "ic_glissante": boot["glissante"]["ic95"], "ic_test": boot["test"]["ic95"],
    }


def pct(x: float, decimales: int = 1) -> str:
    return f"{x * 100:.{decimales}f}".replace(".", ",") + " %"


def verifier_narration(f: dict) -> None:
    """Chaque chiffre prononcé doit correspondre aux résultats actuels."""
    texte_complet = " ".join(s for scene in NARRATION.values() for s, _ in scene)
    attendus = [f"{f['clubs']} clubs", f"{f['villes']} villes", f"{f['variantes']} noms",
                f"{f['matchs']:,}".replace(",", " ") + " matchs",
                f"{f['n_glissante']:,}".replace(",", " ") + " matchs",
                f"{round(f['nuls'] * 100)} % de matchs nuls",
                f"{round(f['buts'])} buts par match",
                f"{f['titres_asec']} titres sur {f['saisons']}",
                pct(f["glis"][f["retenu"]]["accuracy"]), pct(f["glis"]["naif"]["accuracy"])]
    manquants = [a for a in attendus if a not in texte_complet]
    if f["retenu"] != "elo":
        manquants.append("modèle retenu : Elo")
    if any(b["glissante"]["ic95"][1] >= 0 for b in f["m"]["bootstrap_vs_naif"].values()):
        manquants.append("tous les modèles significativement meilleurs que la référence")
    if not f["ic_test"][0] < 0 < f["ic_test"][1]:  # la vidéo dit « non significatif »
        manquants.append("saison test : écart devenu significatif, revoir le texte")
    if manquants:
        raise SystemExit("Narration à mettre à jour, chiffres différents des résultats : "
                         + " ; ".join(manquants))


# ------------------------------------------------------------------- audio
def lire_wav(chemin: Path) -> np.ndarray:
    """WAV PCM 16 bits -> mono float32 rééchantillonné à SR."""
    with wave.open(str(chemin)) as w:
        sr, n, canaux = w.getframerate(), w.getnframes(), w.getnchannels()
        x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768
    x = x.reshape(-1, canaux).mean(axis=1)
    if sr != SR:
        x = np.interp(np.arange(int(len(x) * SR / sr)) * sr / SR, np.arange(len(x)), x)
    # retire les silences de début et de fin produits par la synthèse
    actif = np.flatnonzero(np.abs(x) > 0.01)
    return x[max(actif[0] - 400, 0):actif[-1] + 2000] if len(actif) else x


def ecrire_wav(chemin: Path, stereo: np.ndarray) -> None:
    with wave.open(str(chemin), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(stereo, -1, 1) * 32767).astype(np.int16).tobytes())


def synthese(phrase: str, reutiliser: bool) -> np.ndarray:
    AUDIO.mkdir(parents=True, exist_ok=True)
    cle = hashlib.sha1(f"{VOIX}|{VITESSE}|{phrase}".encode()).hexdigest()[:12]
    chemin = AUDIO / f"voix_{cle}.wav"
    if not (reutiliser and chemin.exists()):
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                        str(TTS), "-Texte", phrase, "-Sortie", str(chemin), "-Voix", VOIX,
                        "-Vitesse", str(VITESSE)], check=True, capture_output=True)
    return lire_wav(chemin)


def musique(duree: float, voix: np.ndarray) -> np.ndarray:
    """Nappe d'accords + arpège doux, synthétisés (libres de droits), atténués sous la voix."""
    n = int(duree * SR)
    t = np.arange(n) / SR
    note = lambda midi: 440 * 2 ** ((midi - 69) / 12)
    # La mineur – Fa – Do – Sol, une mesure de 2,4 s par accord
    accords = [(57, 60, 64), (53, 57, 60), (48, 55, 60), (55, 59, 62)]
    mesure = 2.4
    sortie = np.zeros(n, dtype=np.float32)
    for k in range(int(duree / mesure) + 1):
        a = accords[k % 4]
        d0, d1 = int(k * mesure * SR), min(int((k + 1) * mesure * SR + 0.8 * SR), n)
        if d0 >= n:
            break
        tt = t[d0:d1] - k * mesure
        env = np.minimum(1, tt / 0.6) * np.minimum(1, (tt[-1] - tt + 1e-3) / 0.8)
        nappe = sum(np.sin(2 * np.pi * note(m) * tt) + 0.5 * np.sin(2 * np.pi * note(m) * 1.004 * tt)
                    + 0.15 * np.sin(4 * np.pi * note(m) * tt) for m in a)
        basse = np.sin(2 * np.pi * note(a[0] - 12) * tt)
        sortie[d0:d1] += (0.10 * nappe + 0.16 * basse) * env
        for j in range(8):  # arpège en croches
            p0 = d0 + int(j * mesure / 8 * SR)
            if p0 >= n:
                break
            p1 = min(p0 + int(0.9 * SR), n)
            tp = t[p0:p1] - t[p0]
            hauteur = note(a[j % 3] + 12 + (12 if j in (3, 7) else 0))
            sortie[p0:p1] += 0.07 * np.sin(2 * np.pi * hauteur * tp) * np.exp(-tp / 0.25)
    # filtre passe-bas doux (moyenne glissante) pour adoucir les attaques
    sortie = np.convolve(sortie, np.ones(12) / 12, mode="same")
    sortie /= np.abs(sortie).max() + 1e-9
    # niveau : plus fort sans voix, atténué (ducking) pendant la voix, fondus début / fin
    presence = moyenne_glissante((np.abs(voix) > 0.02).astype(np.float32), SR // 2) > 0.05
    niveau = np.where(presence, 0.07, 0.20).astype(np.float32)
    niveau = moyenne_glissante(niveau, SR // 3)
    fondu = np.minimum(1, np.minimum(t / 1.5, (duree - t) / 3.0)).clip(0, 1)
    return (sortie * niveau * fondu).astype(np.float32)


def moyenne_glissante(x: np.ndarray, n: int) -> np.ndarray:
    """Moyenne glissante centrée (somme cumulée : linéaire, contrairement à np.convolve)."""
    c = np.cumsum(np.concatenate([np.zeros(n // 2 + 1), x, np.zeros(n - n // 2)]))
    return ((c[n:n + len(x)] - c[:len(x)]) / n).astype(np.float32)


# --------------------------------------------------------------- dessin
def fond_sombre(t: float) -> Image.Image:
    """Dégradé vert nuit + grille de données discrète qui défile lentement."""
    y = np.linspace(0, 1, H)[:, None, None]
    x = np.linspace(0, 1, L)[None, :, None]
    c1, c2 = np.array(SOMBRE_1), np.array(SOMBRE_2)
    base = c1 * (1 - 0.6 * y - 0.4 * x) + c2 * (0.6 * y + 0.4 * x)
    halo = np.exp(-(((x - 0.85) * 1.8) ** 2 + ((y - 0.15) * 2.2) ** 2)) * np.array([60, 28, 0])
    img = Image.fromarray(np.clip(base + halo, 0, 255).astype(np.uint8)).convert("RGBA")
    calque = Image.new("RGBA", (L, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(calque)
    pas, dec = 80, int(t * 12) % 80
    for gx in range(-pas, L + pas, pas):
        d.line([gx + dec, 0, gx + dec, H], fill=(255, 255, 255, 10), width=1)
    for gy in range(0, H, pas):
        d.line([0, gy, L, gy], fill=(255, 255, 255, 10), width=1)
    for gx in range(-pas, L + pas, pas):
        for gy in range(0, H, pas):
            d.ellipse([gx + dec - 2, gy - 2, gx + dec + 2, gy + 2], fill=(245, 160, 74, 28))
    img.alpha_composite(calque)
    return img


_FONDS: dict[int, Image.Image] = {}


def fond(t: float) -> Image.Image:
    cle = int(t * 12) % 80
    if cle not in _FONDS:
        _FONDS[cle] = fond_sombre(t)
    return _FONDS[cle].copy()


def carte_bloc(img, boite, fond_rgb, bord_rgb, alpha, rayon=22, epaisseur=3):
    calque = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(calque).rounded_rectangle(boite, radius=rayon,
                                             fill=(*fond_rgb, int(255 * alpha)),
                                             outline=(*bord_rgb, int(255 * alpha)),
                                             width=epaisseur)
    img.alpha_composite(calque)


def lignes(contenu: str, taille: int, largeur: int, gras=False) -> list[str]:
    f = police(gras, taille)
    d = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    resultat, courante = [], ""
    for mot in contenu.split():
        essai = f"{courante} {mot}".strip()
        if d.textlength(essai, font=f) <= largeur:
            courante = essai
        else:
            resultat.append(courante)
            courante = mot
    return resultat + [courante]


def etiquette(img, surtitre: str, alpha: float, clair=False):
    """Repère de séquence en haut à gauche (les sous-titres occupent le bas)."""
    if alpha <= 0:
        return
    f = police(True, 26)
    w = ImageDraw.Draw(img).textlength(surtitre, font=f) + 48
    carte_bloc(img, (40, 36, 40 + w, 88), (16, 36, 27) if not clair else (255, 255, 255),
               (224, 112, 0), alpha * 0.95, rayon=12, epaisseur=2)
    texte(img, (64, 62), surtitre, 26, "#FFFFFF" if not clair else ORANGE, alpha=alpha,
          ancre="lm")


def sous_titre(img, contenu: str | None, alpha: float):
    if not contenu or alpha <= 0:
        return
    rangs = lignes(contenu, 38, 1760, gras=True)
    f = police(True, 38)
    d = ImageDraw.Draw(img)
    w = max(d.textlength(r, font=f) for r in rangs) + 64
    h = 52 * len(rangs) + 28
    y0 = H - 40 - h
    calque = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(calque).rounded_rectangle(
        [(L - w) / 2, y0, (L + w) / 2, y0 + h], radius=14, fill=(8, 20, 15, int(205 * alpha)))
    img.alpha_composite(calque)
    for i, r in enumerate(rangs):
        texte(img, (L // 2, y0 + 40 + i * 52), r, 38, "#FFFFFF", alpha=alpha, ancre="mm")


# --------------------------------------------------------------- séquences
def seq_profil(t, duree, reperes, **_):
    img = fond(t)
    a = progression(t, 0.2, 0.8)
    texte(img, (L // 2, 300), NOM, 104, "#FFFFFF", alpha=a, ancre="mm",
          decalage=int(30 * (1 - a)))
    c = progression(t, 0.9, 0.9)
    if c > 0:
        largeur = int(620 * c)
        d = ImageDraw.Draw(img)
        x0 = L // 2 - largeur // 2
        for i, col in enumerate((ORANGE, "#FFFFFF", VERT)):
            d.rectangle([x0 + i * largeur // 3, 378, x0 + (i + 1) * largeur // 3, 384], fill=col)
    b = progression(t, 1.3)
    texte(img, (L // 2, 455), DOMAINES, 50, CLAIR, alpha=b, ancre="mm", decalage=int(20 * (1 - b)))
    e = progression(t, 2.0)
    texte(img, (L // 2, 550), FORMATION, 40, "#DDE6E1", gras=False, alpha=e, ancre="mm",
          decalage=int(20 * (1 - e)))
    g = progression(t, 2.8)
    if g > 0:
        f = police(True, 36)
        w = ImageDraw.Draw(img).textlength(RECHERCHE + ".", font=f) + 80
        carte_bloc(img, ((L - w) / 2, 625, (L + w) / 2, 705), (40, 30, 15), (245, 160, 74), g,
                   rayon=40, epaisseur=3)
        texte(img, (L // 2, 665), RECHERCHE + ".", 36, CLAIR, alpha=g, ancre="mm")
    k = progression(t, 3.6)
    texte(img, (L // 2, 800), "Projet : Ligue 1 Côte d'Ivoire — collecte, analyse et prédiction "
          "des matchs", 32, "#AFC0B7", gras=False, alpha=k, ancre="mm")
    return img


def seq_contexte(t, duree, reperes, cartes, ordre, f, **_):
    img = Image.new("RGBA", (L, H), "#FFFFFF")
    bandeau_drapeau(img, 0, 8)
    debut, fin = reperes[2], duree - 1.0
    k = int(np.clip((t - debut) / max(fin - debut, 0.1), 0, 1) * (len(cartes) - 1) + 0.5)
    img.paste(cartes[k].resize((900, 833), Image.LANCZOS), (70, 60))
    etiquette(img, "CONTEXTE", progression(t, 0.1), clair=True)
    a = progression(t, 0.3)
    texte(img, (1040, 170), "Un championnat formateur…", 58, ENCRE, alpha=a)
    texte(img, (1040, 245), "La Ligue 1 ivoirienne alimente l'Afrique", 36, ENCRE_2, gras=False,
          alpha=a)
    texte(img, (1040, 292), "et l'Europe en joueurs.", 36, ENCRE_2, gras=False, alpha=a)
    b = progression(t, reperes[1])
    texte(img, (1040, 395), "…aux données dispersées", 58, ORANGE, alpha=b)
    texte(img, (1040, 470), "Résultats éparpillés entre plusieurs sites,", 36, ENCRE_2,
          gras=False, alpha=b)
    texte(img, (1040, 517), "presque jamais analysés.", 36, ENCRE_2, gras=False, alpha=b)
    c = progression(t, reperes[2])
    vues = ordre.head(k)
    texte(img, (1040, 610), f"{int(vues['n_clubs'].sum())}", 130, ORANGE, alpha=c)
    texte(img, (1040, 765), f"clubs sur {f['clubs']}  ·  {len(vues)} villes sur {f['villes']}"
          f"  ·  {f['saisons']} saisons", 34, ENCRE, alpha=c)
    texte(img, (1040, 830), "Coordonnées : articles Wikipédia des villes", 24, ENCRE_2,
          gras=False, alpha=c)
    return img


OBJECTIFS = [
    ("01", "Constituer une base fiable", "collecte de 4 sources, scores recoupés"),
    ("02", "Analyser les performances", "classements, forme, avantage du terrain"),
    ("03", "Étudier le réseau des joueurs", "mouvements entre clubs, centralité"),
    ("04", "Comparer six modèles", "prédire victoire, nul ou défaite"),
]


def seq_objectifs(t, duree, reperes, **_):
    img = fond(t)
    etiquette(img, "PROBLÉMATIQUE ET OBJECTIFS", progression(t, 0.1))
    bascule = reperes[2] - 0.3
    if t < bascule:
        a = progression(t, 0.2)
        texte(img, (L // 2, 220), "LA QUESTION DE DÉPART", 30, CLAIR, alpha=a, ancre="mm")
        q1 = lignes("Que révèlent les données publiques sur la Ligue 1 ivoirienne ?", 68, 1500,
                    gras=True)
        for i, r in enumerate(q1):
            texte(img, (L // 2, 340 + i * 90), r, 68, "#FFFFFF", alpha=a, ancre="mm",
                  decalage=int(20 * (1 - a)))
        b = progression(t, reperes[1])
        y = 340 + len(q1) * 90 + 60
        for i, r in enumerate(lignes("Peut-on prédire un match mieux qu'une règle naïve ?", 60,
                                     1500, gras=True)):
            texte(img, (L // 2, y + i * 80), r, 60, CLAIR, alpha=b, ancre="mm",
                  decalage=int(20 * (1 - b)))
        return img
    t2 = t - bascule
    a = progression(t2, 0.0, 0.5)
    texte(img, (150, 150), "OBJECTIF GÉNÉRAL", 28, CLAIR, alpha=a)
    for i, r in enumerate(lignes("Décrire objectivement le championnat ivoirien et mesurer "
                                 "jusqu'où ses résultats sont prévisibles.", 46, 1620, True)):
        texte(img, (150, 200 + i * 60), r, 46, "#FFFFFF", alpha=a)
    texte(img, (150, 360), "OBJECTIFS SPÉCIFIQUES", 28, CLAIR, alpha=a)
    largeur, ecart = 390, 30
    for i, (num, titre, detail) in enumerate(OBJECTIFS):
        b = progression(t2, 0.4 + i * 0.55 if i < 2 else (reperes[3] - bascule) + (i - 2) * 0.5,
                        0.5)
        if b <= 0:
            continue
        x = 150 + i * (largeur + ecart)
        dy = int(25 * (1 - b))
        carte_bloc(img, (x, 420 + dy, x + largeur, 800 + dy), (28, 52, 41), (224, 112, 0), b)
        texte(img, (x + 32, 455 + dy), num, 44, ORANGE, alpha=b)
        for k, r in enumerate(lignes(titre, 38, largeur - 64, True)):
            texte(img, (x + 32, 535 + dy + k * 48), r, 38, "#FFFFFF", alpha=b)
        for k, r in enumerate(lignes(detail, 28, largeur - 64)):
            texte(img, (x + 32, 670 + dy + k * 38), r, 28, "#BFD0C7", gras=False, alpha=b)
    return img


METHODES = [
    ("Statistique descriptive", "SQL : fonctions de fenêtre, CTE"),
    ("Analyse de réseau", "PageRank, intermédiarité, Louvain"),
    ("Modèle Elo", "force des équipes mise à jour"),
    ("Régression logistique", "forêt aléatoire, gradient boosting"),
    ("Réseau de neurones", "MLP PyTorch, arrêt anticipé"),
    ("Validation temporelle", "glissante + bootstrap (IC 95 %)"),
]


def seq_methodes(t, duree, reperes, etapes, **_):
    img = Image.new("RGBA", (L, H), "#FFFFFF")
    bandeau_drapeau(img, 0, 8)
    etiquette(img, "DONNÉES ET MÉTHODES", progression(t, 0.1), clair=True)
    a = progression(t, 0.1)
    texte(img, (120, 135), "De la page web à la base analytique", 54, ENCRE, alpha=a)
    largeur, ecart, y0, y1 = 318, 52, 230, 545
    x = (L - (5 * largeur + 4 * ecart)) // 2
    rythme = max((reperes[2] - 0.6) / 5, 0.5)
    for i, (nom, chiffre, details) in enumerate(etapes):
        b = progression(t, 0.4 + i * rythme, 0.5)
        if b > 0:
            base = nom in ("MongoDB", "PostgreSQL")
            dy = int(20 * (1 - b))
            carte_bloc(img, (x, y0 + dy, x + largeur, y1 + dy),
                       (230, 242, 236) if base else (255, 243, 230),
                       (0, 107, 69) if base else (224, 112, 0), b, epaisseur=4)
            cx = x + largeur // 2
            texte(img, (cx, y0 + 50 + dy), nom, 34, ENCRE, alpha=b, ancre="mm")
            texte(img, (cx, y0 + 135 + dy), chiffre, 40, ORANGE, alpha=b, ancre="mm")
            for k, ligne in enumerate(details):
                texte(img, (cx, y0 + 215 + k * 42 + dy), ligne, 26, ENCRE_2, gras=False,
                      alpha=b, ancre="mm")
            if i < len(etapes) - 1 and b >= 1:
                d = ImageDraw.Draw(img)
                xa, ya = x + largeur + 8, (y0 + y1) // 2
                d.line([xa, ya, xa + ecart - 26, ya], fill=ENCRE_2, width=5)
                d.polygon([(xa + ecart - 26, ya - 11), (xa + ecart - 12, ya),
                           (xa + ecart - 26, ya + 11)], fill=ENCRE_2)
        x += largeur + ecart
    c = progression(t, reperes[2] - 0.2)
    texte(img, (120, 580), "Méthodes mobilisées", 40, ENCRE, alpha=c)
    lw, lh = 540, 104
    for i, (titre, detail) in enumerate(METHODES):
        b = progression(t, reperes[2] + i * 0.35, 0.45)
        if b <= 0:
            continue
        x = 120 + (i % 3) * (lw + 30)
        y = 640 + (i // 3) * (lh + 14)
        carte_bloc(img, (x, y, x + lw, y + lh), (247, 248, 247), (200, 205, 202), b, rayon=16,
                   epaisseur=2)
        ImageDraw.Draw(img).rectangle([x, y + 16, x + 6, y + lh - 16], fill=ORANGE)
        texte(img, (x + 30, y + 14), titre, 32, ENCRE, alpha=b)
        texte(img, (x + 30, y + 60), detail, 26, ENCRE_2, gras=False, alpha=b)
    return img


def seq_constats(t, duree, reperes, capture, f, **_):
    """Observations descriptives (tuiles), puis la page Championnat du site."""
    bascule = reperes[1] + 0.2
    if t < bascule + 1.2:
        img = fond(t)
        etiquette(img, "RÉSULTATS — OBSERVATIONS", progression(t, 0.1))
        texte(img, (L // 2, 175), "Ce que montrent les données (statistique descriptive)", 44,
              "#FFFFFF", alpha=progression(t, 0.1), ancre="mm")
        tuiles = [(pct(f["nuls"], 0), "des matchs se terminent", "par un nul", 0.3),
                  (f"{f['buts']:.2f}".replace(".", ","), "buts par match", "en moyenne", 1.5),
                  (f"{f['titres_asec']} / {f['saisons']}", "titres pour", "l'ASEC Mimosas",
                   reperes[1]),
                  (pct(f["part_asec"], 0), f"des {f['departs']} départs suivis",
                   "partent de l'ASEC", reperes[1] + 0.5)]
        w, ecart = 380, 30
        x0 = (L - 4 * w - 3 * ecart) // 2
        for i, (val, l1, l2, debut) in enumerate(tuiles):
            b = progression(t, debut, 0.5)
            if b <= 0:
                continue
            x, dy = x0 + i * (w + ecart), int(25 * (1 - b))
            carte_bloc(img, (x, 290 + dy, x + w, 680 + dy), (28, 52, 41), (224, 112, 0), b)
            texte(img, (x + w // 2, 420 + dy), val, 92, CLAIR, alpha=b, ancre="mm")
            texte(img, (x + w // 2, 555 + dy), l1, 32, "#FFFFFF", gras=False, alpha=b, ancre="mm")
            texte(img, (x + w // 2, 600 + dy), l2, 32, "#FFFFFF", gras=False, alpha=b, ancre="mm")
        n_matchs = f"{f['matchs']:,}".replace(",", " ")
        texte(img, (L // 2, 780), f"Sur {n_matchs} matchs joués de 2016-17 à 2025-26 · "
              "constats observés, pas des liens de cause à effet", 30,
              "#AFC0B7", gras=False, alpha=progression(t, 2.0), ancre="mm")
        if t < bascule:
            return img
        # fondu vers la capture du site
        capt = plan(capture, 170, 0.0)
        return Image.blend(img, capt, progression(t, bascule, 1.2))
    t2, d2 = t - bascule, duree - bascule
    img = plan(capture, 170, t2 / d2, zoom=0.04)
    etiquette(img, "SITE — CLASSEMENT RECALCULÉ", progression(t2, 0.0))
    return img


def seq_modeles(t, duree, reperes, f, **_):
    img = Image.new("RGBA", (L, H), "#FFFFFF")
    bandeau_drapeau(img, 0, 8)
    etiquette(img, "RÉSULTATS — MODÉLISATION", progression(t, 0.1), clair=True)
    glis = f["glis"]
    a = progression(t, 0.1)
    texte(img, (120, 135), "Part de bons pronostics", 52, ENCRE, alpha=a)
    texte(img, (120, 205), f"validation temporelle glissante · {f['n_glissante']:,} matchs "
          "prédits · 2021-22 → 2025-26".replace(",", " "), 30, ENCRE_2, gras=False, alpha=a)
    ordre = sorted(glis, key=lambda k: -glis[k]["accuracy"])
    x0, xmax, y0, pas = 520, 1080, 270, 72  # échelle 0 → 50 % sur xmax pixels
    d = ImageDraw.Draw(img)
    for g in range(0, 51, 10):
        xg = x0 + xmax * g / 50
        d.line([xg, y0 - 10, xg, y0 + pas * len(ordre) - 20], fill="#E6E8EB", width=2)
        texte(img, (xg, y0 + pas * len(ordre) - 5), f"{g} %", 24, ENCRE_2, gras=False, alpha=a,
              ancre="ma")
    for i, nom in enumerate(ordre):
        b = progression(t, reperes[1] - 0.6 + i * 0.15, 0.9)
        y = y0 + i * pas
        acc = glis[nom]["accuracy"]
        couleur = ORANGE if nom == f["retenu"] else ("#9A9A94" if nom == "naif" else "#7FA898")
        texte(img, (x0 - 24, y + 28), NOMS_MODELES[nom], 32, ENCRE, gras=nom == f["retenu"],
              alpha=a, ancre="rm")
        if b > 0:
            d.rounded_rectangle([x0, y + 8, x0 + max(int(xmax * acc / 0.5 * b), 12), y + 50],
                                radius=8, fill=couleur)
            texte(img, (x0 + xmax * acc / 0.5 * b + 16, y + 29), pct(acc), 30, ENCRE, alpha=b,
                  ancre="lm")
    xn = x0 + xmax * glis["naif"]["accuracy"] / 0.5
    c = progression(t, reperes[1] + 1.0)
    if c > 0:
        for yy in range(y0 - 10, y0 + pas * len(ordre) - 20, 18):
            d.line([xn, yy, xn, yy + 9], fill="#57606A", width=3)
    # lecture des résultats : établi / non établi
    e = progression(t, reperes[2] - 0.3)
    if e > 0:
        bx, by, bw = 120, 752, 1680
        carte_bloc(img, (bx, by, bx + bw, by + 116), (240, 247, 243), (0, 107, 69), e, rayon=16)
        texte(img, (bx + 30, by + 16), "Établi : les 5 modèles battent la référence naïve "
              "(bootstrap apparié sur la log-loss, IC 95 % de l'écart entièrement sous 0)",
              28, ENCRE, alpha=e)
        texte(img, (bx + 30, by + 64), "Non établi : un écart entre modèles · saison test "
              f"2025-26 seule : {pct(f['test_retenu'])} contre {pct(f['test_naif'])}, "
              "écart non significatif", 28, ENCRE_2, gras=False, alpha=e)
    return img


def seq_prediction(t, duree, reperes, capture, match, **_):
    img = plan(capture, 0, t / duree, zoom=0.02)
    etiquette(img, "SITE — PRÉDICTION", progression(t, 0.1))
    a = progression(t, 0.6)
    if a <= 0:
        return img
    x0, y0, x1, y1 = 1050, 230, 1860, 860
    dy = int(30 * (1 - a))
    carte_bloc(img, (x0, y0 + dy, x1, y1 + dy), (255, 255, 255), (224, 112, 0), a, epaisseur=4)
    texte(img, (x0 + 45, y0 + 40 + dy), "MATCH À VENIR · SAISON 2026-2027", 24, ORANGE, alpha=a)
    texte(img, (x0 + 45, y0 + 80 + dy), f"{match['dom']} – {match['ext']}", 42, ENCRE, alpha=a)
    for i, (lib, p, couleur) in enumerate([("Victoire domicile", match["p_dom"], ORANGE),
                                           ("Match nul", match["p_nul"], "#9A9A94"),
                                           ("Victoire extérieur", match["p_ext"], VERT)]):
        b = progression(t, 1.2 + i * 0.4, 0.8)
        y = y0 + 190 + i * 125 + dy
        texte(img, (x0 + 45, y), f"{lib} : {p * 100:.0f} %", 36, ENCRE, alpha=a)
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([x0 + 45, y + 55, x1 - 45, y + 79], radius=12, fill="#EEF0EE")
        if b > 0:
            d.rounded_rectangle([x0 + 45, y + 55, x0 + 45 + int((x1 - x0 - 90) * p * b), y + 79],
                                radius=12, fill=couleur)
    texte(img, (x0 + 45, y1 - 50 + dy), "Probabilités, pas un pronostic de pari.", 26, ENCRE_2,
          gras=False, alpha=a)
    return img


COMPETENCES = ["Web scraping", "MongoDB", "PostgreSQL · SQL", "ETL", "Statistique",
               "Analyse de réseau", "Machine Learning", "PyTorch", "Streamlit"]


def seq_conclusion(t, duree, reperes, **_):
    img = fond(t)
    etiquette(img, "CONCLUSION", progression(t, 0.1))
    etapes = ["Collecte", "Bases de données", "Analyse", "Modélisation", "Application"]
    f = police(True, 44)
    d = ImageDraw.Draw(img)
    morceaux = []
    for i, e in enumerate(etapes):
        morceaux.append((e, i))
        if i < len(etapes) - 1:
            morceaux.append(("  →  ", i + 0.5))
    x = (L - sum(d.textlength(m, font=f) for m, _ in morceaux)) / 2
    for contenu, rang in morceaux:
        a = progression(t, 0.2 + rang * 0.35, 0.4)
        texte(img, (x, 150), contenu, 44, CLAIR if "→" in contenu else "#FFFFFF", alpha=a)
        x += d.textlength(contenu, font=f)
    fc = police(True, 28)
    for rangee, (debut_r, fin_r) in enumerate(((0, 5), (5, len(COMPETENCES)))):
        groupe = COMPETENCES[debut_r:fin_r]
        largeurs = [d.textlength(c, font=fc) + 44 for c in groupe]
        x = (L - sum(largeurs) - 14 * (len(largeurs) - 1)) / 2
        y = 225 + rangee * 66
        for i, (c, w) in enumerate(zip(groupe, largeurs, strict=True)):
            b = progression(t, 1.6 + (debut_r + i) * 0.12, 0.4)
            if b > 0:
                carte_bloc(img, (x, y, x + w, y + 54), (28, 52, 41), (95, 125, 110), b, rayon=27,
                           epaisseur=2)
                texte(img, (x + w / 2, y + 27), c, 28, "#E4EAE6", alpha=b, ancre="mm")
            x += w + 14
    g = progression(t, reperes[1] - 0.3)
    texte(img, (L // 2, 455), NOM, 92, "#FFFFFF", alpha=g, ancre="mm", decalage=int(20 * (1 - g)))
    texte(img, (L // 2, 545), DOMAINES_FIN, 44, CLAIR, alpha=g, ancre="mm")
    h = progression(t, reperes[1] + 0.6)
    if h > 0:
        fr = police(True, 40)
        msg = "Recherche de stage et d'alternance"
        w = d.textlength(msg, font=fr) + 90
        carte_bloc(img, ((L - w) / 2, 605, (L + w) / 2, 689), (224, 112, 0), (224, 112, 0), h,
                   rayon=42)
        texte(img, (L // 2, 647), msg, 40, "#FFFFFF", alpha=h, ancre="mm")
    k = progression(t, reperes[1] + 1.4)
    for i, (nom, url) in enumerate(LIENS.items()):
        texte(img, (L // 2, 755 + i * 52), f"{nom} : {url.removeprefix('https://')}", 34,
              "#DDE6E1", gras=False, alpha=k, ancre="mm")
    bandeau_drapeau(img, H - 10, 10)
    return img


# ---------------------------------------------------------------- montage
def captures(reutiliser: bool) -> dict[str, Image.Image]:
    v.CAPTURES.mkdir(parents=True, exist_ok=True)
    pages = {"championnat": "championnat", "prediction": "prediction"}
    for nom, page in pages.items():
        if not (reutiliser and (v.CAPTURES / f"{nom}.png").exists()):
            capturer(page, v.CAPTURES / f"{nom}.png")
    return {nom: Image.open(v.CAPTURES / f"{nom}.png").convert("RGB") for nom in pages}


def srt_temps(s: float) -> str:
    ms = round(s * 1000)
    return f"{ms // 3_600_000:02d}:{ms // 60_000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def main(reutiliser: bool = False, apercu: bool = False, sans_voix: bool = False,
         sans_musique: bool = False) -> None:
    import imageio.v2 as imageio
    import imageio_ffmpeg

    f = faits()
    verifier_narration(f)
    clubs = pd.read_parquet(DATA / "clubs.parquet")
    resultats = pd.read_parquet(DATA / "resultats_club.parquet")
    prochains = pd.read_parquet(DATA / "modele" / "predictions_a_venir.parquet")
    match = prochains[(prochains["dom"] == "ASEC Mimosas") & (prochains["ext"] == "AFAD Djékanou")]
    match = (match if len(match) else prochains).iloc[0]
    ecrans = captures(reutiliser)
    cartes, ordre = images_carte(villes_carte(clubs, resultats), reutiliser=True)

    sequences = [
        ("01_profil", seq_profil, {}),
        ("02_contexte", seq_contexte, {"cartes": cartes, "ordre": ordre, "f": f}),
        ("03_objectifs", seq_objectifs, {}),
        ("04_methodes", seq_methodes, {"etapes": chiffres_pipeline()}),
        ("05a_constats", seq_constats, {"capture": ecrans["championnat"], "f": f}),
        ("05b_modeles", seq_modeles, {"f": f}),
        ("05c_prediction", seq_prediction, {"capture": ecrans["prediction"], "match": match}),
        ("06_conclusion", seq_conclusion, {}),
    ]

    # 1. voix : une phrase = un sous-titre ; la durée de chaque séquence suit la narration
    plan_temps, debut = [], 0.0
    for nom, fonction, args in sequences:
        t, reperes, phrases = DEBUT_VOIX, [], []
        for affiche, dit in NARRATION[nom]:
            son = synthese(dit or affiche, reutiliser)
            reperes.append(t)
            phrases.append((t, t + len(son) / SR, affiche, son))
            t += len(son) / SR + PAUSE
        duree = max(t - PAUSE + FIN_MIN, DUREE_MIN.get(nom, 0))
        plan_temps.append((nom, fonction, args, debut, duree, reperes, phrases))
        debut += duree
    total = debut

    DIAPOS.mkdir(parents=True, exist_ok=True)
    if apercu:
        for nom, fonction, args, _, duree, reperes, phrases in plan_temps:
            for j, instant in enumerate([duree * 0.3, duree * 0.92]):
                img = fonction(instant, duree, reperes, **args)
                actif = next((p for p in phrases if p[0] <= instant <= p[1] + PAUSE), None)
                sous_titre(img, actif[2] if actif else None, 1.0)
                img.convert("RGB").save(DIAPOS / f"{nom}_{j}.png")
        print(f"Aperçu : {len(plan_temps)} séquences, {total:.1f} s -> {DIAPOS}")
        return

    # 2. piste audio : voix + musique, et sous-titres .srt
    voix = np.zeros(int(total * SR) + SR, dtype=np.float32)
    srt = []
    for nom, _, _, debut, _, _, phrases in plan_temps:
        for t0, t1, affiche, son in phrases:
            i0 = int((debut + t0) * SR)
            voix[i0:i0 + len(son)] += son * (0.0 if sans_voix else 0.92 / (np.abs(son).max() + 1e-9))
            srt.append((debut + t0, debut + t1 + 0.15, affiche))
    melange = voix if sans_musique else voix + musique(
        len(voix) / SR, voix if not sans_voix else np.zeros_like(voix))
    suffixe = ("_sans_voix" if sans_voix else "") + ("_sans_musique" if sans_musique else "")
    AUDIO.mkdir(parents=True, exist_ok=True)
    piste = AUDIO / f"bande_son{suffixe}.wav"
    ecrire_wav(piste, np.stack([melange, melange], axis=1))
    sortie = FICHIER.with_name(f"{FICHIER.stem}{suffixe}.mp4")
    sortie.with_suffix(".srt").write_text(
        "\n".join(f"{i}\n{srt_temps(a)} --> {srt_temps(b)}\n{txt}\n"
                  for i, (a, b, txt) in enumerate(srt, start=1)), encoding="utf-8")

    # 3. images : séquences + sous-titres incrustés, fondu enchaîné de 0,4 s
    muet = AUDIO / "video_muette.mp4"
    ecrivain = imageio.get_writer(muet, fps=FPS, codec="libx264", quality=8,
                                  pixelformat="yuv420p", macro_block_size=8)
    precedente, fondu = None, int(0.4 * FPS)
    for nom, fonction, args, debut, duree, reperes, phrases in plan_temps:
        n = round((debut + duree) * FPS) - round(debut * FPS)
        for k in range(n):
            instant = k / FPS
            img = fonction(instant, duree, reperes, **args)
            actif = next((p for p in phrases if p[0] - 0.05 <= instant <= p[1] + 0.15), None)
            if actif:
                sous_titre(img, actif[2], min(1.0, (instant - actif[0] + 0.05) / 0.15,
                                               (actif[1] + 0.15 - instant) / 0.15))
            cadre = np.asarray(img.convert("RGB"))
            if precedente is not None and k < fondu:
                a = k / fondu
                cadre = (cadre * a + precedente * (1 - a)).astype(np.uint8)
            ecrivain.append_data(cadre)
            if k == int(n * 0.9):
                Image.fromarray(cadre).save(DIAPOS / f"{nom}.png")
        precedente = cadre
    ecrivain.close()

    # 4. assemblage image + son (AAC), lecture progressive pour LinkedIn
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(muet),
                    "-i", str(piste), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(sortie)],
                   check=True)
    muet.unlink()
    print(f"{len(plan_temps)} séquences, {total:.1f} s -> {sortie} (+ {sortie.with_suffix('.srt').name})")


def controler(chemin: Path = FICHIER) -> str:
    """Résumé ffmpeg du fichier produit (durée, flux vidéo et audio)."""
    import imageio_ffmpeg

    r = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-i", str(chemin)],
                       check=False, capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return "\n".join(ligne.strip() for ligne in r.stderr.splitlines()
                     if re.search(r"Duration|Stream", ligne))


if __name__ == "__main__":
    if "--controle" in sys.argv:
        print(controler())
    else:
        main(reutiliser="--reutiliser" in sys.argv, apercu="--apercu" in sys.argv,
             sans_voix="--sans-voix" in sys.argv, sans_musique="--sans-musique" in sys.argv)

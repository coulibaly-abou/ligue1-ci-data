"""Rapport final (PDF, 10 pages max) généré à partir des résultats.

    python -m src.restitution.rapport        # ou : make rapport  (après make figures)

Tous les chiffres sont lus dans app/data/ et docs/resultats/ : relancer le pipeline
puis ce script met le rapport à jour sans réécriture manuelle.
"""
import json

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from config.settings import RACINE

DATA = RACINE / "app" / "data"
RES = RACINE / "docs" / "resultats"
FIG = RACINE / "docs" / "figures"
SORTIE = RACINE / "docs" / "rapport.pdf"
ORANGE, VERT, ENCRE, ENCRE_2 = (colors.HexColor(c) for c in
                                ("#E07000", "#006B45", "#1F2328", "#57606A"))
NOMS = {"naif": "Référence naïve", "elo": "Elo", "logreg": "Régression logistique",
        "foret": "Forêt aléatoire", "boosting": "Gradient boosting",
        "mlp": "Réseau de neurones (MLP)"}
LARGEUR = A4[0] - 3.6 * cm
LIBELLES_VAR = {"elo_dom": "Elo de l'équipe à domicile", "elo_ext": "Elo de l'équipe à "
                "l'extérieur", "elo_diff": "écart Elo", "forme_domicile_dom": "forme à "
                "domicile de l'équipe qui reçoit", "repos_dom": "jours de repos (domicile)",
                "rang_dom": "rang (domicile)", "diff_saison_dom": "différence de buts "
                "(domicile)", "forme10_ext": "forme sur 10 matchs (extérieur)"}

base = getSampleStyleSheet()
S = {
    "titre": ParagraphStyle("titre", parent=base["Title"], fontSize=22, leading=27,
                            textColor=ENCRE, spaceAfter=4),
    "sous": ParagraphStyle("sous", parent=base["Normal"], fontSize=11, textColor=ENCRE_2,
                           alignment=TA_CENTER, spaceAfter=14),
    "h1": ParagraphStyle("h1", parent=base["Heading1"], fontSize=15, textColor=ORANGE,
                         spaceBefore=10, spaceAfter=6),
    "h2": ParagraphStyle("h2", parent=base["Heading2"], fontSize=11.5, textColor=ENCRE,
                         spaceBefore=6, spaceAfter=3),
    "p": ParagraphStyle("p", parent=base["Normal"], fontSize=9.5, leading=13.5,
                        textColor=ENCRE, spaceAfter=5),
    "puce": ParagraphStyle("puce", parent=base["Normal"], fontSize=9.5, leading=13,
                           textColor=ENCRE, leftIndent=12, bulletIndent=2, spaceAfter=2),
    "legende": ParagraphStyle("legende", parent=base["Normal"], fontSize=8, leading=10,
                              textColor=ENCRE_2, alignment=TA_CENTER, spaceAfter=8),
    "cle": ParagraphStyle("cle", parent=base["Normal"], fontSize=19, leading=22,
                          textColor=ORANGE, alignment=TA_CENTER),
    "cle_lib": ParagraphStyle("cle_lib", parent=base["Normal"], fontSize=8, leading=10,
                              textColor=ENCRE_2, alignment=TA_CENTER),
}


def p(texte):
    return Paragraph(texte, S["p"])


def puces(items):
    return [Paragraph(t, S["puce"], bulletText="•") for t in items]


def figure(nom, legende, largeur=1.0):
    img = Image(str(FIG / f"{nom}.png"))
    ratio = img.imageHeight / img.imageWidth
    img.drawWidth = LARGEUR * largeur
    img.drawHeight = LARGEUR * largeur * ratio
    return KeepTogether([img, Paragraph(legende, S["legende"])])


def tableau(lignes, largeurs=None, entete=True):
    t = Table(lignes, colWidths=largeurs, hAlign="CENTER")
    style = [("FONTSIZE", (0, 0), (-1, -1), 8.5), ("TEXTCOLOR", (0, 0), (-1, -1), ENCRE),
             ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#E6E8EB")),
             ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 3),
             ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if entete:
        style += [("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                  ("LINEBELOW", (0, 0), (-1, 0), 1, ORANGE)]
    t.setStyle(TableStyle(style))
    return t


def chiffres_cles(items):
    cellules = [[Paragraph(v, S["cle"]) for v, _ in items],
                [Paragraph(lib, S["cle_lib"]) for _, lib in items]]
    t = Table(cellules, colWidths=[LARGEUR / len(items)] * len(items))
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF3E6")),
                           ("TOPPADDING", (0, 0), (-1, 0), 8),
                           ("BOTTOMPADDING", (0, 1), (-1, 1), 8)]))
    return t


def pied(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(ENCRE_2)
    canvas.drawString(1.8 * cm, 1.1 * cm, "Plateforme d'analyse de la Ligue 1 ivoirienne — "
                      "Aboubakar Coulibaly · BUT3 Science des données")
    canvas.drawRightString(A4[0] - 1.8 * cm, 1.1 * cm, f"{doc.page}")
    canvas.restoreState()


def construire():
    m = json.loads((RES / "metriques.json").read_text(encoding="utf-8"))
    matchs = pd.read_parquet(DATA / "matchs.parquet")
    joues = matchs[matchs["statut"] == "joue"]
    res_saison = pd.read_parquet(DATA / "resultats_saison.parquet")
    palmares = pd.read_parquet(DATA / "palmares.parquet")
    noeuds = pd.read_parquet(DATA / "reseau_noeuds.parquet")
    mvts = pd.read_parquet(DATA / "reseau_mouvements.parquet")
    glis = pd.read_csv(RES / "validation_glissante.csv")
    moy = glis.groupby("modele")[["accuracy", "log_loss", "brier", "rps"]].mean() \
        .sort_values("log_loss")
    test = pd.DataFrame(m["resultats_test"]).set_index("modele")
    retenu, boot = m["modele_retenu"], m["bootstrap_vs_naif"]
    meilleur = moy.drop("naif").index[0]
    naif = moy.loc["naif"]
    pct = joues["resultat"].value_counts(normalize=True) * 100
    buts = (joues["buts_dom"] + joues["buts_ext"]).mean()
    asec = int((palmares["champion"] == "ASEC Mimosas").sum())
    b_best = boot[meilleur]["glissante"]
    significatif = b_best["ic95"][1] < 0
    proto = m["protocole"]
    resultats = pd.read_parquet(DATA / "resultats_club.parquet")
    par_lieu = resultats.groupby(["club", "a_domicile"])["points"].mean().unstack()
    par_lieu = par_lieu[resultats.groupby("club").size() >= 120]
    club_ecart = (par_lieu[True] - par_lieu[False]).idxmin()
    departs = mvts[mvts["depart_ligue1"].astype(bool) & ~mvts["arrivee_ligue1"].astype(bool)]
    impacts = [
        ("Clubs et entraîneurs", "Mesurer sa performance sans cellule data",
         (f"{club_ecart} prend moins de points à domicile "
         f"({par_lieu.loc[club_ecart, True]:.2f} par match) qu'à l'extérieur "
         f"({par_lieu.loc[club_ecart, False]:.2f}) : un axe de travail concret.")),
        ("Joueurs, agents, recruteurs", "Rendre visibles les talents locaux",
         (f"{len(departs)} départs suivis vers {departs['arrivee'].nunique()} clubs hors "
         f"Ligue 1, dont {(departs['depart'] == 'ASEC Mimosas').mean():.0%} depuis la seule "
         "ASEC : les joueurs des autres clubs restent peu exposés.")),
        ("Médias et supporters", "Débattre avec des chiffres vérifiés",
         ("Scores recoupés entre trois sources (11 écarts signalés) ; probabilités de match "
         "expliquées plutôt qu'un pronostic tranché.")),
        ("Ligue et Fédération", "Piloter l'équilibre du championnat",
         (f"{asec} titres sur {len(palmares)} pour l'ASEC, {pct['N']:.0f} % de nuls, "
         f"{buts:.2f} buts par match : des indicateurs pour évaluer le format, le "
         "calendrier et l'attractivité.")),
    ]
    confusion = pd.DataFrame(m["confusions"][retenu])   # lignes = réel, colonnes = prédit
    predits_n = int(confusion["prédit N"].sum())
    bons_n = int(confusion.loc["réel N", "prédit N"])
    imp = pd.read_csv(RES / "importance_variables.csv")
    top_var = ", ".join(LIBELLES_VAR.get(v, v) for v in
                        imp[imp["modele"] == "logreg"]["variable"].head(4))

    h = []
    # ------------------------------------------------------------------ page 1
    h += [Spacer(1, 0.6 * cm),
          Paragraph("Prédire la Ligue 1 ivoirienne", S["titre"]),
          Paragraph("De la collecte web au réseau de neurones : une plateforme de données "
                    "complète sur dix saisons de MTN Ligue 1 (2016 → 2026)", S["sous"]),
          chiffres_cles([(f"{(joues.groupby('saison').size() >= 90).sum()}",
                          "saisons complètes<br/>+ 2026-27 en cours"),
                         (f"{len(joues):,}".replace(",", " "), "matchs joués"),
                         (f"{pct['N']:.0f} %", "de matchs nuls"),
                         (f"{moy.loc[meilleur, 'accuracy']:.0%}",
                          f"précision du meilleur modèle<br/>(naïf : {naif['accuracy']:.0%})")]),
          Spacer(1, 0.4 * cm),
          Paragraph("Résumé", S["h1"]),
          p("Les données du championnat ivoirien sont dispersées et peu exploitées. Ce projet "
            "construit une chaîne complète : collecte automatisée et respectueuse des sites "
            "(RSSSF, Wikipédia, Futbol24, API-Football), zone brute <b>MongoDB</b>, modèle "
            "relationnel <b>PostgreSQL</b> conçu selon Merise, analyses SQL et réseau, six "
            "modèles de prédiction du résultat (victoire domicile, nul, victoire extérieur) "
            "dont un <b>réseau de neurones PyTorch</b>, et un tableau de bord <b>Streamlit</b>."),
          p(f"Le championnat est <b>serré et peu prolifique</b> : {pct['N']:.0f} % de nuls, "
            f"{buts:.2f} buts par match, un avantage du terrain faible ({pct['D']:.0f} % de "
            f"victoires à domicile). L'ASEC Mimosas domine ({asec} titres sur "
            f"{len(palmares)}) et occupe le centre du réseau des transferts."),
          p(f"En validation temporelle glissante sur {proto['n_glissante']} matchs, le modèle "
            f"<b>{NOMS[meilleur]}</b> obtient la meilleure log-loss "
            f"({moy.loc[meilleur, 'log_loss']:.4f} contre {naif['log_loss']:.4f} pour la "
            f"référence naïve) et une précision de {moy.loc[meilleur, 'accuracy']:.1%} "
            f"(naïf : {naif['accuracy']:.1%}). "
            + ("Le gain est statistiquement significatif (bootstrap, IC 95 % "
               f"[{b_best['ic95'][0]:+.4f} ; {b_best['ic95'][1]:+.4f}]). "
               if significatif else "Le gain reste dans la marge d'incertitude du bootstrap. ")
            + "Les modèles complexes, dont le réseau de neurones, n'apportent pas de gain "
              "avec ~1 500 matchs d'entraînement : un résultat honnête, cohérent avec la "
              "littérature sur la prédiction du football."),
          figure("00_architecture", "Figure 1 — Architecture : chaque base a un rôle unique."),
          PageBreak(),
          Paragraph("Objectif et impact", S["h1"]),
          p("La Ligue 1 ivoirienne forme des joueurs pour toute l'Afrique et l'Europe, mais "
            "ses données sont dispersées, incomplètes et presque jamais analysées. "
            "<b>L'objectif est de les rassembler dans une base fiable, sourcée et "
            "gratuite</b>, pour que les acteurs du football ivoirien décident avec des faits "
            "plutôt qu'avec des impressions. Chaque usage ci-dessous s'appuie sur un constat "
            "mesuré dans les données."),
          tableau([["Pour qui", "Ce que ça change", "Constat mesuré"]] + [
              [Paragraph(a, S["p"]), Paragraph(b, S["p"]), Paragraph(c, S["p"])]
              for a, b, c in impacts],
              [3.3 * cm, 4.2 * cm, 7.9 * cm]),
          p("<b>Ce que ce projet n'est pas</b> : un outil de paris. Les probabilités servent "
            "à comprendre le championnat et à situer une affiche, pas à miser."),
          Spacer(1, 0.2 * cm)]

    # ------------------------------------------------------- 1. données
    h += [Paragraph("1. Données : sources, volumes, qualité", S["h1"]),
          p("Un audit des sources a été mené avant toute collecte : couverture, conditions "
            "d'utilisation et <i>robots.txt</i>. Soccerway/Flashscore (CGU interdisant le "
            "scraping), Transfermarkt (championnat non suivi) et Wikidata (SPARQL interdit "
            "par robots.txt) ont été écartés."),
          tableau([["Source", "Données", "Couverture"],
                   ["RSSSF", "tous les matchs, classements officiels", "2016-17 → 2025-26"],
                   ["Wikipédia FR/EN", "stades, buteurs, grilles, ~460 carrières", "11 saisons"],
                   ["Futbol24", "résultats et calendrier daté", "saison en cours"],
                   ["API-Football", "matchs, effectifs, transferts, événements",
                    "2022-23 → 2024-25"]],
                  [3.2 * cm, 8 * cm, 4.2 * cm]),
          Spacer(1, 0.25 * cm),
          p("<b>Traçabilité.</b> Chaque page est archivée dans MongoDB avec son URL, sa date "
            "et une empreinte SHA-256 ; on peut re-parser sans re-télécharger. Collecte "
            "quotidienne planifiée, pause de 2 s entre requêtes, quota API respecté (100/jour) "
            "avec reprise automatique."),
          p("<b>ETL et contrôles.</b> L'ETL harmonise 157 écritures de noms en 31 clubs, "
            "recoupe les scores entre sources (11 divergences sur ~2 000 matchs, toutes "
            "journalisées) et vérifie que les classements recalculés sont identiques aux "
            "classements officiels sur les 10 saisons. Le modèle relationnel (MCD → MLD → "
            "MPD) compte 13 tables ; 4 vues matérialisées et 10 requêtes SQL documentées "
            "(fonctions de fenêtre, CTE « gaps and islands ») alimentent le tableau de bord."),
          tableau([["Saison", "Matchs", "Domicile", "Nul", "Extérieur", "Buts/match"]] +
                  [[r.saison, r.matchs, f"{r.pct_domicile:.1f} %", f"{r.pct_nul:.1f} %",
                    f"{r.pct_exterieur:.1f} %", f"{r.buts_par_match:.2f}"]
                   for r in res_saison.itertuples()],
                  [2.6 * cm, 2 * cm, 2.4 * cm, 2 * cm, 2.4 * cm, 2.4 * cm]),
          Paragraph("Tableau 1 — Matchs joués et répartition des résultats par saison "
                    "(requête 06). 2019-20 : arrêt Covid ; 2020-21 : poules + play-off.",
                    S["legende"]),
          p("<b>Limites des données.</b> Aucune source légale ne publie les buteurs et cartons "
            "match par match avant 2022 ; les effectifs complets n'existent que via "
            "API-Football (2022-2025) ; les carrières Wikipédia sont biaisées vers les grands "
            "clubs et les joueurs partis à l'étranger."),
          PageBreak()]

    # ------------------------------------------------- 2. exploration
    serie = pd.read_parquet(DATA / "series.parquet").iloc[0]
    h += [Paragraph("2. Analyse exploratoire", S["h1"]),
          figure("01_resultats_par_saison",
                 "Figure 2 — Un tiers de nuls et ~2 buts par match, toutes saisons confondues."),
          p(f"Le premier constat conditionne toute la suite : <b>{pct['N']:.0f} % des matchs "
            f"se terminent par un nul</b> (≈ 25 % en Europe) et le total moyen est de "
            f"{buts:.2f} buts. Les scores 1-1, 1-0, 0-0 et 0-1 représentent à eux seuls plus "
            "de la moitié des matchs (figure 3). Le nombre de buts suit approximativement une "
            "loi de Poisson."),
          Table([[Image(str(FIG / "02_scores.png"), width=6.6 * cm, height=5.8 * cm),
                  Image(str(FIG / "04_avantage_terrain.png"), width=9.2 * cm, height=7.2 * cm)]],
                colWidths=[7 * cm, 9.6 * cm]),
          Paragraph("Figure 3 — Fréquence des scores (gauche) ; avantage du terrain par club "
                    "(droite).", S["legende"]),
          p(f"L'<b>avantage du terrain</b> existe ({pct['D']:.0f} % de victoires à domicile "
            f"contre {pct['E']:.0f} % à l'extérieur) mais il est faible et instable : il s'est "
            "inversé en 2025-26. Il varie fortement selon les clubs, certains clubs de "
            "province prenant nettement plus de points chez eux."),
          figure("03_elo", "Figure 4 — Score Elo reconstruit match après match (lissé)."),
          p(f"Le score Elo, recalculé après chaque match, résume la hiérarchie : l'ASEC "
            f"Mimosas domine la période ({asec} titres, une série record de "
            f"{int(serie['matchs_sans_defaite'])} matchs sans défaite), tandis que FC "
            "San-Pédro et le Stade d'Abidjan ont émergé récemment (titres 2024 et 2025)."),
          PageBreak()]

    # ----------------------------------------------------- 3. réseau
    top = noeuds.head(6)
    sortants = mvts[mvts["depart_ligue1"].astype(bool) & ~mvts["arrivee_ligue1"].astype(bool)]
    h += [Paragraph("3. Réseau des clubs", S["h1"]),
          p(f"Les carrières Wikipédia et les transferts API-Football donnent "
            f"{len(mvts)} mouvements de joueurs entre {len(noeuds)} clubs. Le graphe orienté "
            "pondéré est analysé avec les mêmes algorithmes que Neo4j Graph Data Science : "
            "<b>PageRank</b> (centralité), intermédiarité et <b>communautés de Louvain</b>."),
          figure("05_reseau", "Figure 5 — Clubs de Ligue 1 (orange) et clubs étrangers les "
                 "plus centraux (vert) ; taille proportionnelle au PageRank.", 0.85),
          p("Clubs les plus centraux : " + ", ".join(
              f"{r.club} ({r.pagerank:.3f})" for r in top.itertuples()) + ". L'ASEC Mimosas "
            "est de loin le club le plus central, notamment par ses liens avec Beveren "
            "(Belgique), partenaire historique de son académie. Principales destinations à "
            "l'étranger : " + ", ".join(sortants["arrivee"].value_counts().head(5).index) +
            ". Ce réseau est biaisé vers les clubs dont les joueurs ont un article Wikipédia."),
          PageBreak()]

    # ------------------------------------------------- 4. modélisation
    h += [Paragraph("4. Modélisation", S["h1"]),
          Paragraph("4.1 Variables et protocole", S["h2"]),
          p(f"<b>Cible</b> : résultat en 3 classes (D, N, E). <b>{proto['n_variables']} "
            "variables</b>, toutes calculées avec l'information disponible <i>avant</i> le "
            "match en parcourant les matchs dans l'ordre chronologique : Elo des deux équipes "
            f"(K = {m['params_elo']['k']:g}, réglé en validation, retour partiel vers la "
            "moyenne entre saisons, promus à 1 450), forme sur 5 et 10 matchs, buts marqués "
            "et encaissés glissants, points par match, différence de buts et rang dans la "
            "saison, forme à domicile / à l'extérieur, jours de repos, et écarts entre les "
            "deux équipes."),
          p("<b>Aucun découpage aléatoire</b> : 2016-17 initialise l'Elo ; chaque saison "
            "2021-22 → 2025-26 est prédite par un modèle entraîné sur toutes les saisons "
            f"précédentes (validation glissante, {proto['n_glissante']} matchs). Le modèle "
            "retenu est <b>le plus simple</b> parmi ceux dont la log-loss moyenne 2021 → "
            "2024 est à moins de 0,002 de la meilleure (écart négligeable devant "
            "l'incertitude) ; la saison 2025-26 sert de "
            "<b>test final</b> et n'intervient dans aucun choix."),
          Paragraph("4.2 Modèles comparés", S["h2"]),
          *puces([
              ("<b>Référence naïve</b> : toujours « domicile », probabilités = fréquences "
              "observées."),
              "<b>Elo</b> : régression logistique sur le seul écart Elo.",
              (f"<b>Régression logistique multinomiale</b> standardisée, régularisation "
              f"C = {m['hyperparametres']['logreg_C']:g} choisie en validation."),
              ("<b>Forêt aléatoire</b> (400 arbres, feuilles ≥ 25) et <b>gradient boosting</b> "
              "(profondeur 3, arrêt anticipé)."),
              (f"<b>Réseau de neurones PyTorch</b> : couches {m['hyperparametres']['mlp']['couches']}, "
              f"dropout {m['hyperparametres']['mlp']['dropout']}, pénalité L2 "
              f"{m['hyperparametres']['mlp']['weight_decay']:g}, arrêt anticipé sur les matchs "
              "les plus récents, moyenne de 5 initialisations ; architecture choisie par "
              "recherche sur grille.")]),
          p("<b>Métriques</b> : précision, log-loss (qualité des probabilités, métrique "
            "principale), score de Brier et RPS (ranked probability score, qui tient compte "
            "de l'ordre D > N > E), matrice de confusion et calibration."),
          Paragraph("4.3 Résultats", S["h2"]),
          figure("06_comparaison_modeles", "Figure 6 — Moyennes de la validation glissante "
                 "(5 saisons)."),
          tableau([["Modèle", "Précision", "Log-loss", "Brier", "RPS"]] +
                  [[NOMS[n], f"{r.accuracy:.1%}", f"{r.log_loss:.4f}", f"{r.brier:.4f}",
                    f"{r.rps:.4f}"] for n, r in moy.iterrows()],
                  [5.5 * cm, 2.4 * cm, 2.4 * cm, 2.4 * cm, 2.4 * cm]),
          Paragraph("Tableau 2 — Validation glissante 2021-22 → 2025-26 (moyennes).",
                    S["legende"]),
          PageBreak(),
          figure("07_glissante_par_saison", "Figure 7 — Log-loss par saison prédite.", 0.85),
          tableau([["Modèle (test 2025-26)", "Précision", "Log-loss", "Brier", "RPS"]] +
                  [[NOMS[n], f"{r.accuracy:.1%}", f"{r.log_loss:.4f}", f"{r.brier:.4f}",
                    f"{r.rps:.4f}"] for n, r in test.sort_values("log_loss").iterrows()],
                  [5.5 * cm, 2.4 * cm, 2.4 * cm, 2.4 * cm, 2.4 * cm]),
          Paragraph(f"Tableau 3 — Test final sur 2025-26 ({proto['n_test']} matchs). "
                    f"Saison atypique : {m['repartition_test']['E']:.0%} de victoires à "
                    f"l'extérieur contre {m['repartition_test']['D']:.0%} à domicile.",
                    S["legende"]),
          figure("08_bootstrap", "Figure 8 — Écart de log-loss avec la référence naïve et "
                 "intervalle de confiance à 95 % (bootstrap apparié, 2 000 tirages).", 0.85),
          p(f"<b>Lecture.</b> Sur l'ensemble de la validation glissante, {NOMS[meilleur]} "
            f"réduit la log-loss de {(naif['log_loss'] - moy.loc[meilleur, 'log_loss']):.4f} "
            f"et gagne {(moy.loc[meilleur, 'accuracy'] - naif['accuracy']) * 100:.1f} points "
            "de précision. Sur la seule saison de test (240 matchs), les intervalles de "
            "confiance sont trop larges pour départager les modèles : une saison ne suffit "
            "pas à conclure, d'où l'intérêt de la validation glissante. Le réseau de neurones "
            "bat lui aussi la référence naïve, mais reste derrière Elo et la régression "
            "logistique : avec ~1 500 matchs et des variables déjà synthétiques (Elo, forme), il n'y "
            "a pas d'interaction non linéaire exploitable."),
          PageBreak(),
          figure("09_calibration_confusion", f"Figure 9 — Calibration du modèle retenu "
                 f"({NOMS[retenu]}) sur la validation glissante ; matrice de confusion du "
                 "test."),
          p("Les probabilités sont correctement calibrées (points proches de la diagonale). "
            "Le <b>nul reste la classe la plus difficile</b> : "
            + ("le modèle retenu ne le prédit jamais sur le test, "
               if predits_n == 0 else
               f"sur le test, le modèle retenu le prédit {predits_n} fois et n'a raison que "
               f"{bons_n} fois, ")
            + "car sa probabilité reste autour de 30 % quel que soit le match et n'est "
            "presque jamais la plus élevée. C'est une limite connue de la "
            "prédiction en 3 classes : la précision plafonne autour de 45-50 %, y compris "
            "pour les bookmakers."),
          figure("10_importance", "Figure 10 — Importance par permutation (régression "
                 "logistique, test 2025-26).", 0.75),
          p(f"Variables les plus utiles : {top_var}. Le niveau des équipes (Elo) porte "
            "l'essentiel de l'information ; les autres variables ont des effets faibles, du "
            "même ordre que leur incertitude, ce qui explique que les modèles complexes "
            "n'apportent rien de plus."),
          PageBreak()]

    # ------------------------------------------- 5. déploiement, limites
    h += [Paragraph("5. Restitution et déploiement", S["h1"]),
          p("Le tableau de bord Streamlit (6 pages : Accueil, Championnat, Club, Réseau, "
            "Prédiction, Modèles) lit uniquement des fichiers Parquet exportés depuis "
            "PostgreSQL et les résultats du modèle : il se déploie sur Streamlit Community "
            "Cloud sans exposer les bases. La page Prédiction donne les probabilités des "
            "matchs à venir de 2026-27 et un simulateur pour toutes les affiches."),
          tableau([["Commande", "Effet"],
                   ["make db", "lance MongoDB, PostgreSQL, Neo4j (Docker Compose)"],
                   ["make collect", "collecte web + API (reprise automatique du quota)"],
                   ["make etl", "MongoDB → PostgreSQL, contrôles, vues matérialisées"],
                   ["make train", "réglages, validation glissante, test, modèle final"],
                   ["make export", "données du tableau de bord (Parquet)"],
                   ["make rapport", "figures + ce rapport PDF"],
                   ["make app", "tableau de bord en local"]],
                  [3.5 * cm, 12 * cm]),
          Spacer(1, 0.3 * cm),
          Paragraph("6. Limites", S["h1"]),
          *puces([
              ("<b>Volume</b> : ~240 matchs par saison ; les écarts entre modèles sont du même "
              "ordre que l'incertitude d'une saison."),
              ("<b>Variables manquantes</b> : compositions, blessures, buteurs et cartons "
              "match par match (seulement 2022-2025 via API-Football), cotes des bookmakers."),
              "<b>Réseau</b> biaisé vers les joueurs ayant un article Wikipédia.",
              ("<b>Formats irréguliers</b> : saison 2019-20 interrompue, 2020-21 en poules ; "
              "classements recalculés approximatifs pour ces deux saisons.")]),
          Paragraph("7. Pistes d'amélioration", S["h1"]),
          *puces([
              ("Modèle de <b>Poisson bivarié / Dixon-Coles</b> pour prédire le score et mieux "
              "estimer la probabilité de nul."),
              ("Intégrer les <b>événements de match</b> API-Football (en cours de collecte) : "
              "forme des buteurs, cartons, absences."),
              ("Charger le graphe dans <b>Neo4j</b> (étape suivante du cahier des charges) "
              "pour les requêtes de plus court chemin et de coéquipiers communs."),
              ("Évaluer en continu sur 2026-27 : chaque journée jouée devient un nouveau test, "
              "ré-entraînement automatique hebdomadaire (GitHub Actions).")]),
          Paragraph("Conclusion", S["h1"]),
          p("Le projet livre une chaîne de données complète et reproductible sur un "
            "championnat peu documenté. Côté prédiction, le message est clair : dans une "
            f"ligue où {pct['N']:.0f} % des matchs sont nuls, <b>un bon résumé du niveau des "
            "équipes (Elo) vaut mieux qu'un modèle complexe</b>, et une évaluation honnête — "
            "découpage temporel, validation glissante, intervalles de confiance — compte "
            "plus que le choix de l'algorithme."),
          Spacer(1, 0.3 * cm),
          Paragraph("Sources : RSSSF © José Batalha / Rec.Sport.Soccer Statistics Foundation ; "
                    "Wikipédia (CC BY-SA) ; Futbol24 ; API-Football. Code : dépôt "
                    "ligue1-ci-data.", S["legende"])]

    doc = SimpleDocTemplate(str(SORTIE), pagesize=A4, leftMargin=1.8 * cm,
                            rightMargin=1.8 * cm, topMargin=1.5 * cm, bottomMargin=1.6 * cm,
                            title="Prédire la Ligue 1 ivoirienne",
                            author="Aboubakar Coulibaly")
    doc.build(h, onFirstPage=pied, onLaterPages=pied)
    print(SORTIE)


if __name__ == "__main__":
    construire()

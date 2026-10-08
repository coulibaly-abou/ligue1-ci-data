"""Figures statiques (PNG) du rapport, du post LinkedIn et de la vidéo.

    python -m src.restitution.figures        # ou : make figures

Lit app/data/ (export) et docs/resultats/ (entraînement) ; écrit docs/figures/.
"""
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config.settings import RACINE

DATA = RACINE / "app" / "data"
RESULTATS = RACINE / "docs" / "resultats"
SORTIE = RACINE / "docs" / "figures"

# Palette validée (scripts du skill dataviz) : divergente domicile / nul / extérieur
ORANGE, VERT, GRIS, ROUGE = "#E07000", "#006B45", "#9A9A94", "#B8322A"
ENCRE, ENCRE_2, GRILLE = "#1F2328", "#57606A", "#E6E8EB"
NOMS = {"naif": "Référence naïve", "elo": "Elo", "logreg": "Régression logistique",
        "foret": "Forêt aléatoire", "boosting": "Gradient boosting",
        "mlp": "Réseau de neurones"}

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRILLE,
    "axes.labelcolor": ENCRE_2, "xtick.color": ENCRE_2, "ytick.color": ENCRE_2,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.color": GRILLE, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "axes.titleweight": "bold", "axes.titlesize": 12, "axes.titlecolor": ENCRE,
    "axes.titlelocation": "left", "figure.dpi": 100, "savefig.dpi": 200,
    "savefig.bbox": "tight", "legend.frameon": False,
})


def _sauver(fig, nom: str) -> None:
    fig.savefig(SORTIE / f"{nom}.png", facecolor="white")
    plt.close(fig)
    print(f"docs/figures/{nom}.png")


def resultats_par_saison() -> None:
    r = pd.read_parquet(DATA / "resultats_saison.parquet")
    r = r[r["matchs"] >= 90].reset_index(drop=True)  # saison en cours exclue (trop peu de matchs)
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 3.8), gridspec_kw={"width_ratios": [3, 2]})
    bas = np.zeros(len(r))
    for col, couleur, nom in (("pct_domicile", ORANGE, "Victoire domicile"),
                              ("pct_nul", GRIS, "Nul"),
                              ("pct_exterieur", VERT, "Victoire extérieur")):
        a.bar(r["saison"].str[2:4] + "-" + r["saison"].str[7:], r[col], bottom=bas,
              color=couleur, label=nom, edgecolor="white", linewidth=1.5, width=0.75)
        for x, (v, b0) in enumerate(zip(r[col], bas, strict=True)):
            a.text(x, b0 + v / 2, f"{v:.0f}", ha="center", va="center", color="white",
                   fontsize=8, fontweight="bold")
        bas += r[col].to_numpy()
    a.set_ylim(0, 100)
    a.set_ylabel("% des matchs")
    a.set_title("Résultats par saison : 1 match sur 3 est un nul")
    a.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.1))
    a.grid(axis="x", visible=False)
    b.bar(r["saison"].str[2:4] + "-" + r["saison"].str[7:], r["buts_par_match"],
          color=ORANGE, width=0.6)
    b.axhline(2.7, color=ENCRE_2, linestyle="--", linewidth=1)
    b.text(len(r) - 0.6, 2.74, "≈ grands championnats européens", ha="right", fontsize=8,
           color=ENCRE_2)
    b.set_ylim(0, 3)
    b.set_title("Buts par match")
    b.grid(axis="x", visible=False)
    a.tick_params(axis="x", labelsize=8)
    b.tick_params(axis="x", labelsize=7, rotation=45)
    _sauver(fig, "01_resultats_par_saison")


def heatmap_scores() -> None:
    m = pd.read_parquet(DATA / "matchs.parquet")
    m = m[m["statut"] == "joue"]
    tab = pd.crosstab(m["buts_dom"].clip(upper=4), m["buts_ext"].clip(upper=4),
                      normalize=True) * 100
    fig, ax = plt.subplots(figsize=(4.8, 4.2))
    ax.imshow(tab, cmap=matplotlib.colors.LinearSegmentedColormap.from_list(
        "o", ["#FFFFFF", "#FBD9B8", ORANGE, "#8A4300"]))
    for i in range(tab.shape[0]):
        for j in range(tab.shape[1]):
            v = tab.iloc[i, j]
            ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=9,
                    color="white" if v > 8 else ENCRE)
    etiquettes = ["0", "1", "2", "3", "4+"]
    ax.set_xticks(range(5), etiquettes)
    ax.set_yticks(range(5), etiquettes)
    ax.set_xlabel("Buts de l'équipe à l'extérieur")
    ax.set_ylabel("Buts de l'équipe à domicile")
    ax.set_title("Scores (% des matchs)")
    ax.grid(False)
    _sauver(fig, "02_scores")


def _couper_absences(g: pd.DataFrame, colonne: str) -> pd.DataFrame:
    """Insère un trou dans la courbe quand le club n'a pas joué pendant plus de 200 jours."""
    g = g.sort_values("date").reset_index(drop=True)
    trous = g["date"].diff() > pd.Timedelta(days=200)
    lignes = []
    for i, ligne in g.iterrows():
        if trous.iloc[i]:
            lignes.append({"date": ligne["date"] - pd.Timedelta(days=1), colonne: np.nan})
        lignes.append(ligne.to_dict())
    return pd.DataFrame(lignes)


def evolution_elo() -> None:
    df = pd.read_csv(RESULTATS / "jeu_features.csv", parse_dates=["date_match"])
    long = pd.concat([df[["date_match", "dom", "elo_dom"]].set_axis(["date", "club", "elo"],
                                                                      axis=1),
                      df[["date_match", "ext", "elo_ext"]].set_axis(["date", "club", "elo"],
                                                                     axis=1)])
    clubs = {"ASEC Mimosas": ORANGE, "FC San-Pédro": VERT, "Stade d'Abidjan": "#2A78D6",
             "SO Armée": "#7A4FB0"}
    fig, ax = plt.subplots(figsize=(11, 3.8))
    autres = long[~long["club"].isin(clubs)]
    for _, g in autres.groupby("club"):
        g = _couper_absences(g, "elo")
        ax.plot(g["date"], g["elo"], color=GRILLE, linewidth=0.8)
    for club, couleur in clubs.items():
        g = long[long["club"] == club].sort_values("date")
        g = g.assign(lisse=g["elo"].rolling(6, min_periods=1).mean())
        g = _couper_absences(g[["date", "lisse"]], "lisse")
        ax.plot(g["date"], g["lisse"], color=couleur, linewidth=2)
        ax.text(g["date"].iloc[-1] + pd.Timedelta(days=25), g["lisse"].iloc[-1], club,
                color=ENCRE, fontsize=9, va="center")
    ax.set_title("Score Elo des clubs, 2016 → 2026 (en gris : les autres clubs)")
    ax.text(pd.Timestamp("2020-09-15"), 1680, "arrêt\nCovid", ha="center", fontsize=8,
            color=ENCRE_2)
    ax.set_ylabel("Elo")
    ax.set_xlim(right=long["date"].max() + pd.Timedelta(days=500))
    _sauver(fig, "03_elo")


def avantage_terrain() -> None:
    r = pd.read_parquet(DATA / "resultats_club.parquet")
    av = r.groupby(["club", "a_domicile"])["points"].mean().unstack()
    av = av[r.groupby("club").size() >= 120]
    av = av.assign(ecart=av[True] - av[False]).sort_values(True)
    fig, ax = plt.subplots(figsize=(7, 5.5))
    y = np.arange(len(av))
    ax.hlines(y, av[False], av[True], color=GRILLE, linewidth=3)
    ax.scatter(av[False], y, color=VERT, s=45, zorder=3, label="à l'extérieur",
               edgecolor="white", linewidth=1.5)
    ax.scatter(av[True], y, color=ORANGE, s=45, zorder=3, label="à domicile",
               edgecolor="white", linewidth=1.5)
    ax.set_yticks(y, av.index, fontsize=9)
    ax.set_xlabel("Points par match")
    ax.set_title("Avantage du terrain par club (≥ 120 matchs)")
    ax.legend(loc="lower right")
    ax.grid(axis="y", visible=False)
    _sauver(fig, "04_avantage_terrain")


def _etiqueter_sans_chevauchement(fig, ax, noeuds: pd.DataFrame) -> None:
    """Place chaque nom à droite, à gauche, au-dessus ou au-dessous de son nœud,
    à la première position qui ne chevauche ni un nom déjà placé ni un gros nœud."""
    rendu = fig.canvas.get_renderer()
    places = []
    for club, ligne in noeuds.iterrows():
        r = np.sqrt((20 + 9000 * ligne.pagerank) / np.pi) + 2
        for dx, dy, ha, va in ((r, 0, "left", "center"), (-r, 0, "right", "center"),
                               (0, r, "center", "bottom"), (0, -r, "center", "top")):
            t = ax.annotate(club, (ligne.x, ligne.y), xytext=(dx, dy), textcoords="offset points",
                            ha=ha, va=va, fontsize=8, color=ENCRE, zorder=3,
                            bbox={"boxstyle": "round,pad=0.15", "facecolor": "white",
                                  "edgecolor": "none", "alpha": 0.85})
            boite = t.get_window_extent(rendu)
            if not any(boite.overlaps(b) for b in places):
                places.append(boite)
                break
            t.remove()


def reseau() -> None:
    n = pd.read_parquet(DATA / "reseau_noeuds.parquet").dropna(subset=["x"]).set_index("club")
    a = pd.read_parquet(DATA / "reseau_aretes.parquet")
    a = a[a["depart"].isin(n.index) & a["arrivee"].isin(n.index)]
    fig, ax = plt.subplots(figsize=(9, 7))
    for lien in a.itertuples():
        p, q = n.loc[lien.depart], n.loc[lien.arrivee]
        ax.plot([p.x, q.x], [p.y, q.y], color="#C9CDD2", linewidth=0.3 + 0.5 * lien.poids,
                alpha=0.6, zorder=1)
    for ligue1, couleur, nom in ((True, ORANGE, "Ligue 1 ivoirienne"),
                                 (False, VERT, "Club étranger")):
        s = n[n["ligue1"] == ligue1]
        ax.scatter(s["x"], s["y"], s=20 + 9000 * s["pagerank"], color=couleur,
                   edgecolor="white", linewidth=1, zorder=2, label=nom)
    _etiqueter_sans_chevauchement(fig, ax, n.nlargest(12, "pagerank"))
    ax.set_axis_off()
    ax.set_title("Réseau des mouvements de joueurs — taille = PageRank")
    ax.legend(loc="lower left", markerscale=0.5)
    _sauver(fig, "05_reseau")


def comparaison_modeles() -> None:
    g = pd.read_csv(RESULTATS / "validation_glissante.csv")
    moy = g.groupby("modele")[["log_loss", "accuracy"]].mean().sort_values("log_loss",
                                                                          ascending=False)
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 3.8))
    couleurs = [GRIS if i == "naif" else ORANGE for i in moy.index]
    a.barh([NOMS[i] for i in moy.index], moy["accuracy"] * 100, color=couleurs, height=0.6)
    for i, v in enumerate(moy["accuracy"] * 100):
        a.text(v + 0.5, i, f"{v:.1f} %", va="center", fontsize=9, color=ENCRE)
    a.set_xlim(0, 52)
    a.set_title("Précision moyenne (validation glissante)")
    a.set_xlabel("% de résultats correctement prédits")
    a.grid(axis="y", visible=False)
    naif = moy.loc["naif", "log_loss"]
    gain = (naif - moy["log_loss"]) * 1000
    b.barh([NOMS[i] for i in moy.index], gain, color=couleurs, height=0.6)
    for i, v in enumerate(gain):
        b.text(v + 0.4 if v >= 0 else v - 0.4, i, f"{v:+.1f}", va="center", fontsize=9,
               ha="left" if v >= 0 else "right", color=ENCRE)
    b.axvline(0, color=ENCRE_2, linewidth=1)
    b.set_title("Gain de log-loss vs naïf (× 1000, plus = mieux)")
    b.set_yticks([])
    b.grid(axis="y", visible=False)
    _sauver(fig, "06_comparaison_modeles")


def glissante_par_saison() -> None:
    g = pd.read_csv(RESULTATS / "validation_glissante.csv")
    couleurs = {"naif": GRIS, "elo": ORANGE, "logreg": "#2A78D6", "foret": VERT,
                "boosting": "#7A4FB0", "mlp": ROUGE}
    fig, ax = plt.subplots(figsize=(8, 3.8))
    for nom, s in g.groupby("modele"):
        ax.plot(s["saison_test"], s["log_loss"], marker="o", markersize=5, linewidth=2,
                color=couleurs[nom], label=NOMS[nom],
                linestyle="--" if nom == "naif" else "-")
    ax.set_xticks(sorted(g["saison_test"].unique()),
                  [f"{s}-{str(s + 1)[2:]}" for s in sorted(g["saison_test"].unique())])
    ax.set_ylabel("Log-loss (plus bas = mieux)")
    ax.set_title("Log-loss saison par saison (chaque saison prédite avec les précédentes)")
    ax.legend(ncol=3, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    _sauver(fig, "07_glissante_par_saison")


def bootstrap() -> None:
    m = json.loads((RESULTATS / "metriques.json").read_text(encoding="utf-8"))
    b = m["bootstrap_vs_naif"]
    ordre = sorted(b, key=lambda n: b[n]["glissante"]["ecart_moyen"], reverse=True)
    fig, ax = plt.subplots(figsize=(8, 3.6))
    for k, (cadre, couleur, nom, dy) in enumerate((
            ("glissante", ORANGE,
             f"Validation glissante ({m['protocole']['n_glissante']} matchs)", 0.15),
            ("test", VERT, f"Test 2025-26 ({m['protocole']['n_test']} matchs)", -0.15))):
        for i, n in enumerate(ordre):
            e = b[n][cadre]
            ax.plot(e["ic95"], [i + dy] * 2, color=couleur, linewidth=2)
            ax.scatter(e["ecart_moyen"], i + dy, color=couleur, s=40, zorder=3,
                       edgecolor="white", label=nom if i == 0 else None)
    ax.axvline(0, color=ENCRE_2, linestyle="--", linewidth=1)
    ax.set_yticks(range(len(ordre)), [NOMS[n] for n in ordre])
    ax.set_xlabel("Écart de log-loss vs naïf (IC 95 %) — à gauche de 0 : meilleur que le naïf")
    ax.set_title("Le gain est-il significatif ? (bootstrap)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, fontsize=8)
    ax.grid(axis="y", visible=False)
    _sauver(fig, "08_bootstrap")


def calibration_et_confusion() -> None:
    m = json.loads((RESULTATS / "metriques.json").read_text(encoding="utf-8"))
    retenu = m["modele_retenu"]
    cal = pd.read_csv(RESULTATS / "calibration.csv")
    cal = cal[cal["modele"] == retenu]
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 4))
    for classe, couleur, nom in (("D", ORANGE, "domicile"), ("N", GRIS, "nul"),
                                 ("E", VERT, "extérieur")):
        s = cal[cal["classe"] == classe]
        a.plot(s["proba_moyenne"], s["frequence_observee"], marker="o", color=couleur,
               linewidth=2, label=nom)
    a.plot([0.1, 0.65], [0.1, 0.65], color=ENCRE_2, linestyle="--", linewidth=1)
    a.set_xlabel("Probabilité prédite")
    a.set_ylabel("Fréquence observée")
    a.set_title(f"Calibration — {NOMS[retenu]}")
    a.legend(title="Classe", fontsize=8)
    cm = pd.DataFrame(m["confusions"][retenu]).to_numpy()   # lignes = réel, colonnes = prédit
    b.imshow(cm, cmap=matplotlib.colors.LinearSegmentedColormap.from_list(
        "o", ["#FFFFFF", ORANGE]))
    for i in range(3):
        for j in range(3):
            b.text(j, i, cm[i, j], ha="center", va="center", fontsize=12,
                   color="white" if cm[i, j] > cm.max() * 0.6 else ENCRE)
    b.set_xticks(range(3), ["prédit D", "prédit N", "prédit E"])
    b.set_yticks(range(3), ["réel D", "réel N", "réel E"])
    b.set_title("Matrice de confusion (test 2025-26)")
    b.grid(False)
    _sauver(fig, "09_calibration_confusion")


def importance() -> None:
    imp = pd.read_csv(RESULTATS / "importance_variables.csv")
    imp = imp[imp["modele"] == "logreg"].head(10).iloc[::-1]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.barh(imp["variable"], imp["hausse_log_loss"] * 1000, xerr=imp["ecart_type"] * 1000,
            color=ORANGE, height=0.6, error_kw={"ecolor": ENCRE_2, "linewidth": 1})
    ax.set_xlabel("Hausse de la log-loss (× 1000) quand la variable est mélangée")
    ax.set_title("Variables les plus utiles — régression logistique")
    ax.grid(axis="y", visible=False)
    _sauver(fig, "10_importance")


def architecture() -> None:
    fig, ax = plt.subplots(figsize=(12, 3.2))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 3.2)
    ax.set_axis_off()
    blocs = [(0.1, "Collecte web", "RSSSF · Wikipédia\nFutbol24 · API-Football\nPython quotidien"),
             (2.5, "MongoDB", "zone brute\nHTML archivé\n(URL, date, SHA-256)"),
             (4.9, "PostgreSQL", "modèle Merise\nETL + recoupements\n10 requêtes SQL"),
             (7.3, "Modèles", "Elo · régression log.\nforêt · boosting\nMLP PyTorch"),
             (9.7, "Streamlit", "tableau de bord\nprédictions\nréseau des clubs")]
    for x, titre, texte in blocs:
        ax.add_patch(matplotlib.patches.FancyBboxPatch(
            (x, 0.5), 2.1, 2.2, boxstyle="round,pad=0.02,rounding_size=0.15",
            facecolor="#FFF3E6" if titre != "Modèles" else "#E6F2EC",
            edgecolor=ORANGE if titre != "Modèles" else VERT, linewidth=1.5))
        ax.text(x + 1.05, 2.3, titre, ha="center", fontsize=12, fontweight="bold",
                color=ENCRE)
        ax.text(x + 1.05, 1.45, texte, ha="center", va="center", fontsize=9, color=ENCRE_2,
                linespacing=1.5)
    for x in (2.2, 4.6, 7.0, 9.4):
        ax.annotate("", xy=(x + 0.3, 1.6), xytext=(x, 1.6),
                    arrowprops={"arrowstyle": "-|>", "color": ENCRE_2, "linewidth": 1.5})
    ax.text(6, 0.15, "networkx / Neo4j : graphe des carrières et transferts (PageRank, "
            "communautés)", ha="center", fontsize=9, color=ENCRE_2, style="italic")
    _sauver(fig, "00_architecture")


def main() -> None:
    SORTIE.mkdir(parents=True, exist_ok=True)
    for f in (architecture, resultats_par_saison, heatmap_scores, evolution_elo,
              avantage_terrain, reseau, comparaison_modeles, glissante_par_saison, bootstrap,
              calibration_et_confusion, importance):
        f()


if __name__ == "__main__":
    main()

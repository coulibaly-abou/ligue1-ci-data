"""Fiches joueurs : déroulé des buts, buts décisifs et note de contribution offensive /10.

Les évènements API-Football (saisons 2022-23 → 2024-25) donnent, pour chaque but, le
buteur et la minute, mais ni le temps de jeu ni les passes décisives. La note mesure donc
la contribution offensive d'un joueur dans sa saison, pas sa performance globale :

    note = 10 × (35 % rang des buts + 25 % rang des buts décisifs
                 + 20 % rang de la part des buts du club + 20 % rang des matchs avec but)
           - 0,5 par carton rouge          (bornée entre 0 et 10)

Chaque « rang » est le rang-centile du joueur parmi les buteurs de la même saison
(0 = le plus faible, 1 = le meilleur) : la note compare un joueur à ses pairs.
"""
import unicodedata

import pandas as pd

POIDS = {"buts": 0.35, "buts_decisifs": 0.25, "part_buts_club": 0.20, "matchs_avec_but": 0.20}
MALUS_ROUGE = 0.5


def cle_joueur(api_id, nom: str | None, club: str) -> str:
    """Identifiant stable : l'id API-Football, sinon le nom abrégé et le club."""
    return f"api{int(api_id)}" if pd.notna(api_id) else f"{nom}|{club}"


def derouler_buts(buts: pd.DataFrame, matchs: pd.DataFrame) -> pd.DataFrame:
    """Score avant / après chaque but, du point de vue de l'équipe qui marque.

    `buts` : id_match, minute, club (club crédité du but, contre son camp compris).
    `matchs` : id_match, dom, ext, buts_dom, buts_ext.
    Seuls les matchs dont le déroulé redonne le score final sont gardés (`complet`).
    Un but est décisif s'il égalise ou donne l'avantage.
    """
    b = buts.merge(matchs[["id_match", "dom", "ext", "buts_dom", "buts_ext"]], on="id_match")
    b = b.sort_values(["id_match", "minute"], kind="stable").copy()
    b["pour_dom"] = b["club"] == b["dom"]
    b["score_dom"] = b.groupby("id_match")["pour_dom"].cumsum()
    b["score_ext"] = b.groupby("id_match").cumcount() + 1 - b["score_dom"]
    total = b.groupby("id_match").agg(d=("pour_dom", "sum"), n=("pour_dom", "size"))
    complet = (total["d"] == b.groupby("id_match")["buts_dom"].first()) & \
              (total["n"] - total["d"] == b.groupby("id_match")["buts_ext"].first())
    b["complet"] = b["id_match"].map(complet)
    pour = b["score_dom"].where(b["pour_dom"], b["score_ext"])
    contre = b["score_ext"].where(b["pour_dom"], b["score_dom"])
    b["ecart_avant"] = (pour - 1) - contre
    b["decisif"] = b["complet"] & b["ecart_avant"].isin([-1, 0])
    return b.drop(columns=["pour_dom"])


def notes_joueurs(buts: pd.DataFrame, cartons: pd.DataFrame,
                  buts_club_saison: pd.DataFrame) -> pd.DataFrame:
    """Une ligne par joueur et par saison : statistiques et note /10.

    `buts` : sortie de derouler_buts + saison, type_but, buteur, api_joueur_id.
    `cartons` : saison, joueur, api_joueur_id, club, couleur.
    `buts_club_saison` : saison, club, bp (buts du club dans toute la saison).
    """
    b = buts[(buts["type_but"] != "contre_son_camp") & buts["buteur"].notna()].copy()
    b["joueur"] = [cle_joueur(a, n, c) for a, n, c in
                   zip(b["api_joueur_id"], b["buteur"], b["club"], strict=True)]
    stats = b.groupby(["saison", "joueur"]).agg(
        nom=("buteur", "last"), club=("club", "last"), buts=("id_match", "size"),
        penalties=("type_but", lambda s: int((s == "penalty").sum())),
        buts_decisifs=("decisif", "sum"), matchs_avec_but=("id_match", "nunique"),
        minute_moyenne=("minute", "mean")).reset_index()

    c = cartons[cartons["couleur"].isin(["rouge", "jaune_rouge"]) & cartons["joueur"].notna()]
    rouges = pd.Series([cle_joueur(a, n, k) for a, n, k in
                        zip(c["api_joueur_id"], c["joueur"], c["club"], strict=True)],
                       dtype=object)
    rouges = pd.DataFrame({"saison": c["saison"].to_numpy(), "joueur": rouges.to_numpy()}) \
        .groupby(["saison", "joueur"]).size().rename("rouges")
    stats = stats.join(rouges, on=["saison", "joueur"])
    stats["rouges"] = stats["rouges"].fillna(0).astype(int)

    stats = stats.merge(buts_club_saison.rename(columns={"bp": "buts_club"}),
                        on=["saison", "club"], how="left")
    stats["part_buts_club"] = stats["buts"] / stats["buts_club"]

    rangs = sum(poids * stats.groupby("saison")[col].rank(pct=True)
                for col, poids in POIDS.items())
    stats["note"] = (10 * rangs - MALUS_ROUGE * stats["rouges"]).clip(0, 10).round(1)
    stats["rang_saison"] = stats.groupby("saison")["note"].rank(
        ascending=False, method="min").astype(int)
    return stats.sort_values(["saison", "note"], ascending=[True, False]) \
        .reset_index(drop=True)


def _sans_accents(texte: str) -> str:
    texte = unicodedata.normalize("NFKD", texte or "")
    return "".join(c for c in texte if not unicodedata.combining(c)).lower().replace("-", " ")


def _correspond(abrege: str, prenom: str | None, nom: str | None) -> bool:
    """« K. Abissa » correspond-il à (prénom, nom) ? Initiale du prénom + dernier mot du nom."""
    mots = _sans_accents(abrege).replace(".", ". ").split()
    if not mots:
        return False
    famille = _sans_accents(nom).split()
    if mots[-1] not in famille:
        return False
    initiales = [m[0] for m in mots[:-1]]
    return not initiales or _sans_accents(prenom)[:1] == initiales[0] or         any(f[:1] == initiales[0] for f in famille)


def rapprocher_profils(notes: pd.DataFrame, effectifs: pd.DataFrame) -> pd.Series:
    """Id API-Football de chaque ligne de `notes`, retrouvé dans l'effectif du club.

    `effectifs` : saison, club, api_joueur_id, prenom, nom_famille. Le rapprochement
    n'est retenu que s'il désigne un seul joueur de l'effectif (sinon : inconnu).
    """
    par_club = {k: g for k, g in effectifs.groupby(["saison", "club"])}
    ids = []
    for saison, club, nom in zip(notes["saison"], notes["club"], notes["nom"], strict=True):
        g = par_club.get((saison, club))
        trouves = [] if g is None else [
            i for i, p, f in zip(g["api_joueur_id"], g["prenom"], g["nom_famille"], strict=True)
            if _correspond(nom, p, f)]
        ids.append(trouves[0] if len(set(trouves)) == 1 else None)
    return pd.Series(ids, index=notes.index, dtype="Int64")

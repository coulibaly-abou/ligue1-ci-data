"""Construction des tables du modèle relationnel (MLD, docs/modele_donnees.md)
à partir de la zone brute MongoDB.

Chaque fonction construire_* renvoie un DataFrame prêt à charger dans la table
du même nom (sql/schema.sql). Les identifiants sont attribués ici, en Python,
pour relier facilement les tables entre elles.

Règles de priorité entre sources (une seule ligne par match) :
- saisons publiées par RSSSF : RSSSF (journée, date, statut) ;
- saison en cours : Futbol24 (daté), complété par la grille Wikipédia ;
- API-Football (2022-2024) enrichit les matchs RSSSF : stade, arbitre, id API.
Les autres sources servent au recoupement (journal des anomalies).
"""
from collections import defaultdict

import pandas as pd

from config.settings import SAISON_EN_COURS, SAISONS
from src.etl.nettoyage import (
    anomalies_match,
    capacite_plausible,
    normaliser,
    resoudre_club,
    resoudre_stade,
)
from src.utils.logs import get_logger

log = get_logger("etl")

TYPES_TABLEAU = {"final table": "final", "halfway table": "mi-saison",
                 "table at abandonment": "arret", "wikipedia": "final"}
SAISONS_ATYPIQUES = {"2019-2020": ("championnat", "interrompue"),
                     "2020-2021": ("poules + play-off", "terminee")}


def id_saison(libelle: str) -> int:
    return int(libelle[:4])


class Referentiel:
    """Lignes d'une table de référence, avec recherche par clé normalisée."""

    def __init__(self, colonne_id: str):
        self.colonne_id = colonne_id
        self.index: dict[str, int] = {}
        self.lignes: list[dict] = []

    def obtenir(self, cle: str, **valeurs) -> int:
        """id de la ligne de clé `cle`, créée si besoin ; complète les champs vides."""
        if cle not in self.index:
            self.index[cle] = len(self.lignes) + 1
            self.lignes.append({self.colonne_id: self.index[cle], **valeurs})
        ligne = self.lignes[self.index[cle] - 1]
        for champ, valeur in valeurs.items():
            if ligne.get(champ) in (None, False) and valeur not in (None, False):
                ligne[champ] = valeur
        return self.index[cle]

    def ligne(self, id_: int) -> dict:
        return self.lignes[id_ - 1]

    def table(self) -> pd.DataFrame:
        return pd.DataFrame(self.lignes)


class Contexte:
    """Données brutes chargées une fois + référentiels partagés (ville, stade, club)."""

    def __init__(self, db):
        self.db = db
        self.api = defaultdict(list)  # endpoint -> [(params, réponse)]
        for doc in db.raw_api.find({}, {"endpoint": 1, "params": 1, "reponse.response": 1}):
            self.api[doc["endpoint"]].append((doc["params"], doc["reponse"]["response"]))
        self.villes = Referentiel("id_ville")
        self.stades = Referentiel("id_stade")
        self.clubs = Referentiel("id_club")
        self.club_api: dict[int, int] = {}  # id équipe API-Football -> id_club
        self.anomalies: list[dict] = []

    def id_ville(self, nom: str | None) -> int | None:
        cle = normaliser(nom)
        return self.villes.obtenir(cle, nom=nom.strip()) if cle else None

    def id_stade(self, nom: str | None, ville=None, capacite=None) -> int | None:
        nom = resoudre_stade(nom)
        if not nom:
            return None
        return self.stades.obtenir(normaliser(nom), nom=nom, id_ville=self.id_ville(ville),
                                   capacite=capacite_plausible(capacite))

    def id_club(self, nom: str | None, ligue1: bool = False) -> int | None:
        """id d'un club : nom harmonisé si club de Ligue 1, sinon club « externe »."""
        if not nom or not normaliser(nom):
            return None
        officiel = resoudre_club(nom)
        cle = officiel or "externe:" + normaliser(nom)
        return self.clubs.obtenir(cle, nom=officiel or nom.strip(), est_ligue1=ligue1,
                                  api_id=None, id_ville=None, id_stade=None)

    def anomalie(self, table: str, description: str, detail: str = "") -> None:
        self.anomalies.append({"table": table, "description": description, "detail": detail})


# ------------------------------------------------------- référentiels

def preparer_clubs_et_stades(ctx: Contexte) -> None:
    """Clubs de Ligue 1 avec ville et stade (Wikipédia, puis API-Football)."""
    for doc in ctx.db.raw_clubs.find().sort("saison", -1):  # la saison la plus récente d'abord
        cid = ctx.id_club(doc["club"], ligue1=True)
        ligne = ctx.clubs.ligne(cid)
        ligne["id_ville"] = ligne["id_ville"] or ctx.id_ville(doc.get("ville"))
        # la colonne « Ville » de Wikipédia est celle du club, pas du stade : la ville
        # d'un stade ne vient que d'API-Football
        ligne["id_stade"] = ligne["id_stade"] or ctx.id_stade(
            doc.get("stade"), None, doc.get("capacite"))
    for _, reponse in ctx.api["/teams"]:
        for item in reponse:
            cid = ctx.id_club(item["team"]["name"], ligue1=True)
            ctx.club_api[item["team"]["id"]] = cid
            ligne = ctx.clubs.ligne(cid)
            ligne["api_id"] = item["team"]["id"]
            lieu = item.get("venue") or {}
            ligne["id_stade"] = ligne["id_stade"] or ctx.id_stade(
                lieu.get("name"), lieu.get("city"), lieu.get("capacity"))
            ligne["id_ville"] = ligne["id_ville"] or ctx.id_ville(lieu.get("city"))


def construire_saison(matchs: pd.DataFrame) -> pd.DataFrame:
    lignes = []
    for libelle in SAISONS:
        sid = id_saison(libelle)
        de_la_saison = matchs[matchs.id_saison == sid]
        nb_clubs = len(set(de_la_saison.id_club_dom) | set(de_la_saison.id_club_ext)) or None
        fmt, statut = SAISONS_ATYPIQUES.get(libelle, ("championnat", "terminee"))
        lignes.append({"id_saison": sid, "libelle": libelle, "annee_debut": sid,
                       "annee_fin": sid + 1, "nb_clubs": nb_clubs, "format": fmt,
                       "statut": "en_cours" if libelle == SAISON_EN_COURS else statut})
    return pd.DataFrame(lignes)


# ---------------------------------------------------------------------- matchs

def _matchs_bruts(ctx: Contexte, source: str) -> list[dict]:
    return list(ctx.db.raw_matches.find({"source": source}, {"_id": 0}))


def _cle(m: dict) -> tuple:
    return m["saison"], resoudre_club(m["equipe_dom"]), resoudre_club(m["equipe_ext"])


def _index_api_fixtures(ctx: Contexte) -> dict:
    """(saison, id_club_dom, id_club_ext) -> [rencontres API-Football]."""
    index = defaultdict(list)
    for params, reponse in ctx.api["/fixtures"]:
        for f in reponse:
            index[(params["season"], ctx.club_api.get(f["teams"]["home"]["id"]),
                   ctx.club_api.get(f["teams"]["away"]["id"]))].append(f)
    return index


def _selectionner_matchs(ctx: Contexte) -> list[dict]:
    """Une ligne par match, selon la priorité des sources (voir docstring du module)."""
    lignes = _matchs_bruts(ctx, "rsssf")
    saisons_rsssf = {m["saison"] for m in lignes}
    deja = {_cle(m) for m in lignes}
    for source in ("futbol24", "wikipedia"):  # saison(s) que RSSSF n'a pas encore publiées
        for m in _matchs_bruts(ctx, source):
            if m["saison"] not in saisons_rsssf and _cle(m) not in deja:
                lignes.append(m)
                deja.add(_cle(m))

    # Matchs à jouer de la saison en cours, avec la date Futbol24 si elle est confirmée
    dates_prevues = {_cle(f): f["date"] for f in ctx.db.raw_fixtures.find(
        {"source": "futbol24", "saison": SAISON_EN_COURS}) if not f.get("horaire_provisoire")}
    for f in ctx.db.raw_fixtures.find({"source": "wikipedia", "saison": SAISON_EN_COURS}):
        if _cle(f) not in deja:
            deja.add(_cle(f))
            lignes.append({**f, "phase": "Saison reguliere", "journee": None,
                           "date": dates_prevues.get(_cle(f)), "buts_dom": None,
                           "buts_ext": None, "statut": "a_jouer", "note": None})
    return lignes


def construire_match(ctx: Contexte) -> pd.DataFrame:
    index_api = _index_api_fixtures(ctx)
    lignes = []
    for i, m in enumerate(_selectionner_matchs(ctx), start=1):
        dom, ext = ctx.id_club(m["equipe_dom"], True), ctx.id_club(m["equipe_ext"], True)
        ligne = {
            "id_match": i, "phase": m["phase"], "journee": m.get("journee"),
            "date_match": m.get("date"), "buts_dom": m.get("buts_dom"),
            "buts_ext": m.get("buts_ext"), "statut": m["statut"], "arbitre": None,
            "note": m.get("note"), "source": m["source"], "api_fixture_id": None,
            "id_saison": id_saison(m["saison"]), "id_club_dom": dom, "id_club_ext": ext,
            "id_stade": ctx.clubs.ligne(dom)["id_stade"],  # par défaut : stade du club recevant
        }
        # Enrichissement API-Football (stade réel, arbitre) + recoupement du score
        candidats = index_api.get((ligne["id_saison"], dom, ext), [])
        if candidats and m["statut"] == "joue":
            f = min(candidats, key=lambda c: abs(
                pd.Timestamp(c["fixture"]["date"][:10]) - pd.Timestamp(m.get("date") or "2000")))
            lieu = f["fixture"].get("venue") or {}
            ligne["id_stade"] = ctx.id_stade(lieu.get("name"), lieu.get("city")) \
                or ligne["id_stade"]
            ligne["arbitre"] = f["fixture"].get("referee")
            ligne["api_fixture_id"] = f["fixture"]["id"]
            buts_api = (f["goals"]["home"], f["goals"]["away"])
            if buts_api != (ligne["buts_dom"], ligne["buts_ext"]):
                ctx.anomalie("match", "score différent RSSSF / API-Football",
                             f"{m['saison']} {m['equipe_dom']}-{m['equipe_ext']} : "
                             f"{ligne['buts_dom']}-{ligne['buts_ext']} vs {buts_api}")
        for probleme in anomalies_match({**m, "club_dom": dom, "club_ext": ext}):
            ctx.anomalie("match", probleme,
                         f"{m['saison']} {m['equipe_dom']}-{m['equipe_ext']} ({m['source']})")
        lignes.append(ligne)

    df = pd.DataFrame(lignes)
    df["date_match"] = pd.to_datetime(df["date_match"]).dt.date
    # api_fixture_id est UNIQUE : un même match API ne sert qu'une fois
    doublon = df["api_fixture_id"].notna() & df["api_fixture_id"].duplicated()
    df.loc[doublon, "api_fixture_id"] = None
    return df


def recouper_wikipedia(ctx: Contexte, matchs: pd.DataFrame) -> dict:
    """Compare les scores retenus avec la grille Wikipédia (contrôle de l'harmonisation)."""
    reference = {(r.id_saison, r.id_club_dom, r.id_club_ext): (r.buts_dom, r.buts_ext)
                 for r in matchs.itertuples() if r.statut == "joue" and r.source == "rsssf"}
    bilan = {"identiques": 0, "differents": 0, "absents": 0}
    for m in _matchs_bruts(ctx, "wikipedia"):
        cle = (id_saison(m["saison"]), ctx.id_club(m["equipe_dom"]),
               ctx.id_club(m["equipe_ext"]))
        if cle not in reference:
            bilan["absents"] += 1
        elif reference[cle] == (m["buts_dom"], m["buts_ext"]):
            bilan["identiques"] += 1
        else:
            bilan["differents"] += 1
            ctx.anomalie("match", "score différent RSSSF / Wikipédia",
                         f"{m['saison']} {m['equipe_dom']}-{m['equipe_ext']} : "
                         f"{reference[cle]} vs {(m['buts_dom'], m['buts_ext'])}")
    return bilan


# ---------------------------------------------------- buts et cartons (API)

def construire_but_et_carton(ctx: Contexte, matchs: pd.DataFrame):
    par_fixture = {int(f): int(m) for f, m in
                   zip(matchs.api_fixture_id, matchs.id_match) if pd.notna(f)}
    couleurs = {"Yellow Card": "jaune", "Red Card": "rouge", "Second Yellow card": "jaune_rouge"}
    types_but = {"Normal Goal": "normal", "Penalty": "penalty", "Own Goal": "contre_son_camp"}
    buts, cartons = [], []
    for params, reponse in ctx.api["/fixtures/events"]:
        id_match = par_fixture.get(params["fixture"])
        if id_match is None:
            continue
        for e in reponse:
            club = ctx.club_api.get(e["team"]["id"]) or ctx.id_club(e["team"]["name"])
            minute = (e["time"]["elapsed"] or 0) + (e["time"]["extra"] or 0) or None
            if e["type"] == "Goal" and e["detail"] in types_but:
                buts.append({"id_but": len(buts) + 1, "minute": minute,
                             "type_but": types_but[e["detail"]], "buteur": e["player"]["name"],
                             "passeur": e["assist"]["name"], "id_match": id_match,
                             "id_club": club, "id_personne": None})
            elif e["type"] == "Card" and e["detail"] in couleurs:
                cartons.append({"id_carton": len(cartons) + 1, "minute": minute,
                                "couleur": couleurs[e["detail"]], "joueur": e["player"]["name"],
                                "id_match": id_match, "id_club": club, "id_personne": None})
    return pd.DataFrame(buts), pd.DataFrame(cartons)


# --------------------------------------------------- classements et buteurs

def construire_classement(ctx: Contexte) -> pd.DataFrame:
    lignes = []
    for c in ctx.db.raw_standings.find({}, {"_id": 0}):
        type_tableau = TYPES_TABLEAU.get(c["type_tableau"], c["type_tableau"])
        if c["source"] == "wikipedia" and c["saison"] == SAISON_EN_COURS:
            type_tableau = "en_cours"
        lignes.append({
            "phase": c["phase"], "groupe": c.get("groupe") or "", "type_tableau": type_tableau,
            "rang": c["rang"], "joues": c["j"], "gagnes": c["g"], "nuls": c["n"],
            "perdus": c["p"], "buts_pour": c["bp"], "buts_contre": c["bc"],
            "points": c["pts"], "mention": c.get("mention"), "source": c["source"],
            "id_saison": id_saison(c["saison"]), "id_club": ctx.id_club(c["equipe"], True),
        })
    df = pd.DataFrame(lignes)
    cle = ["id_saison", "id_club", "phase", "groupe", "type_tableau", "source"]
    doublons = df.duplicated(cle)
    for _, r in df[doublons].iterrows():
        ctx.anomalie("classement", "ligne de classement en double", str(r[cle].to_dict()))
    df = df[~doublons].reset_index(drop=True)
    df.insert(0, "id_classement", df.index + 1)
    return df


def construire_stat_buteur(ctx: Contexte) -> pd.DataFrame:
    lignes = [{"joueur": b["joueur"], "buts": b["buts"], "matchs": b.get("matchs"),
               "source": b["source"], "id_saison": id_saison(b["saison"]),
               "id_club": ctx.id_club(b.get("club"), True), "id_personne": None}
              for b in ctx.db.raw_scorers.find({}, {"_id": 0}) if b.get("buts") is not None]
    for params, reponse in ctx.api["/players/topscorers"]:
        for p in reponse:
            stats = p["statistics"][0]
            if stats["goals"]["total"] is None:
                continue
            lignes.append({"joueur": p["player"]["name"], "buts": stats["goals"]["total"],
                           "matchs": stats["games"]["appearences"], "source": "api_football",
                           "id_saison": params["season"],
                           "id_club": ctx.club_api.get(stats["team"]["id"]),
                           "id_personne": None})
    df = pd.DataFrame(lignes).drop_duplicates(["id_saison", "joueur", "source"])
    df = df.reset_index(drop=True)
    df.insert(0, "id_stat", df.index + 1)
    return df


# ------------------------------------------------ personnes et passages

def construire_personne_et_passage(ctx: Contexte):
    """Personnes et passages en club : Wikipédia (fiche anglaise prioritaire),
    puis entraîneurs API-Football."""
    fiches = list(ctx.db.raw_persons.find({}, {"_id": 0}))
    urls_en = {f["url"] for f in fiches if f["langue"] == "en"}
    personnes, passages = [], []
    par_identite = {}  # (nom normalisé, date de naissance) -> id_personne

    def ajouter_passage(id_personne, club, role, debut, fin, pret, matchs, buts, source):
        passages.append({
            "id_passage": len(passages) + 1, "role": role, "annee_debut": debut,
            "annee_fin": fin, "pret": pret, "matchs": matchs, "buts": buts,
            "club_brut": club, "source": source, "id_personne": id_personne,
            "id_club": None if role == "selection" else ctx.id_club(club),
        })

    for f in fiches:
        if f["langue"] == "fr" and f.get("url_autre_langue") in urls_en:
            continue  # la même personne a une fiche anglaise : on garde celle-ci
        pid = len(personnes) + 1
        roles = set(f.get("roles", []))
        types = {p["type"] for p in f["passages"]}
        personnes.append({
            "id_personne": pid, "nom": f["nom"], "nom_complet": f.get("nom_complet"),
            "date_naissance": f.get("naissance"), "nationalite": f.get("nationalite"),
            "poste": f.get("poste"),
            "est_joueur": "joueur" in roles or bool(types & {"senior", "jeunes"}),
            "est_entraineur": "entraineur" in roles or "entraineur" in types,
            "url_wikipedia": f["url"], "api_id": None,
        })
        par_identite[(normaliser(f["nom"]), f.get("naissance"))] = pid
        for p in f["passages"]:
            ajouter_passage(pid, p["club"], p["type"], p["debut"], p["fin"], p["pret"],
                            p["matchs"], p["buts"], f["source"])

    for _, reponse in ctx.api["/coachs"]:
        for c in reponse:
            naissance = (c.get("birth") or {}).get("date")
            nom = " ".join(filter(None, [c.get("firstname"), c.get("lastname")])) or c["name"]
            pid = par_identite.get((normaliser(nom), naissance))
            if pid is None:
                pid = len(personnes) + 1
                par_identite[(normaliser(nom), naissance)] = pid
                personnes.append({
                    "id_personne": pid, "nom": nom, "nom_complet": nom,
                    "date_naissance": naissance, "nationalite": c.get("nationality"),
                    "poste": None, "est_joueur": False, "est_entraineur": True,
                    "url_wikipedia": None, "api_id": c["id"],
                })
            else:
                personnes[pid - 1].update(est_entraineur=True, api_id=c["id"])
            for poste in c.get("career", []):
                ajouter_passage(pid, poste["team"]["name"], "entraineur",
                                int(poste["start"][:4]) if poste.get("start") else None,
                                int(poste["end"][:4]) if poste.get("end") else None,
                                False, None, None, "api_football")

    df_personnes = pd.DataFrame(personnes)
    doublon_api = df_personnes["api_id"].notna() & df_personnes["api_id"].duplicated()
    df_personnes.loc[doublon_api, "api_id"] = None
    return df_personnes, pd.DataFrame(passages)


def construire_transfert(ctx: Contexte) -> pd.DataFrame:
    lignes, vus = [], set()
    for _, reponse in ctx.api["/transfers"]:
        for item in reponse:
            joueur = item["player"]
            for t in item["transfers"]:
                depart, arrivee = t["teams"]["out"], t["teams"]["in"]
                cle = (joueur["id"], t.get("date"), depart["id"], arrivee["id"])
                if cle in vus:  # le même transfert figure chez les deux clubs
                    continue
                vus.add(cle)
                lignes.append({
                    "id_transfert": len(lignes) + 1, "joueur": joueur["name"],
                    "date_transfert": t.get("date") or None, "type_transfert": t.get("type"),
                    "source": "api_football", "id_personne": None,
                    "id_club_depart": ctx.club_api.get(depart["id"])
                    or ctx.id_club(depart["name"]),
                    "id_club_arrivee": ctx.club_api.get(arrivee["id"])
                    or ctx.id_club(arrivee["name"]),
                })
    df = pd.DataFrame(lignes)
    if not df.empty:  # dates invalides de l'API (ex. « 0000-00-00 ») -> NULL
        df["date_transfert"] = pd.to_datetime(df["date_transfert"], errors="coerce").dt.date
    return df


# ------------------------------------------------------------ assemblage

def construire_tout(db) -> tuple[dict[str, pd.DataFrame], Contexte]:
    """Toutes les tables, dans l'ordre de chargement (tables référencées d'abord)."""
    ctx = Contexte(db)
    preparer_clubs_et_stades(ctx)
    match = construire_match(ctx)
    log.info("Recoupement RSSSF / Wikipédia : %s", recouper_wikipedia(ctx, match))
    but, carton = construire_but_et_carton(ctx, match)
    classement = construire_classement(ctx)
    stat_buteur = construire_stat_buteur(ctx)
    personne, passage = construire_personne_et_passage(ctx)
    transfert = construire_transfert(ctx)
    # ville, stade et club sont construits en dernier : les étapes ci-dessus ont pu y
    # ajouter des lignes (clubs externes des carrières et des transferts)
    tables = {
        "ville": ctx.villes.table(),
        "stade": ctx.stades.table(),
        "club": ctx.clubs.table(),
        "saison": construire_saison(match),
        "personne": personne,
        "match": match,
        "but": but,
        "carton": carton,
        "classement": classement,
        "passage": passage,
        "transfert": transfert,
        "stat_buteur": stat_buteur,
    }
    return tables, ctx

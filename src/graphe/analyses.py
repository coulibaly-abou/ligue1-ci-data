"""Analyses du réseau des clubs (mouvements de joueurs) avec networkx.

Le graphe relie deux clubs quand un joueur passe de l'un à l'autre :
- carrières Wikipédia (passages seniors consécutifs d'une même personne) ;
- transferts déclarés par API-Football.
Mêmes algorithmes que Neo4j Graph Data Science (PageRank, communautés de Louvain),
calculés ici pour que le tableau de bord déployé n'ait pas besoin d'un serveur Neo4j.
"""
import networkx as nx
import pandas as pd

SQL_PASSAGES = """
SELECT pa.id_personne, pa.annee_debut, pa.annee_fin, pa.pret, c.nom AS club, c.est_ligue1
FROM ligue1.passage pa JOIN ligue1.club c USING (id_club)
WHERE pa.role = 'senior' AND pa.annee_debut IS NOT NULL
ORDER BY pa.id_personne, pa.annee_debut, pa.id_passage
"""

SQL_TRANSFERTS = """
SELECT t.joueur, t.date_transfert, t.type_transfert,
       d.nom AS depart, d.est_ligue1 AS depart_ligue1,
       a.nom AS arrivee, a.est_ligue1 AS arrivee_ligue1
FROM ligue1.transfert t
JOIN ligue1.club d ON d.id_club = t.id_club_depart
JOIN ligue1.club a ON a.id_club = t.id_club_arrivee
"""


def mouvements(passages: pd.DataFrame, transferts: pd.DataFrame) -> pd.DataFrame:
    """Une ligne par mouvement club -> club touchant au moins un club de Ligue 1."""
    p = passages.sort_values(["id_personne", "annee_debut"])
    suivant = p.groupby("id_personne").shift(-1)
    carrieres = pd.DataFrame({
        "depart": p["club"], "arrivee": suivant["club"], "annee": suivant["annee_debut"],
        "depart_ligue1": p["est_ligue1"], "arrivee_ligue1": suivant["est_ligue1"],
        "pret": suivant["pret"], "source": "carrieres_wikipedia"}).dropna(subset=["arrivee"])
    api = pd.DataFrame({
        "depart": transferts["depart"], "arrivee": transferts["arrivee"],
        "annee": pd.to_datetime(transferts["date_transfert"]).dt.year,
        "depart_ligue1": transferts["depart_ligue1"],
        "arrivee_ligue1": transferts["arrivee_ligue1"],
        "pret": transferts["type_transfert"].fillna("").str.contains("Loan"),
        "source": "api_football"})
    tout = pd.concat([carrieres, api], ignore_index=True)
    tout = tout[(tout["depart"] != tout["arrivee"])
                & (tout["depart_ligue1"].astype(bool) | tout["arrivee_ligue1"].astype(bool))]
    return tout.reset_index(drop=True)


def construire_graphe(mvts: pd.DataFrame) -> nx.DiGraph:
    aretes = mvts.groupby(["depart", "arrivee"]).size().reset_index(name="poids")
    g = nx.DiGraph()
    ligue1 = set(mvts.loc[mvts["depart_ligue1"].astype(bool), "depart"]) | \
        set(mvts.loc[mvts["arrivee_ligue1"].astype(bool), "arrivee"])
    for a in aretes.itertuples():
        g.add_edge(a.depart, a.arrivee, poids=int(a.poids))
    nx.set_node_attributes(g, {n: n in ligue1 for n in g.nodes}, "ligue1")
    return g


def indicateurs(g: nx.DiGraph) -> pd.DataFrame:
    """PageRank, degrés pondérés, intermédiarité et communauté de chaque club."""
    pagerank = nx.pagerank(g, weight="poids")
    non_oriente = g.to_undirected()
    intermediarite = nx.betweenness_centrality(non_oriente, weight=None)
    communautes = nx.community.louvain_communities(non_oriente, weight="poids", seed=0)
    communaute = {n: i for i, c in enumerate(sorted(communautes, key=len, reverse=True))
                  for n in c}
    return pd.DataFrame({
        "club": list(g.nodes),
        "ligue1": [g.nodes[n]["ligue1"] for n in g.nodes],
        "pagerank": [pagerank[n] for n in g.nodes],
        "departs": [g.out_degree(n, weight="poids") for n in g.nodes],
        "arrivees": [g.in_degree(n, weight="poids") for n in g.nodes],
        "intermediarite": [intermediarite[n] for n in g.nodes],
        "communaute": [communaute[n] for n in g.nodes],
    }).sort_values("pagerank", ascending=False).reset_index(drop=True)


def positions(g: nx.DiGraph, noeuds: list[str], seed: int = 7) -> dict:
    """Coordonnées 2D (force-directed) pour dessiner un sous-graphe."""
    sous = g.subgraph(noeuds).to_undirected()
    depart = nx.spring_layout(sous, seed=seed)
    return nx.kamada_kawai_layout(sous, pos=depart)  # écarte mieux les nœuds que spring

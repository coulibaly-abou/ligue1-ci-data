# Plateforme d'analyse de la Ligue 1 ivoirienne

Pipeline de données complet sur 10 saisons de MTN Ligue 1 (2016 → 2026) : collecte web,
MongoDB, PostgreSQL, réseau des clubs, six modèles de prédiction (dont un réseau de neurones
PyTorch) et tableau de bord Streamlit.

![Architecture](docs/figures/00_architecture.png)

**Démo** : _lien Streamlit Community Cloud à ajouter après déploiement_ ·
**Rapport** : [docs/rapport.pdf](docs/rapport.pdf) (9 pages)

## Résultats

| | |
|---|---|
| Matchs collectés | 1 934 matchs joués, 10 saisons complètes + 2026-27 en cours |
| Nuls | 30 % des matchs (≈ 25 % en Europe), 2,06 buts par match |
| Domination | ASEC Mimosas : 6 titres sur 10, club le plus central du réseau des transferts |

Prédiction du résultat (victoire domicile / nul / victoire extérieur). Validation temporelle
glissante : chaque saison 2021-22 → 2025-26 est prédite par un modèle entraîné uniquement
sur les saisons précédentes (1 141 matchs prédits).

| Modèle | Précision | Log-loss |
|---|---|---|
| **Elo** (retenu) | **43,7 %** | **1,0715** |
| Régression logistique | 42,6 % | 1,0732 |
| Forêt aléatoire | 42,3 % | 1,0779 |
| Réseau de neurones (MLP PyTorch) | 42,6 % | 1,0792 |
| Gradient boosting | 41,3 % | 1,0838 |
| Référence naïve (toujours domicile) | 35,4 % | 1,0974 |

Tous les modèles battent la référence naïve de façon significative (bootstrap, IC 95 %).
Le modèle simple fondé sur l'Elo fait aussi bien que les modèles complexes : avec ≈ 240
matchs par saison et 30 % de nuls, la qualité de l'évaluation compte plus que l'algorithme.
Détails : page **Modèles** du tableau de bord, [notebooks/02_modelisation.ipynb](notebooks/02_modelisation.ipynb).

![Modèles](docs/figures/06_comparaison_modeles.png)

## Installation

```bash
cp .env.example .env
docker compose up -d
pip install -e ".[dev,modele]"
```

## Pipeline

```bash
make collect   # collecte web + API (≈ 1 min hors API ; reprise automatique du quota API)
make etl       # MongoDB -> PostgreSQL, contrôles, vues matérialisées
make train     # réglages, validation glissante, test 2025-26, modèle final (≈ 5 min)
make export    # données du tableau de bord : app/data/*.parquet
make rapport   # figures (docs/figures) + rapport PDF (docs/rapport.pdf)
make app       # tableau de bord en local : http://localhost:8501
make pipeline  # collect + etl + train + export
```

Sources (RSSSF, Wikipédia, Futbol24, API-Football) et limites : [docs/sources.md](docs/sources.md).
Modèle de données (Merise : MCD, MLD, MPD) : [docs/modele_donnees.md](docs/modele_donnees.md).

### Collecte quotidienne (Windows)

La tâche planifiée « Ligue1CI - collecte quotidienne » lance
`scripts/collecte_quotidienne.bat` chaque jour à 8 h (ou au prochain démarrage du PC).
API-Football (offre gratuite : 100 requêtes/jour) reprend là où elle s'était arrêtée.
Journal : `logs/collecte_quotidienne.log` et `logs/pipeline.log`.

## Ce que fait chaque base

| Base | Rôle |
|---|---|
| MongoDB | zone brute : HTML archivé (URL, date, SHA-256) et documents tels que collectés, par source |
| PostgreSQL | zone analytique : 13 tables normalisées, 157 écritures de noms harmonisées en 31 clubs, scores recoupés entre sources, classements recalculés identiques aux officiels ; 10 requêtes dans [sql/analyses/](sql/analyses/), vues matérialisées dans [sql/vues_materialisees.sql](sql/vues_materialisees.sql) |
| Graphe | carrières Wikipédia + transferts API-Football : PageRank, intermédiarité, communautés de Louvain ([src/graphe/analyses.py](src/graphe/analyses.py)) ; calculé avec networkx pour le tableau de bord. **À faire** : chargement dans Neo4j et 5 requêtes Cypher ([cypher/](cypher/) encore vide) |

## Modélisation

- **Variables** ([src/modele/features.py](src/modele/features.py)), calculées uniquement avec
  l'information disponible avant chaque match : Elo (K et avantage du terrain réglés en
  validation), forme sur 5 et 10 matchs, buts glissants, points, rang et différence de
  buts dans la saison, forme à domicile / à l'extérieur, jours de repos.
- **Modèles** : référence naïve, Elo, régression logistique multinomiale, forêt aléatoire,
  gradient boosting ([baselines.py](src/modele/baselines.py)) et MLP PyTorch avec dropout,
  pénalité L2, arrêt anticipé et moyenne de 5 graines ([reseau.py](src/modele/reseau.py)).
- **Évaluation** ([evaluation.py](src/modele/evaluation.py)) : précision, log-loss, Brier,
  RPS, matrice de confusion, calibration, importance par permutation, bootstrap apparié.
- **Choix du modèle** : le plus simple parmi ceux à moins de 0,002 de log-loss du meilleur
  sur 2021 → 2024 ; test final sur 2025-26, jamais utilisé pour un choix.

## Tableau de bord et déploiement

`app/` (Streamlit, 6 pages : Accueil, Championnat, Club, Réseau, Prédiction, Modèles) ne lit
que `app/data/*.parquet` : il se déploie sans base de données.

1. Pousser le dépôt sur GitHub (avec `app/data/`).
2. Sur [share.streamlit.io](https://share.streamlit.io) : *Create app* → dépôt, branche
   `main`, fichier `app/Accueil.py`. Les dépendances légères sont dans
   [app/requirements.txt](app/requirements.txt).
3. Après chaque mise à jour des données : `make pipeline` puis commit de `app/data/` ;
   l'application se met à jour toute seule.

## Limites

- ≈ 240 matchs par saison : les écarts entre modèles sont du même ordre que l'incertitude
  d'une saison.
- Aucune source légale ne publie les buteurs et cartons match par match avant 2022.
- Le réseau ne suit que les joueurs ayant un article Wikipédia (biais vers les grands clubs).
- 2019-20 (arrêt Covid) et 2020-21 (poules + play-off) : classements recalculés approximatifs.

## Valorisation

Post LinkedIn, script de la vidéo, diapositives et vidéo MP4 : [docs/linkedin/](docs/linkedin/).

Sources : RSSSF © José Batalha / Rec.Sport.Soccer Statistics Foundation ; Wikipédia (CC BY-SA) ;
Futbol24 ; API-Football.

# Sources de données — audit du 6 octobre 2026

Réponse à la question ouverte du cahier des charges : *quels sites sources, et couvrent-ils
les effectifs et transferts ?*

## Sources retenues

| Source | Données | Couverture | Collections MongoDB |
|---|---|---|---|
| [RSSSF](https://rsssf.org/tablesi/ivo2025.html) | Tous les matchs (journée, date, score, forfaits, matchs arrêtés), classements | 2016-17 → 2025-26 | `raw_matches`, `raw_standings` |
| [Wikipédia FR](https://fr.wikipedia.org/wiki/Championnat_de_C%C3%B4te_d%27Ivoire_de_football_2026-2027) — saisons | Stades, buteurs, classement, grille des résultats (dont matchs restant à jouer) | 2016-17 → 2026-27, inégal | `raw_clubs`, `raw_scorers`, `raw_standings`, `raw_matches`, `raw_fixtures` |
| [Wikipédia EN](https://en.wikipedia.org/wiki/2024%E2%80%9325_Ligue_1_(Ivory_Coast)) — saisons | Stades, buteurs | 6 saisons | `raw_clubs`, `raw_scorers` |
| Wikipédia EN + FR — joueurs et entraîneurs | Identité, parcours daté club par club, prêts, matchs/buts, sélections, carrière d'entraîneur | ~460 personnes | `raw_persons` |
| [Futbol24](https://www.futbol24.com/fr/national/Ivory-Coast/Ligue-1/2026-2027/calendrier) | Résultats datés et prochains matchs avec horaire | saison en cours seulement | `raw_matches`, `raw_fixtures` |

Le HTML complet de chaque page est archivé dans `raw_pages` (URL, date, empreinte SHA-256),
ce qui permet de re-parser sans re-télécharger. Les fiches joueurs ne sont
re-téléchargées qu'une fois par mois (cache).

Chaque document garde sa `source` : quand deux sources donnent la même information
(ex. RSSSF et la grille Wikipédia), les deux sont conservées et l'ETL choisit / recoupe.

### Volume collecté (6 octobre 2026)

| Collection | Documents | Détail |
|---|---|---|
| `raw_matches` | 2 873 | RSSSF 1 930 · grilles Wikipédia 930 · Futbol24 13 |
| `raw_fixtures` | 331 | 229 matchs 2026-27 à jouer (Wikipédia) · prochains matchs datés (Futbol24) · 49 matchs jamais joués de 2019-20 |
| `raw_standings` | 469 | RSSSF 301 · Wikipédia 168 |
| `raw_clubs` | 143 | stades et villes, 9 saisons sur 11 |
| `raw_scorers` | 52 | top buteurs, 7 saisons sur 11 |
| `raw_persons` | 627 fiches (~460 personnes) | 5 460 passages en club dont 1 774 touchant 2016+, 410 prêts, 18 entraîneurs |
| `raw_pages` | 694 | HTML brut |

### Matchs par saison (RSSSF)

| Saison | Matchs | Format |
|---|---|---|
| 2016-2017 | 182 | 14 clubs |
| 2017-2018 | 183 | 14 clubs |
| 2018-2019 | 182 | 14 clubs |
| 2019-2020 | 140 | 14 clubs, **arrêtée (Covid)** |
| 2020-2021 | 97 | **2 poules de 7 + play-off à 4** |
| 2021-2022 | 183 | 14 clubs |
| 2022-2023 | 242 | 16 clubs (play-off annulé) |
| 2023-2024 | 241 | 16 clubs |
| 2024-2025 | 240 | 16 clubs |
| 2025-2026 | 240 | 16 clubs |
| 2026-2027 | en cours | Wikipédia + Futbol24 (RSSSF pas encore publié) |

## Sources examinées et écartées

| Source | Résultat du test | Raison |
|---|---|---|
| Soccerway / Flashscore | Tout (effectifs, buteurs, cartons) via une API interne signée | **CGU : scraping interdit** (art. 2.9 et 2.10) |
| Transfermarkt | Seuls ASEC et Stade d'Abidjan ont un effectif | Championnat ivoirien non suivi |
| Wikidata (SPARQL, API) | 375 joueurs, peu de dates côté clubs ivoiriens | `robots.txt` interdit `/sparql` et `/w/api.php` |
| Futbol24 — détail des matchs | Buteurs/cartons chargés via `/api/` | `robots.txt` interdit `/api/` |
| footballdatabase.com | HTTP 503 ; robots.txt impose 30 s entre requêtes | Indisponible lors du test — à retester |
| soccer365.net | Connexion fermée par le serveur | Inaccessible |
| Sofascore, Eurosport, Foot-Africa, WorldFootball | HTTP 403 (anti-robot) | Accès refusé |
| fif.ci (fédération) | HTTP 521 | Hors ligne |
| news.abidjan.net (presse) | Scores et classements en texte libre, buteurs rarement | Format trop irrégulier pour une collecte fiable |

## Ce qui reste non couvert

- **Buteurs et cartons match par match** : aucune source légale et exploitable.
  `fact_but` se limitera aux totaux par joueur et par saison (top 5-10).
- **Effectifs complets par saison** : `raw_persons` ne contient que les joueurs qui ont
  un article Wikipédia (surtout ASEC, Africa Sports, joueurs partis à l'étranger).
  Le graphe Neo4j sera donc **biaisé vers les grands clubs** : à mentionner dans le rapport.
- **Entraîneurs** : 18 fiches seulement (ASEC, Africa Sports), plus les carrières
  d'entraîneur présentes dans les fiches de joueurs.
- **Dates des matchs futurs** : publiées seulement journée par journée ; la collecte
  hebdomadaire les récupère au fil de la saison.

## Respect des sites

- `robots.txt` vérifié avant chaque requête (`src/collecte/scrapers/http.py`) ;
- pause de 2 s entre deux requêtes ; User-Agent identifiant le projet ;
- sources dont les CGU interdisent le scraping écartées (Soccerway) ;
- sources citées : RSSSF © José Batalha / Rec.Sport.Soccer Statistics Foundation ;
  Wikipédia sous licence CC BY-SA ; Futbol24.

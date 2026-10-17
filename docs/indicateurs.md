# Indicateurs — définitions, calculs et limites

Chaque valeur du tableau de bord est soit **brute** (lue dans une source), soit **calculée**
(dérivée des données brutes par le code cité). Les calculs du tableau de bord sont dans
[app/indicateurs.py](../app/indicateurs.py) et testés dans
[tests/test_indicateurs.py](../tests/test_indicateurs.py) ; la note des joueurs dans
[src/restitution/joueurs.py](../src/restitution/joueurs.py), testée dans
[tests/test_joueurs.py](../tests/test_joueurs.py).

Règle générale : **une donnée absente n'est jamais remplacée par 0**. Une moyenne sur
zéro match vaut « — » ; une statistique non publiée est affichée « Non publié ».

## Matchs et bilans (2016-17 → saison en cours)

| Indicateur | Type | Définition et calcul | Dénominateur / période |
|---|---|---|---|
| Score | brut | Score final RSSSF (saisons terminées), Wikipédia ou Futbol24 (saison en cours), recoupé entre sources | — |
| Victoires, nuls, défaites | calculé | Issue du match vue par le club (`mv_resultat_club`) | matchs joués de la sélection |
| Points | calculé | 3 par victoire, 1 par nul, 0 par défaite | — |
| Points par match | calculé | points ÷ matchs joués | matchs de la sélection (filtres saison, lieu, période) |
| Buts marqués / encaissés par match | calculé | somme des buts ÷ matchs joués | idem |
| Différence de buts | calculé | buts marqués − buts encaissés | idem |
| Matchs sans encaisser / sans marquer | calculé | nombre de matchs avec 0 but encaissé / marqué | idem |
| Classement | calculé | tri par points, puis différence de buts, puis buts marqués, sur les matchs de la sélection | une saison ; avec un filtre lieu ou période, c'est un classement *de la sélection* |
| Forme | brut | issues des 5 derniers matchs de la sélection | 5 matchs |
| Tendance | calculé | points/match des 5 derniers matchs − points/match des matchs précédents | affichée seulement si la sélection compte ≥ 10 matchs ; descriptive, pas un test |
| Bilan par adversaire | calculé | bilan restreint aux matchs contre chaque adversaire | souvent 2 à 20 matchs : historique, pas mesure de niveau |
| Matchs à venir | brut | calendrier Wikipédia, dates confirmées Futbol24 | dates non confirmées en fin de liste |
| Probabilités d'un match | calculé | modèle Elo retenu en validation glissante (voir README, Modélisation) | — |

**Contrôle (17/10/2026)** : les bilans recalculés (J, V, N, D, BP, BC, Pts) ont été
comparés aux classements finaux officiels RSSSF de la saison régulière : **229 sur 254
identiques (90 %)**. Les 25 écarts (2016-17, 2018-19, 2021-22, 2022-23, 2023-24) viennent
de matchs absents des sources, de décisions sur tapis vert exclues du calcul et de scores
divergents entre sources. Le champion affiché vient toujours du classement officiel.

## Déroulé des matchs (2022-23 → 2024-25, API-Football)

| Indicateur | Type | Définition |
|---|---|---|
| Buteur, minute, type de but | brut | évènements API-Football ; minute = temps réglementaire + temps additionnel |
| Score après chaque but | calculé | cumul des buts dans l'ordre des minutes ; un contre-son-camp est crédité à l'équipe qui en bénéficie (comme dans l'API) |
| Déroulé complet | calculé | vrai si le déroulé redonne exactement le score final (98,6 % des matchs avec évènements) |
| But décisif | calculé | but qui égalise ou donne l'avantage (écart avant le but de −1 ou 0) ; calculé seulement sur les déroulés complets |
| Buts par quart d'heure | calculé | 0-15, 16-30, 31-45+ (temps additionnel compris), 46-60, 61-75, 76-90+ |

Couverture : 81 % des buts de 2022-23, 68 % en 2023-24, 45 % en 2024-25 ; 23 % des buts
publiés n'ont pas de nom de buteur. Seuls les cartons rouges sont publiés de façon fiable.

## Note de contribution offensive sur 10 (calculée, non officielle)

Pour chaque buteur d'une saison :

```
note = 10 × (0,35 × rang(buts) + 0,25 × rang(buts décisifs)
             + 0,20 × rang(part des buts du club) + 0,20 × rang(matchs avec un but))
       − 0,5 × cartons rouges                       bornée entre 0 et 10
```

- `rang(x)` est le **rang-centile** du joueur parmi les buteurs de la même saison
  (ex aequo : rang moyen), entre 0 et 1. La note compare donc un joueur à ses pairs : elle
  n'est pas comparable d'une saison à l'autre au sens absolu.
- **Part des buts du club** = buts du joueur ÷ buts du club *sur toute la saison* (RSSSF) :
  le dénominateur inclut les matchs sans déroulé publié, la part est donc minorée quand la
  couverture est faible (2024-25).
- La page Joueurs décompose chaque note critère par critère (« Pourquoi cette note ? »).
- **Données insuffisantes** : sous 3 buts (83 % des buteurs), la note est signalée comme
  indicative ; un filtre permet de n'afficher que les notes fiables.

Limites assumées :

- API-Football ne publie pour ce championnat **ni temps de jeu, ni titularisations, ni
  passes décisives, ni actions défensives**. La note ne peut donc pas être adaptée au poste :
  elle ne concerne que la contribution offensive des buteurs, et un défenseur ou un
  gardien n'en a pas. Avec ces données, il suffirait d'ajouter des critères par poste
  (ex. buts encaissés par 90 minutes pour un gardien) dans `notes_joueurs`.
- Un joueur est identifié par son id API-Football quand il est publié (13 % des buts),
  sinon par « nom abrégé + club » : deux homonymes du même club seraient confondus, et un
  joueur transféré en cours de saison compte comme deux joueurs.
- Profils (poste, âge, nationalité) : retrouvés dans les effectifs API-Football pour
  environ 20 % des buteurs ; les autres sont « Non renseigné ».

## Zones d'activité

Aucune source accessible ne publie de coordonnées d'évènements (tirs, passes, positions)
pour la Ligue 1 ivoirienne. **Aucune carte de chaleur n'est affichée** ; la page Joueurs
montre à la place la répartition des buts par quart d'heure. Pour activer une vraie
visualisation sur terrain, il faut une source d'évènements avec coordonnées (par exemple
une offre payante de fournisseur de données si elle couvre ce championnat) : ajouter un
collecteur dans `src/collecte/scrapers/`, une table d'évènements avec `x`, `y` dans
`sql/schema.sql`, puis tracer le terrain avec Plotly (formes `layout.shapes`).

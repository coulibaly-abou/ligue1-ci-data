# Spécifications et conformité au projet de référence

**Référence** : post LinkedIn de Paul Senecaut (octobre 2026) présentant un tableau de bord du
LOSC alimenté par l'API Sportmonks.

**Ce qui a été consulté** : le texte public du post et le résumé des commentaires. Les
captures d'écran, la vidéo et le site lui-même n'étaient pas accessibles sans compte
LinkedIn : la mise en page de la référence n'a donc **pas** été vue. Les fonctionnalités
« confirmées » ci-dessous sont celles que le texte du post décrit. Les autres viennent du
cahier des charges du projet et sont marquées « proposée ».

**Adaptation** : la référence couvre un club de Ligue 1 française avec une API payante. Ce
projet couvre **toute la Ligue 1 ivoirienne** (31 clubs, 2016 → 2026) avec des sources
gratuites. Le tableau de bord club (page Clubs) joue le rôle du tableau de bord LOSC pour
n'importe quel club, avec un sélecteur.

Statuts : ✅ réalisé · 🟡 partiel (données limitées) · ⛔ impossible avec les sources
accessibles (remplacement honnête en place).

| # | Fonctionnalité attendue | Origine | Implémentation | Preuve de vérification | Statut |
|---|---|---|---|---|---|
| 1 | Résultats et listes de matchs | confirmée | Clubs (tableau des matchs cliquable), Matchs, Championnat | AppTest de toutes les pages ; capture `docs/captures/Club.png` | ✅ |
| 2 | Statistiques d'équipe | confirmée | Clubs : bilan V/N/D, points, différence, moyennes, classement | `test_bilan`, `test_classement` ; bilans recoupés avec 254 classements officiels (229 identiques, écarts expliqués dans `docs/indicateurs.md`) | ✅ |
| 3 | Analyse attaque / défense par saison | confirmée | Attaque & Défense : quadrant, tableau, évolution, domicile/extérieur, par quart d'heure | AppTest ; capture `attaque_defense.png` | ✅ |
| 4 | Tirs, tirs cadrés, xG | proposée | non publiés pour ce championnat : affichés comme absents, jamais à 0 | légende de la page, `docs/sources.md` | ⛔ |
| 5 | Fiches joueurs | confirmée | Joueurs : fiche, profil, buts match par match avec lien vers le match, buts cumulés | AppTest avec `?joueur=` ; capture `joueurs.png` | ✅ |
| 6 | Note sur 10 (temps de jeu + performance) | confirmée | note de contribution offensive : 4 critères pondérés, rang-centile par saison, décomposition « Pourquoi cette note ? », mention « indicative » sous 3 buts | `test_notes_joueurs`, `test_poids_identiques_au_calcul_de_la_note` ; top 12 vérifiés à la main (meilleurs buteurs de chaque saison en tête) | 🟡 temps de jeu non publié |
| 7 | Note adaptée au poste | proposée | impossible sans temps de jeu ni actions défensives ; filtre par poste disponible | `docs/indicateurs.md` (limites) | ⛔ |
| 8 | Zones d'activité estimées | confirmée | aucune coordonnée publiée : pas de carte inventée ; remplacée par « Quand marque-t-il ? » (buts par quart d'heure) ; marche à suivre pour activer documentée | `docs/indicateurs.md`, section Zones d'activité | ⛔ remplacement |
| 9 | Détail des matchs : évènements | confirmée | Matchs : chronologie des buts et cartons rouges, score après chaque but, but décisif, écart au score | `test_derouler_buts_*` ; 98,6 % des déroulés redonnent le score final | 🟡 2022-23 → 2024-25 |
| 10 | Détail des matchs : compositions, statistiques | confirmée | onglet Statistiques : buts, penalties, cartons rouges ; possession, tirs, corners, compositions marqués « Non publié » | AppTest : `Possession → Non publié` | ⛔ remplacement |
| 11 | Match précédent / suivant | proposée | boutons dans la saison, ou parmi les matchs du club filtré | `test_voisins_et_prochains` ; interaction testée (1000 → 1001 → 1000) | ✅ |
| 12 | Alimentation automatique par API | confirmée | collecte quotidienne (tâche planifiée + GitHub Actions), cache MongoDB, quota API-Football, reprise automatique | `scripts/collecte_quotidienne.bat`, `.github/workflows/collecte.yml` | ✅ |
| 13 | Requêtes et transformations | confirmée | ETL MongoDB → PostgreSQL, contrôles d'anomalies, 10 requêtes SQL, vues matérialisées | `tests/test_nettoyage.py`, `logs/anomalies_etl.csv` | ✅ |
| 14 | Site interactif : graphiques, survols, filtres | confirmée | Plotly (infobulles sur tous les graphiques), filtres saison / lieu / période / club / poste / fiabilité, tris des tableaux | test d'interactions : le filtre Domicile fait passer le bilan ASEC 2025-26 de 30 à 15 matchs | ✅ |
| 15 | Profils joueurs avec filtres | confirmée | filtres saison, club, poste, notes fiables, recherche ; comparaison de deux joueurs | interactions testées (140 → 28 → 3 → 13 joueurs) | ✅ |
| 16 | Recherche globale joueur / club | proposée | champ « Rechercher » dans la barre latérale, liens vers les fiches | interaction testée (`kante` → 2 fiches, `asec` → 1 club) | ✅ |
| 17 | Filtres actifs visibles et remise à zéro | proposée | puces « Filtres actifs » ; bouton Réinitialiser (Clubs) | interaction testée (retour à 30 matchs, lieu Tous) | ✅ |
| 18 | Filtre par compétition | proposée | un seul championnat collecté ; phases harmonisées (saison régulière, poules, play-off) et affichées sur chaque match | `test_phase` | 🟡 |
| 19 | Prochains matchs | proposée | Clubs : 5 prochains matchs avec probabilités du modèle Elo | capture `Club.png` | ✅ |
| 20 | Photos officielles des joueurs | proposée | non utilisées (droits non vérifiés) : pastilles aux initiales, aux couleurs du club | — | ⛔ choix |
| 21 | États vides et erreurs | proposée | messages « Aucun match… », « Déroulé non disponible… », « Données insuffisantes » | AppTest sur des matchs sans déroulé (`?match=5`) | ✅ |
| 22 | Mode sans clé API | proposée | l'application ne lit que `app/data/*.parquet` (données réelles exportées, versionnées) : aucune clé ni base nécessaire pour la lancer | lancement local sans bases | ✅ |
| 23 | Responsive | proposée | mise en page Streamlit + règles CSS pour téléphones (`commun.py`) | non vérifié sur appareil réel | 🟡 |

## Critères d'acceptation retenus

- Chaque indicateur affiché provient de `app/data/` et a une définition dans
  `docs/indicateurs.md`.
- Tout filtre visible modifie les chiffres affichés (vérifié par le test d'interactions).
- Aucune statistique non publiée n'est affichée comme un zéro.
- `pytest` et `ruff check .` passent ; les 10 pages s'exécutent sans exception (AppTest).

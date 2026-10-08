# Vidéo LinkedIn — scénario, voix off et captures

**Fichier** : `docs/linkedin/video_ligue1.mp4` — 1920×1080, 25 images/s, **1 min 26 s**,
muette (ajouter la voix off ci-dessous et, si souhaité, une musique discrète).

**Régénérer** (le site doit tourner sur le port 8599) :

```bash
streamlit run app/Accueil.py --server.port 8599
python -m src.restitution.video                # recapture le site puis monte la vidéo
python -m src.restitution.video --reutiliser   # remonte sans recapturer
```

Tous les chiffres à l'écran sont lus dans les résultats du projet (`app/data/`).

## Scénario et voix off

Ton : professionnel, dynamique, naturel — environ 2,5 mots par seconde.

| # | Temps | À l'écran | Voix off |
|---|---|---|---|
| 1 | 0:00 – 0:06 | **COULIBALY ABOUBAKAR — Data Scientist**, puis « Ligue 1 Côte d'Ivoire — Data Science & Machine Learning » | « Bonjour, je suis Aboubakar Coulibaly, Data Scientist. Voici mon projet sur la Ligue 1 ivoirienne. » |
| 2 | 0:06 – 0:17 | Carte de la Côte d'Ivoire : les 17 villes et 31 clubs apparaissent un à un, Abidjan en dernier | « Le championnat ivoirien forme des talents pour toute l'Afrique et l'Europe, mais ses données sont dispersées. J'ai commencé par les rassembler : 31 clubs, 17 villes, dix saisons. » |
| 3 | 0:17 – 0:26 | **Objectifs de l'étude** : six objectifs apparaissent un par un | « L'objectif : analyser les performances des clubs, comprendre les dynamiques du championnat, et tester jusqu'où on peut prédire le résultat d'un match. » |
| 3b | 0:26 – 0:39 | **Collecte et bases de données** : les cinq étapes apparaissent une à une (4 sources web → 711 pages collectées → MongoDB, 2 873 matchs bruts → ETL, 11 écarts de score signalés, 102 noms → 31 clubs → PostgreSQL, 1 934 matchs, 12 tables, 10 requêtes SQL), puis la page Données & Méthodologie et son tableau de volumes | « Tout commence par la collecte : quatre sources web, plus de 700 pages archivées dans MongoDB avec leur date et leur source. Un ETL recoupe ensuite les scores et harmonise les noms des clubs, avant de tout charger dans PostgreSQL : 1 934 matchs prêts à être analysés. » |
| 4a | 0:39 – 0:45 | Page Championnat : classement recalculé, cadre sur l'évolution du rang | « Viennent ensuite les analyses : classements journée par journée… » |
| 4b | 0:45 – 0:50 | Rang final de chaque club, saison après saison | « …hiérarchie sur dix saisons… » |
| 4c | 0:50 – 0:56 | Page Clubs : bilan de l'ASEC Mimosas | « …et bilan complet de chaque club. » |
| 5 | 0:56 – 1:08 | **Machine Learning** + les cinq modèles, puis la page Modèles et son tableau | « J'ai ensuite comparé six modèles, de la référence naïve au réseau de neurones, en prédisant chaque saison uniquement avec les précédentes. Résultat : un simple modèle Elo fait aussi bien que le réseau de neurones, avec 43,7 % de bons pronostics contre 35,4 % pour la référence. » |
| 6 | 1:08 – 1:18 | Page Prédiction : ASEC Mimosas – AFAD Djékanou, 42 % / 31 % / 27 % | « Pour chaque match à venir, l'application donne trois probabilités. Ici, ASEC Mimosas contre AFAD Djékanou : 42 % de victoire à domicile. » |
| 7 | 1:18 – 1:26 | « Data → Analyse → Modélisation → Prédiction », puis l'identité | « De la donnée brute à la prédiction, tout est en ligne. Le lien est en commentaire. » |

Les chiffres des scènes 3b, 5 et 6 sont ceux des fichiers de résultats au moment du
montage : si le pipeline est relancé, relire les valeurs à l'écran avant d'enregistrer
la voix.

## Captures utilisées

| Fichier | Contenu | Scène |
|---|---|---|
| `captures_hd/carte/carte_00.png` → `carte_17.png` | carte avec 0 à 17 villes (apparition progressive) | 2 |
| `captures_hd/methodologie.png` | page Données & Méthodologie (volumes MongoDB) | 3b |
| `captures_hd/championnat.png` | page Championnat complète (1600 px, ×1,5) | 4a, 4b |
| `captures_hd/club.png` | page Clubs (ASEC Mimosas) | 4c |
| `captures_hd/modeles.png` | page Modèles | 5 |
| `captures_hd/prediction.png` | page Prédiction (affiche par défaut ASEC – AFAD) | 6 |
| `captures_hd/accueil.png` | page d'accueil, en fond flouté | 7 |
| `diapos/*.png` | une image clé par scène (vignette, miniature, Canva) | — |

## Monter une version avec voix dans Canva

1. Créer un design « Vidéo » 1920×1080 et importer `video_ligue1.mp4`.
2. Enregistrer la voix off scène par scène (bouton « Enregistrer ») en suivant le tableau.
3. Ajouter des sous-titres (beaucoup de personnes regardent sans le son sur LinkedIn).
4. Exporter en MP4 1080p.

Variante plus vivante : remplacer la scène 6 par un enregistrement d'écran de 10 s
(Windows : `Win + Alt + R`) où l'on choisit une affiche dans le simulateur de la page
Prédiction.

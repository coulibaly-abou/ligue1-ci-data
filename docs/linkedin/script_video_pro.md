# Vidéo LinkedIn narrée : scénario, voix off et sous-titres

**Fichier** : `docs/linkedin/video_ligue1_pro.mp4` (1920×1080, 25 images/s, H.264 + AAC 192 kb/s),
environ 90 s. Sous-titres incrustés, et fournis à part dans `video_ligue1_pro.srt`.
La vidéo muette d'origine (`video_ligue1.mp4`, générée par `src/restitution/video.py`) est conservée.

**Générer** : voir la section « Vidéo de présentation narrée » du README.
Le texte prononcé et les sous-titres sont dans `NARRATION` ([video_pro.py](../../src/restitution/video_pro.py)).
La durée de chaque séquence suit la longueur de sa narration.

## Séquences

| # | À l'écran | Narration (sous-titres) |
|---|---|---|
| 1. Profil | Nom, « Data Science • Statistique • Machine Learning », BUT 3 SD parcours EMS, recherche de stage et d'alternance | « Aboubakar Coulibaly, étudiant en BUT 3 Science des Données, parcours Exploration et Modélisation Statistique. Il recherche un stage et une alternance en Data Science. » |
| 2. Contexte | Carte : les 17 villes et 31 clubs apparaissent ; « Un championnat formateur… aux données dispersées » | « La Ligue 1 ivoirienne forme des joueurs pour l'Afrique et l'Europe. Pourtant, ses données sont dispersées et presque jamais analysées. Ce projet rassemble dix saisons : 31 clubs, répartis dans 17 villes. » |
| 3. Problématique et objectifs | La question de départ, puis l'objectif général et les 4 objectifs spécifiques | « Problématique : que révèlent les données publiques sur ce championnat ? Et peut-on prédire un match mieux qu'une règle naïve ? Quatre objectifs : constituer une base fiable, analyser les performances des clubs, étudier le réseau des mouvements de joueurs, et comparer six modèles de prédiction. » |
| 4. Données et méthodes | Chaîne Sources → Collecte → MongoDB → ETL → PostgreSQL (volumes réels), puis les 6 familles de méthodes | « Quatre sources web sont collectées en Python et archivées dans MongoDB. Un ETL recoupe les scores et harmonise 102 noms en 31 clubs : 1 934 matchs dans PostgreSQL. Méthodes : requêtes SQL, analyse de réseau, et Machine Learning en validation temporelle. » |
| 5a. Observations | Tuiles 30 % de nuls · 2,06 buts par match · 6/10 titres ASEC · 42 % des départs depuis l'ASEC (« constats observés, pas des liens de cause à effet »), puis la page Championnat du site | « Premiers constats : 30 % de matchs nuls, à peine 2 buts par match, et 6 titres sur 10 pour l'ASEC Mimosas. » |
| 5b. Modélisation | Barres : part de bons pronostics des 6 modèles (axe à partir de 0) ; encadré « Établi / Non établi » | « Chaque saison est prédite avec les seules saisons précédentes : 1 141 matchs. Un simple modèle Elo atteint 43,7 % de bons pronostics, contre 35,4 % pour la référence naïve. Le gain est significatif, mais les modèles restent trop proches pour être départagés. » |
| 5c. Prédiction | Page Prédiction du site + carte ASEC Mimosas – AFAD Djékanou (42 / 31 / 27 %) | « L'application Streamlit donne ensuite les probabilités de chaque match à venir. » |
| 6. Conclusion | Collecte → Bases → Analyse → Modélisation → Application, compétences, nom, « Recherche de stage et d'alternance », liens GitHub et LinkedIn | « De la collecte web au Machine Learning : un projet complet. Aboubakar Coulibaly recherche un stage et une alternance. » |

## Ce que la vidéo affirme, et ce qu'elle n'affirme pas

- **Observations** (statistique descriptive sur 1 934 matchs) : part de nuls, buts par match, palmarès, départs. Aucun lien de cause à effet n'est présenté.
- **Établi** : en validation glissante (1 141 matchs), les 5 modèles battent la référence naïve. L'intervalle de confiance à 95 % du bootstrap apparié sur la log-loss est entièrement sous 0.
- **Non établi** : une hiérarchie entre les modèles. Sur la seule saison test 2025-26, Elo fait 39,2 % contre 33,8 %, un écart non significatif.

Le script s'arrête avant le montage si l'un de ces chiffres ou de ces conclusions ne correspond plus aux résultats (`verifier_narration`).

## Voix off

La voix de synthèse (« Paul », Windows) parle à la troisième personne : elle ne se fait pas passer pour vous.
Pour une version avec votre propre voix :

1. `python -m src.restitution.video_pro --sans-voix` produit `video_ligue1_pro_sans_voix.mp4` (musique et sous-titres, mêmes minutages).
2. Dans Canva ou CapCut, enregistrez le texte du tableau ci-dessus, à la première personne si vous le souhaitez, en suivant les sous-titres.

## Publication LinkedIn

- Importer `video_ligue1_pro.mp4`, puis ajouter `video_ligue1_pro.srt` comme fichier de sous-titres. Les sous-titres sont aussi incrustés dans l'image : la vidéo reste lisible sans le son.
- Miniature conseillée : `diapos_pro/01_profil.png` ou `diapos_pro/05b_modeles.png`.

# Script de la vidéo LinkedIn (≈ 80 s)

La vidéo `video_ligue1.mp4` est une première version muette, générée automatiquement
(`python -m src.restitution.video`). Les 13 diapositives sont aussi disponibles en PNG
1920×1080 dans `docs/linkedin/diapos/` : on peut les importer dans **Canva**
(Créer un design → Vidéo 1920×1080 → Importer), y ajouter la voix off, une musique et
des transitions, puis exporter en MP4.

Conseils LinkedIn : sous-titres incrutés (beaucoup regardent sans le son), les 3
premières secondes doivent accrocher, moins de 90 s, format 16:9 ou 1:1.

| # | Diapo | Durée | Voix off |
|---|---|---|---|
| 1 | Accroche : le problème | 0:00 – 0:05 | « La Ligue 1 ivoirienne forme des talents pour toute l'Afrique et l'Europe… mais presque personne n'analyse ses données. J'ai construit la plateforme qui manquait. » |
| 2 | Pour qui ? | 0:05 – 0:12 | « Pour les clubs, qui mesurent enfin leur performance. Pour les recruteurs, qui découvrent les talents hors de l'ASEC. Pour les médias, et pour la Ligue. » |
| 3 | Chiffres clés | 0:12 – 0:18 | « Les données du championnat sont dispersées. J'ai collecté automatiquement dix saisons, près de 2 000 matchs, sur quatre sources. » |
| 4 | Architecture | 0:18 – 0:24 | « Le pipeline : collecte en Python, MongoDB pour les données brutes, PostgreSQL pour l'analyse, des modèles de machine learning, et un tableau de bord Streamlit. » |
| 5 | Résultats par saison | 0:24 – 0:31 | « Premier constat : un match sur trois se termine par un nul. C'est beaucoup plus qu'en Europe. » |
| 6 | Scores | 0:31 – 0:36 | « Et on marque peu : 1-1, 1-0, 0-0 et 0-1 représentent plus de la moitié des matchs. » |
| 7 | Elo | 0:36 – 0:42 | « J'ai recalculé le score Elo de chaque club après chaque match : l'ASEC Mimosas domine la décennie. » |
| 8 | Réseau | 0:42 – 0:49 | « Avec les carrières des joueurs, j'ai construit le réseau des transferts. L'ASEC est la plaque tournante vers l'Europe. » |
| 9 | Comparaison des modèles | 0:49 – 0:56 | « J'ai comparé six modèles, du plus simple au réseau de neurones, en prédisant chaque saison uniquement avec les saisons précédentes. » |
| 10 | Bootstrap | 0:56 – 1:02 | « Tous font mieux que le hasard. Mais sur une seule saison, l'incertitude est trop grande pour les départager. » |
| 11 | La leçon | 1:02 – 1:09 | « La leçon : un simple modèle Elo fait aussi bien qu'un réseau de neurones. Avec peu de données, la rigueur de l'évaluation compte plus que l'algorithme. » |
| 12 | Tableau de bord | 1:09 – 1:15 | « Tout est en ligne : classements, fiches clubs, réseau et probabilités des prochains matchs. » |
| 13 | Appel à l'action | 1:15 – 1:20 | « Le code, le rapport et la démo sont en commentaire. Et je cherche une alternance en data : parlons-en ! » |

## Idée de plan filmé (optionnel)

Remplacer la diapo 12 par un enregistrement d'écran de 10 s du tableau de bord
(Windows : `Win + Alt + R` avec la Xbox Game Bar) : choisir une affiche dans le
simulateur de la page Prédiction, puis faire défiler le réseau.

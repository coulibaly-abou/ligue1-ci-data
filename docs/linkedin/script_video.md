# Script de la vidéo LinkedIn (≈ 75 s)

La vidéo `video_ligue1.mp4` est une première version muette, générée automatiquement
(`python -m src.restitution.video`). Les 12 diapositives sont aussi disponibles en PNG
1920×1080 dans `docs/linkedin/diapos/` : on peut les importer dans **Canva**
(Créer un design → Vidéo 1920×1080 → Importer), y ajouter la voix off, une musique et
des transitions, puis exporter en MP4.

Conseils LinkedIn : sous-titres incrutés (beaucoup regardent sans le son), les 3
premières secondes doivent accrocher, moins de 90 s, format 16:9 ou 1:1.

| # | Diapo | Durée | Voix off |
|---|---|---|---|
| 1 | Accroche | 0:00 – 0:05 | « J'ai essayé de prédire les matchs de la Ligue 1 ivoirienne avec la data et l'intelligence artificielle. Voici ce que j'ai appris. » |
| 2 | Chiffres clés | 0:05 – 0:10 | « Les données du championnat sont dispersées. J'ai collecté automatiquement dix saisons, près de 2 000 matchs, sur quatre sources. » |
| 3 | Architecture | 0:10 – 0:16 | « Le pipeline : collecte en Python, MongoDB pour les données brutes, PostgreSQL pour l'analyse, des modèles de machine learning, et un tableau de bord Streamlit. » |
| 4 | Résultats par saison | 0:16 – 0:23 | « Premier constat : un match sur trois se termine par un nul. C'est beaucoup plus qu'en Europe. » |
| 5 | Scores | 0:23 – 0:28 | « Et on marque peu : 1-1, 1-0, 0-0 et 0-1 représentent plus de la moitié des matchs. » |
| 6 | Elo | 0:28 – 0:34 | « J'ai recalculé le score Elo de chaque club après chaque match : l'ASEC Mimosas domine la décennie. » |
| 7 | Réseau | 0:34 – 0:41 | « Avec les carrières des joueurs, j'ai construit le réseau des transferts. L'ASEC est la plaque tournante vers l'Europe. » |
| 8 | Comparaison des modèles | 0:41 – 0:48 | « J'ai comparé six modèles, du plus simple au réseau de neurones, en prédisant chaque saison uniquement avec les saisons précédentes. » |
| 9 | Bootstrap | 0:48 – 0:54 | « Tous font mieux que le hasard. Mais sur une seule saison, l'incertitude est trop grande pour les départager. » |
| 10 | La leçon | 0:54 – 1:01 | « La leçon : un simple modèle Elo fait aussi bien qu'un réseau de neurones. Avec peu de données, la rigueur de l'évaluation compte plus que l'algorithme. » |
| 11 | Tableau de bord | 1:01 – 1:07 | « Tout est en ligne : classements, fiches clubs, réseau et probabilités des prochains matchs. » |
| 12 | Appel à l'action | 1:07 – 1:12 | « Le code, le rapport et la démo sont en commentaire. Et je cherche une alternance en data : parlons-en ! » |

## Idée de plan filmé (optionnel)

Remplacer la diapo 11 par un enregistrement d'écran de 10 s du tableau de bord
(Windows : `Win + Alt + R` avec la Xbox Game Bar) : choisir une affiche dans le
simulateur de la page Prédiction, puis faire défiler le réseau.

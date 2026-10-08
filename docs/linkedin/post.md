# Post LinkedIn — à publier avec la vidéo `video_ligue1.mp4`

> Mettre le lien GitHub et le lien de la démo Streamlit **en premier commentaire**
> (LinkedIn réduit la portée des posts qui contiennent un lien).

---

⚽ J'ai essayé de prédire les matchs de la Ligue 1 ivoirienne avec la data et l'IA.

Le football ivoirien produit des talents partout en Europe, mais ses données sont dispersées et presque jamais analysées. J'ai donc construit, de A à Z, une plateforme de données sur 10 saisons de MTN Ligue 1 (2016 → 2026).

🔧 Ce que j'ai construit
• Collecte automatisée (RSSSF, Wikipédia, Futbol24, API-Football), dans le respect des robots.txt et des CGU
• MongoDB pour les données brutes : chaque page est archivée avec son URL et sa date
• PostgreSQL : modèle Merise, ETL avec recoupement des sources, 10 requêtes SQL (fonctions de fenêtre, CTE)
• Un graphe de 961 mouvements de joueurs : PageRank et communautés de clubs
• 6 modèles de prédiction : Elo, régression logistique, forêt aléatoire, gradient boosting, réseau de neurones PyTorch
• Un tableau de bord Streamlit avec les probabilités des prochains matchs

📊 Ce que disent les données
• 30 % des matchs se terminent par un nul (≈ 25 % en Europe)
• À peine 2 buts par match : 1-1, 1-0, 0-0 et 0-1 couvrent plus de la moitié des matchs
• L'ASEC Mimosas a remporté 6 des 10 derniers titres et est le club le plus central du réseau des transferts

🧠 Le résultat qui m'a le plus appris
Le meilleur modèle n'est pas le réseau de neurones : c'est un simple score Elo.
→ 43,7 % de bons pronostics, contre 35,4 % pour « toujours parier sur l'équipe qui reçoit »
→ une validation temporelle sur 1 141 matchs : chaque saison est prédite uniquement à partir des précédentes
→ un bootstrap qui montre que le gain est réel, mais qu'une seule saison ne suffit pas à départager les modèles

Avec peu de données (≈ 240 matchs par saison), la rigueur de l'évaluation compte plus que la complexité de l'algorithme. Le réseau de neurones fait mieux que le hasard, mais pas mieux qu'un modèle simple. Je préfère présenter ce résultat honnête plutôt qu'un chiffre gonflé par une fuite de données.

🚀 Prochaines étapes : un modèle de Poisson (Dixon-Coles) pour mieux prédire les nuls, et les événements de match (buteurs, cartons) en cours de collecte.

Code, rapport et démo en commentaire 👇

Je recherche une alternance en data science / data engineering : je serais ravi d'échanger !

#DataScience #MachineLearning #Football #CôteDIvoire #Python #SQL #PyTorch #Streamlit #DataEngineering #Alternance

---

## Premier commentaire (à poster juste après)

📂 Code : https://github.com/<ton-compte>/ligue1-ci-data
📊 Démo en ligne : https://<ton-app>.streamlit.app
📄 Rapport (9 pages) : dans le dépôt, docs/rapport.pdf

## Visuel de couverture conseillé

`docs/linkedin/diapos/01.png` (accroche) ou `docs/figures/06_comparaison_modeles.png`.

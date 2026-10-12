# Post LinkedIn — à publier avec la vidéo `video_ligue1_pro.mp4` (+ sous-titres `.srt`)

> Les liens sont dans le post (version « tout-en-un »). Variante possible : les déplacer en
> premier commentaire, LinkedIn mettant parfois moins en avant les posts qui contiennent un lien.
> Le dépôt `ligue1-ci-data` doit être publié (public) sur GitHub avant de poster.

## Phrase de présentation (à réutiliser : résumé LinkedIn, CV, portfolio)

> J'ai réalisé un projet Data Science complet sur la Ligue 1 Côte d'Ivoire : collecte
> automatisée de 10 saisons (1 934 matchs, 31 clubs), bases MongoDB et PostgreSQL, analyses
> statistiques et de réseau, comparaison de six modèles de Machine Learning en validation
> temporelle (43,7 % de bons pronostics contre 35,4 % pour la référence naïve), et une
> application Streamlit interactive.

---

⚽📊 La Ligue 1 ivoirienne forme des joueurs pour toute l'Afrique et l'Europe… mais ses données sont dispersées et presque jamais analysées.

J'en ai fait mon projet personnel de Data Science : 10 saisons de MTN Ligue 1 (2016 → 2026), de la collecte web jusqu'à la prédiction des matchs.

❓ La question de départ
Que révèlent les données publiques sur ce championnat ? Et peut-on prédire un match mieux qu'une règle naïve ?

🔧 Ce que j'ai construit
• Collecte automatisée de 4 sources (RSSSF, Wikipédia, Futbol24, API-Football), dans le respect des robots.txt et des CGU
• MongoDB pour les données brutes : 711 pages archivées avec leur URL et leur date
• Un ETL qui recoupe les scores et harmonise 102 noms en 31 clubs → PostgreSQL (modèle Merise, 12 tables, 10 requêtes SQL)
• Un graphe de 961 mouvements de joueurs : PageRank, intermédiarité, communautés
• 6 modèles comparés : Elo, régression logistique, forêt aléatoire, gradient boosting, réseau de neurones PyTorch et une référence naïve
• Une application Streamlit : classements, fiches clubs, réseau, probabilités des prochains matchs

📈 Ce que montrent les données (1 934 matchs)
• 30 % des matchs se terminent par un nul
• À peine 2 buts par match en moyenne
• L'ASEC Mimosas : 6 titres sur 10, et 42 % des départs suivis vers des clubs hors Ligue 1

🧠 Le résultat qui m'a le plus appris
Chaque saison est prédite uniquement avec les saisons précédentes (1 141 matchs).
→ Un simple modèle Elo atteint 43,7 % de bons pronostics, contre 35,4 % pour la référence naïve
→ Le gain est significatif (bootstrap, IC 95 %), mais les modèles restent trop proches pour être départagés, et le réseau de neurones ne fait pas mieux qu'un modèle simple

Avec peu de données, la rigueur de l'évaluation compte plus que la complexité de l'algorithme. Je préfère un résultat honnête à un chiffre gonflé.

🚀 Prochaine étape : un modèle de Poisson (Dixon-Coles) pour mieux prédire les nuls.

🔗 Code et documentation : https://github.com/coulibaly-abou/ligue1-ci-data
👤 Mes autres projets : https://github.com/coulibaly-abou

🎓 Étudiant en BUT 3 Science des Données (parcours Exploration et Modélisation Statistique), je recherche un stage et une alternance en Data Science, Data Analysis ou Statistique à partir de septembre 2026. Échangeons !

#DataScience #DataAnalysis #MachineLearning #Statistique #Python #SQL #PyTorch #Streamlit #Football #CôteDIvoire #Alternance #Stage

---

## Avant de publier

- Publier le dépôt en public sous le nom `ligue1-ci-data` sur https://github.com/coulibaly-abou
  (le lien du post renvoie une erreur tant que ce n'est pas fait).
- Joindre `video_ligue1_pro.mp4` et ajouter `video_ligue1_pro.srt` comme sous-titres.
- Si l'application est déployée sur Streamlit Community Cloud, ajouter sous le lien du code :
  `🖥️ Démo en ligne : https://<nom-de-l-app>.streamlit.app`

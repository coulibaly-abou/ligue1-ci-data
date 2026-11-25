// 3. Clubs formateurs : clubs de Ligue 1 où le plus de joueurs ont été formés (passage
//    « jeunes »), avec le nombre d'entre eux passés ensuite par un club hors Ligue 1
//    (est_ligue1 = false : club étranger ou ivoirien de division inférieure).
MATCH (c:Club {est_ligue1: true})<-[:FORME_A]-(p:Personne)
OPTIONAL MATCH (p)-[:A_JOUE_POUR]->(autre:Club {est_ligue1: false})
WITH c, p, count(autre) > 0 AS parti_hors_ligue1
RETURN c.nom AS club, count(p) AS joueurs_formes,
       sum(CASE WHEN parti_hors_ligue1 THEN 1 ELSE 0 END) AS partis_hors_ligue1
ORDER BY joueurs_formes DESC, club
LIMIT 15;

-- 3. Avantage du terrain par club : points par match à domicile vs à l'extérieur
-- (clubs avec au moins 60 matchs depuis 2016)
SELECT k.nom AS club,
       ROUND(AVG(points) FILTER (WHERE a_domicile), 2)     AS ppm_domicile,
       ROUND(AVG(points) FILTER (WHERE NOT a_domicile), 2) AS ppm_exterieur,
       ROUND(AVG(points) FILTER (WHERE a_domicile)
             - AVG(points) FILTER (WHERE NOT a_domicile), 2) AS avantage,
       COUNT(*) AS matchs
FROM ligue1.mv_resultat_club r JOIN ligue1.club k USING (id_club)
GROUP BY k.nom
HAVING COUNT(*) >= 60
ORDER BY avantage DESC;

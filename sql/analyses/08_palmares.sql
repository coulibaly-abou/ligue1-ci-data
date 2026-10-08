-- 8. Palmarès : champion de chaque saison (classement officiel RSSSF) et nombre de titres
WITH champions AS (
    SELECT DISTINCT ON (c.id_saison) c.id_saison, k.nom AS champion, c.points
    FROM ligue1.classement c JOIN ligue1.club k USING (id_club)
    WHERE c.rang = 1 AND c.source = 'rsssf' AND c.mention LIKE '%Champions%'
    ORDER BY c.id_saison
)
SELECT s.libelle AS saison, ch.champion, ch.points,
       COUNT(*) OVER (PARTITION BY ch.champion) AS titres_depuis_2016
FROM champions ch JOIN ligue1.saison s USING (id_saison)
ORDER BY s.libelle;

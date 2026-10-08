-- 4. Plus longues séries d'invincibilité (CTE « gaps and islands »)
-- Chaque défaite ouvre un nouveau groupe ; la longueur d'un groupe = série sans défaite.
WITH numerote AS (
    SELECT id_club, id_match, date_match, issue,
           SUM(CASE WHEN issue = 'D' THEN 1 ELSE 0 END)
               OVER (PARTITION BY id_club ORDER BY date_match, id_match) AS groupe
    FROM ligue1.mv_resultat_club
), series AS (
    SELECT id_club, groupe,
           COUNT(*) FILTER (WHERE issue <> 'D') AS longueur,
           MIN(date_match) FILTER (WHERE issue <> 'D') AS debut,
           MAX(date_match) FILTER (WHERE issue <> 'D') AS fin
    FROM numerote
    GROUP BY id_club, groupe
)
SELECT k.nom AS club, s.longueur AS matchs_sans_defaite, s.debut, s.fin
FROM series s JOIN ligue1.club k USING (id_club)
ORDER BY s.longueur DESC
LIMIT 10;

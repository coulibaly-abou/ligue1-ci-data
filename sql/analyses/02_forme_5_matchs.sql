-- 2. Forme sur les 5 derniers matchs de chaque club (toutes saisons confondues)
-- Fenêtre glissante ROWS BETWEEN 4 PRECEDING AND CURRENT ROW + série V/N/D.
WITH forme AS (
    SELECT id_club, id_match, date_match, issue,
           SUM(points) OVER w AS points_5,
           ROW_NUMBER() OVER (PARTITION BY id_club
                              ORDER BY date_match DESC, id_match DESC) AS recent
    FROM ligue1.mv_resultat_club
    WINDOW w AS (PARTITION BY id_club ORDER BY date_match, id_match
                 ROWS BETWEEN 4 PRECEDING AND CURRENT ROW)
)
SELECT k.nom AS club, f.points_5, f.date_match AS dernier_match,
       (SELECT STRING_AGG(f2.issue, '' ORDER BY f2.recent DESC)
        FROM forme f2 WHERE f2.id_club = f.id_club AND f2.recent <= 5) AS serie
FROM forme f JOIN ligue1.club k USING (id_club)
WHERE f.recent = 1 AND f.date_match >= DATE '2026-08-01'   -- clubs de la saison en cours
ORDER BY f.points_5 DESC;

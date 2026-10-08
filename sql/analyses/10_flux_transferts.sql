-- 10. Flux de transferts : clubs de Ligue 1 les plus actifs (arrivées, départs, solde)
-- Source : API-Football (transferts déclarés des clubs suivis, 2022 → 2026).
WITH flux AS (
    SELECT id_club_arrivee AS id_club, 1 AS arrivee, 0 AS depart FROM ligue1.transfert
    UNION ALL
    SELECT id_club_depart, 0, 1 FROM ligue1.transfert
)
SELECT k.nom AS club, SUM(arrivee) AS arrivees, SUM(depart) AS departs,
       SUM(arrivee) - SUM(depart) AS solde
FROM flux JOIN ligue1.club k USING (id_club)
WHERE k.est_ligue1
GROUP BY k.nom
ORDER BY COUNT(*) DESC
LIMIT 15;

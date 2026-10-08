-- 5. Meilleurs buteurs par saison (top 3) ; un joueur cité par deux sources compte une fois
WITH unique_source AS (
    SELECT DISTINCT ON (id_saison, joueur) id_saison, joueur, buts, id_club
    FROM ligue1.stat_buteur
    ORDER BY id_saison, joueur, buts DESC
)
SELECT * FROM (
    SELECT s.libelle AS saison, u.joueur, k.nom AS club, u.buts,
           DENSE_RANK() OVER (PARTITION BY u.id_saison ORDER BY u.buts DESC) AS rang
    FROM unique_source u
    JOIN ligue1.saison s USING (id_saison)
    LEFT JOIN ligue1.club k USING (id_club)
) t
WHERE rang <= 3
ORDER BY saison DESC, rang;

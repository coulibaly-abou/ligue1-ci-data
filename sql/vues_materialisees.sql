-- Vues matérialisées qui alimentent le tableau de bord (recréées à chaque ETL).
-- Une ligne = un club dans un match : base commune des classements et de la forme.
SET search_path TO ligue1;

CREATE MATERIALIZED VIEW mv_match_club AS
SELECT m.id_match, m.id_saison, m.date_match, m.phase, TRUE AS a_domicile,
       m.id_club_dom AS id_club, m.id_club_ext AS id_adversaire,
       m.buts_dom AS bp, m.buts_ext AS bc
FROM match m WHERE m.statut = 'joue'
UNION ALL
SELECT m.id_match, m.id_saison, m.date_match, m.phase, FALSE,
       m.id_club_ext, m.id_club_dom, m.buts_ext, m.buts_dom
FROM match m WHERE m.statut = 'joue';

-- Points et numéro du match (journée jouée par le club), calculés une seule fois
CREATE MATERIALIZED VIEW mv_resultat_club AS
SELECT mc.*,
       CASE WHEN bp > bc THEN 3 WHEN bp = bc THEN 1 ELSE 0 END AS points,
       CASE WHEN bp > bc THEN 'V' WHEN bp = bc THEN 'N' ELSE 'D' END AS issue,
       ROW_NUMBER() OVER (PARTITION BY id_saison, id_club ORDER BY date_match, id_match)
           AS journee_club
FROM mv_match_club mc;

-- Classement recalculé après chaque journée jouée (fonctions de fenêtre cumulées)
CREATE MATERIALIZED VIEW mv_classement_journee AS
WITH cumul AS (
    SELECT id_saison, id_club, journee_club AS journee,
           SUM(points) OVER w AS points,
           SUM(bp - bc) OVER w AS difference,
           SUM(bp) OVER w AS buts_pour
    FROM mv_resultat_club
    WINDOW w AS (PARTITION BY id_saison, id_club ORDER BY journee_club)
)
SELECT c.*, RANK() OVER (PARTITION BY id_saison, journee
                         ORDER BY points DESC, difference DESC, buts_pour DESC) AS rang
FROM cumul c;

-- Avantage du terrain par club et par saison
CREATE MATERIALIZED VIEW mv_avantage_terrain AS
SELECT id_saison, id_club,
       ROUND(AVG(points) FILTER (WHERE a_domicile), 3)     AS ppm_domicile,
       ROUND(AVG(points) FILTER (WHERE NOT a_domicile), 3) AS ppm_exterieur,
       COUNT(*) AS matchs
FROM mv_resultat_club
GROUP BY id_saison, id_club;

CREATE INDEX ON mv_resultat_club (id_club, date_match);
CREATE INDEX ON mv_classement_journee (id_saison, journee);

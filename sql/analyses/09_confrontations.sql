-- 9. Bilan des confrontations directes : derby ASEC Mimosas – Africa Sports
-- (remplacer les deux noms pour une autre affiche)
SELECT k.nom AS club, COUNT(*) AS matchs,
       COUNT(*) FILTER (WHERE r.issue = 'V') AS victoires,
       COUNT(*) FILTER (WHERE r.issue = 'N') AS nuls,
       COUNT(*) FILTER (WHERE r.issue = 'D') AS defaites,
       SUM(r.bp) AS buts_pour, SUM(r.bc) AS buts_contre
FROM ligue1.mv_resultat_club r
JOIN ligue1.club k USING (id_club)
JOIN ligue1.club a ON a.id_club = r.id_adversaire
WHERE k.nom IN ('ASEC Mimosas', 'Africa Sports')
  AND a.nom IN ('ASEC Mimosas', 'Africa Sports')
GROUP BY k.nom;

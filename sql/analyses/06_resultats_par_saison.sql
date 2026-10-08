-- 6. Répartition des résultats et buts par match, saison par saison
SELECT s.libelle AS saison, COUNT(*) AS matchs,
       ROUND(100.0 * AVG((resultat = 'D')::int), 1) AS pct_domicile,
       ROUND(100.0 * AVG((resultat = 'N')::int), 1) AS pct_nul,
       ROUND(100.0 * AVG((resultat = 'E')::int), 1) AS pct_exterieur,
       ROUND(AVG(buts_dom + buts_ext), 2) AS buts_par_match,
       ROUND(100.0 * AVG((buts_dom + buts_ext <= 1)::int), 1) AS pct_un_but_ou_moins
FROM ligue1.v_match m JOIN ligue1.saison s USING (id_saison)
WHERE m.statut = 'joue'
GROUP BY s.libelle
ORDER BY s.libelle;

-- 7. Scores les plus fréquents, avec la part cumulée (fenêtre sur un agrégat)
SELECT buts_dom || '-' || buts_ext AS score, COUNT(*) AS matchs,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct,
       ROUND(100.0 * SUM(COUNT(*)) OVER (ORDER BY COUNT(*) DESC, buts_dom, buts_ext)
             / SUM(COUNT(*)) OVER (), 1) AS pct_cumule
FROM ligue1.match
WHERE statut = 'joue'
GROUP BY buts_dom, buts_ext
ORDER BY matchs DESC
LIMIT 12;

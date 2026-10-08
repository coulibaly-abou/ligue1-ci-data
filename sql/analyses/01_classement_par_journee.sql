-- 1. Classement recalculé journée par journée (saison 2025-2026)
-- Fonctions de fenêtre : cumul des points, puis rang parmi les clubs à la même journée.
SELECT k.nom AS club, c.journee, c.points, c.difference, c.rang
FROM ligue1.mv_classement_journee c
JOIN ligue1.club k USING (id_club)
WHERE c.id_saison = 2025
ORDER BY c.journee, c.rang;

// 5. Parcours complet d'une personne : formation, clubs seniors et postes d'entraîneur,
//    dans l'ordre chronologique.
// Paramètre : $joueur (nom ou partie du nom, sans tenir compte de la casse)
MATCH (p:Personne)-[r:FORME_A|A_JOUE_POUR|A_ENTRAINE]->(c:Club)
WHERE toLower(p.nom) CONTAINS toLower($joueur)
RETURN p.nom AS personne, type(r) AS role, c.nom AS club, c.est_ligue1 AS ligue1,
       r.annee_debut AS debut, r.annee_fin AS fin, r.pret AS pret, r.matchs AS matchs,
       r.buts AS buts
ORDER BY personne, debut;

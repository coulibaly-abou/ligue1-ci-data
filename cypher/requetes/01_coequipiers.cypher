// 1. Coéquipiers d'un joueur : personnes passées en équipe senior dans le même club
//    pendant au moins une année commune (annee_fin NULL = passage en cours).
// Paramètre : $joueur (nom ou partie du nom, sans tenir compte de la casse)
MATCH (j:Personne)-[a:A_JOUE_POUR]->(c:Club)<-[b:A_JOUE_POUR]-(co:Personne)
WHERE toLower(j.nom) CONTAINS toLower($joueur) AND co <> j
  AND a.annee_debut <= coalesce(b.annee_fin, 9999)
  AND b.annee_debut <= coalesce(a.annee_fin, 9999)
RETURN DISTINCT j.nom AS joueur, c.nom AS club, co.nom AS coequipier,
       CASE WHEN a.annee_debut > b.annee_debut THEN a.annee_debut ELSE b.annee_debut END AS depuis
ORDER BY club, depuis, coequipier
LIMIT 50;

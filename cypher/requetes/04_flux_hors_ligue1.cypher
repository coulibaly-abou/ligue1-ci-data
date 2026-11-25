// 4. Flux sortants : destinations hors Ligue 1 (clubs étrangers ou de division inférieure)
//    les plus fréquentes pour les joueurs quittant un club de Ligue 1. Un même transfert
//    peut figurer dans les deux sources : les comptes sont donc donnés par source.
// Paramètre : $depuis (année minimale du mouvement, ex. 2010)
MATCH (a:Club {est_ligue1: true})-[m:MOUVEMENT]->(b:Club {est_ligue1: false})
WHERE m.annee >= $depuis
RETURN b.nom AS destination,
       sum(CASE WHEN m.source = 'carrieres_wikipedia' THEN 1 ELSE 0 END) AS departs_wikipedia,
       sum(CASE WHEN m.source = 'api_football' THEN 1 ELSE 0 END) AS departs_api_football,
       sum(CASE WHEN m.pret THEN 1 ELSE 0 END) AS dont_prets,
       collect(DISTINCT a.nom)[..5] AS clubs_de_depart
ORDER BY departs_wikipedia + departs_api_football DESC, destination
LIMIT 20;

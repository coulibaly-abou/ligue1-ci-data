// Contraintes d'unicité (créent aussi les index utilisés par MERGE / MATCH du chargement).
// Appliqué par src/graphe/chargement_neo4j.py ; instructions séparées par « ; ».
CREATE CONSTRAINT club_nom IF NOT EXISTS
FOR (c:Club) REQUIRE c.nom IS UNIQUE;

CREATE CONSTRAINT personne_id IF NOT EXISTS
FOR (p:Personne) REQUIRE p.id_personne IS UNIQUE;

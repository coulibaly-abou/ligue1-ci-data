// 2. Plus court chemin entre deux clubs à travers les carrières : club - joueur - club ...
//    Montre par quels joueurs deux clubs (ivoiriens ou étrangers) sont reliés.
// Paramètres : $club_depart, $club_arrivee (noms exacts des nœuds :Club)
MATCH (a:Club {nom: $club_depart}), (b:Club {nom: $club_arrivee})
MATCH chemin = shortestPath((a)-[:A_JOUE_POUR|FORME_A*..8]-(b))
RETURN [n IN nodes(chemin) | coalesce(n.nom, '?')] AS etapes,
       length(chemin) / 2 AS nb_joueurs_intermediaires;

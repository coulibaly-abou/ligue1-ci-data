-- MPD PostgreSQL de la Ligue 1 ivoirienne, issu du MCD / MLD (docs/modele_donnees.md).
-- Modèle relationnel normalisé (3FN). Recréé à chaque ETL : python -m src.etl.run

DROP SCHEMA IF EXISTS ligue1 CASCADE;
CREATE SCHEMA ligue1;
SET search_path TO ligue1;

-- ------------------------------------------------------------ référentiels

CREATE TABLE ville (
    id_ville      SERIAL PRIMARY KEY,
    nom           VARCHAR(100) NOT NULL UNIQUE,
    latitude      NUMERIC(8, 5) CHECK (latitude BETWEEN -90 AND 90),
    longitude     NUMERIC(8, 5) CHECK (longitude BETWEEN -180 AND 180),
    url_coordonnees VARCHAR(300)                    -- article Wikipédia d'où viennent lat/lon
);

CREATE TABLE stade (
    id_stade      SERIAL PRIMARY KEY,
    nom           VARCHAR(150) NOT NULL UNIQUE,
    capacite      INTEGER CHECK (capacite > 0),
    id_ville      INTEGER REFERENCES ville (id_ville)
);

CREATE TABLE club (
    id_club       SERIAL PRIMARY KEY,
    nom           VARCHAR(150) NOT NULL UNIQUE,     -- nom harmonisé (config/clubs_alias.yml)
    est_ligue1    BOOLEAN NOT NULL,                 -- FALSE : club cité dans une carrière
    api_id        INTEGER UNIQUE,                   -- identifiant API-Football
    id_ville      INTEGER REFERENCES ville (id_ville),
    id_stade      INTEGER REFERENCES stade (id_stade)
);

CREATE TABLE saison (
    id_saison     SMALLINT PRIMARY KEY,             -- année de début : 2024 pour 2024-2025
    libelle       CHAR(9) NOT NULL UNIQUE,          -- '2024-2025'
    annee_debut   SMALLINT NOT NULL,
    annee_fin     SMALLINT NOT NULL CHECK (annee_fin = annee_debut + 1),
    nb_clubs      SMALLINT,
    format        VARCHAR(30) NOT NULL,
    statut        VARCHAR(15) NOT NULL CHECK (statut IN ('terminee', 'interrompue', 'en_cours'))
);

CREATE TABLE personne (
    id_personne    SERIAL PRIMARY KEY,
    nom            VARCHAR(150) NOT NULL,
    nom_complet    VARCHAR(200),
    date_naissance DATE,
    nationalite    VARCHAR(100),
    poste          VARCHAR(100),
    est_joueur     BOOLEAN NOT NULL,
    est_entraineur BOOLEAN NOT NULL,
    url_wikipedia  VARCHAR(300) UNIQUE,
    api_id         INTEGER UNIQUE
);

-- ------------------------------------------------------------------ matchs

CREATE TABLE match (
    id_match       SERIAL PRIMARY KEY,
    phase          VARCHAR(60) NOT NULL,            -- 'Saison reguliere', 'Championship Playoff'...
    journee        SMALLINT CHECK (journee > 0),
    date_match     DATE,
    buts_dom       SMALLINT CHECK (buts_dom >= 0),
    buts_ext       SMALLINT CHECK (buts_ext >= 0),
    statut         VARCHAR(12) NOT NULL CHECK (statut IN ('joue', 'tapis_vert', 'abandonne',
                                                           'reporte', 'annule', 'a_jouer')),
    arbitre        VARCHAR(100),
    note           TEXT,
    source         VARCHAR(20) NOT NULL,            -- 'rsssf', 'futbol24', 'wikipedia'
    api_fixture_id INTEGER UNIQUE,
    id_saison      SMALLINT NOT NULL REFERENCES saison (id_saison),
    id_club_dom    INTEGER NOT NULL REFERENCES club (id_club),
    id_club_ext    INTEGER NOT NULL REFERENCES club (id_club),
    id_stade       INTEGER REFERENCES stade (id_stade),
    CHECK (id_club_dom <> id_club_ext),
    CHECK (statut <> 'joue' OR (buts_dom IS NOT NULL AND buts_ext IS NOT NULL))
);

CREATE TABLE but (
    id_but         SERIAL PRIMARY KEY,
    minute         SMALLINT CHECK (minute BETWEEN 0 AND 130),
    type_but       VARCHAR(20) NOT NULL CHECK (type_but IN ('normal', 'penalty',
                                                           'contre_son_camp')),
    buteur         VARCHAR(150),
    passeur        VARCHAR(150),
    id_match       INTEGER NOT NULL REFERENCES match (id_match),
    id_club        INTEGER NOT NULL REFERENCES club (id_club),  -- club indiqué par l'API
    id_personne    INTEGER REFERENCES personne (id_personne)
);

CREATE TABLE carton (
    id_carton      SERIAL PRIMARY KEY,
    minute         SMALLINT CHECK (minute BETWEEN 0 AND 130),
    couleur        VARCHAR(12) NOT NULL CHECK (couleur IN ('jaune', 'rouge', 'jaune_rouge')),
    joueur         VARCHAR(150),
    id_match       INTEGER NOT NULL REFERENCES match (id_match),
    id_club        INTEGER NOT NULL REFERENCES club (id_club),
    id_personne    INTEGER REFERENCES personne (id_personne)
);

CREATE TABLE classement (                           -- classements officiels publiés
    id_classement  SERIAL PRIMARY KEY,
    phase          VARCHAR(60) NOT NULL,
    groupe         VARCHAR(5) NOT NULL DEFAULT '',
    type_tableau   VARCHAR(12) NOT NULL CHECK (type_tableau IN ('final', 'mi-saison',
                                                              'arret', 'en_cours')),
    rang           SMALLINT NOT NULL CHECK (rang > 0),
    joues SMALLINT, gagnes SMALLINT, nuls SMALLINT, perdus SMALLINT,
    buts_pour SMALLINT, buts_contre SMALLINT, points SMALLINT,
    mention        VARCHAR(50),
    source         VARCHAR(20) NOT NULL,
    id_saison      SMALLINT NOT NULL REFERENCES saison (id_saison),
    id_club        INTEGER NOT NULL REFERENCES club (id_club),
    UNIQUE (id_saison, id_club, phase, groupe, type_tableau, source)
);

-- ------------------------------------------------- personnes et carrières

CREATE TABLE passage (                              -- un passage d'une personne dans un club
    id_passage     SERIAL PRIMARY KEY,
    role           VARCHAR(12) NOT NULL CHECK (role IN ('senior', 'jeunes', 'selection',
                                                        'entraineur')),
    annee_debut    SMALLINT,
    annee_fin      SMALLINT,                        -- NULL : passage en cours
    pret           BOOLEAN NOT NULL,
    matchs         SMALLINT,
    buts           SMALLINT,
    club_brut      VARCHAR(150) NOT NULL,           -- nom tel qu'écrit dans la source
    source         VARCHAR(20) NOT NULL,
    id_personne    INTEGER NOT NULL REFERENCES personne (id_personne),
    id_club        INTEGER REFERENCES club (id_club),  -- NULL : sélection nationale
    CHECK (annee_debut IS NULL OR annee_fin IS NULL OR annee_debut <= annee_fin)
);

CREATE TABLE transfert (
    id_transfert    SERIAL PRIMARY KEY,
    joueur          VARCHAR(150) NOT NULL,
    date_transfert  DATE,
    type_transfert  VARCHAR(50),                    -- 'Loan', 'Free', montant...
    source          VARCHAR(20) NOT NULL,
    id_personne     INTEGER REFERENCES personne (id_personne),
    id_club_depart  INTEGER REFERENCES club (id_club),
    id_club_arrivee INTEGER REFERENCES club (id_club)
);

CREATE TABLE stat_buteur (                          -- total de buts d'un joueur sur une saison
    id_stat        SERIAL PRIMARY KEY,
    joueur         VARCHAR(150) NOT NULL,
    buts           SMALLINT NOT NULL CHECK (buts >= 0),
    matchs         SMALLINT,
    source         VARCHAR(20) NOT NULL,
    id_saison      SMALLINT NOT NULL REFERENCES saison (id_saison),
    id_club        INTEGER REFERENCES club (id_club),
    id_personne    INTEGER REFERENCES personne (id_personne),
    UNIQUE (id_saison, joueur, source)
);

-- ------------------------------------------------- index des clés étrangères

CREATE INDEX ON stade (id_ville);
CREATE INDEX ON club (id_ville);
CREATE INDEX ON match (id_saison, journee);
CREATE INDEX ON match (id_club_dom);
CREATE INDEX ON match (id_club_ext);
CREATE INDEX ON match (date_match);
CREATE INDEX ON but (id_match);
CREATE INDEX ON carton (id_match);
CREATE INDEX ON classement (id_club);
CREATE INDEX ON passage (id_personne);
CREATE INDEX ON passage (id_club);
CREATE INDEX ON transfert (id_club_depart);
CREATE INDEX ON transfert (id_club_arrivee);
CREATE INDEX ON stat_buteur (id_club);

-- --------------------------------------------------------------------- vue

-- Résultat calculé à partir du score (non stocké : évite toute incohérence)
CREATE VIEW v_match AS
SELECT m.*,
       CASE WHEN m.buts_dom > m.buts_ext THEN 'D'
            WHEN m.buts_dom = m.buts_ext THEN 'N'
            WHEN m.buts_dom < m.buts_ext THEN 'E' END AS resultat
FROM match m;

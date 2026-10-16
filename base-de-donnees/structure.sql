-- Schéma initial de démonstration : données entièrement fictives.
-- Exécuter dans une base dédiée (voir documentation/base-de-donnees.md).
BEGIN;

CREATE TABLE IF NOT EXISTS personnes (
    id_personne BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nom VARCHAR(100) NOT NULL,
    prenom VARCHAR(100) NOT NULL,
    actif BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS identifiants (
    id_identifiant BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_personne BIGINT NOT NULL REFERENCES personnes(id_personne),
    code VARCHAR(64) NOT NULL UNIQUE,
    actif BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS portes (
    id_porte BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nom VARCHAR(100) NOT NULL UNIQUE,
    actif BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS autorisations (
    id_personne BIGINT NOT NULL REFERENCES personnes(id_personne),
    id_porte BIGINT NOT NULL REFERENCES portes(id_porte),
    date_debut TIMESTAMPTZ,
    date_fin TIMESTAMPTZ,
    PRIMARY KEY (id_personne, id_porte),
    CONSTRAINT periode_valide CHECK (
        date_debut IS NULL OR date_fin IS NULL OR date_fin > date_debut
    )
);

COMMIT;

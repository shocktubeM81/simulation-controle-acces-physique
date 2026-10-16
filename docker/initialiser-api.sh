#!/bin/sh
# Initialisation des rôles techniques lors du premier démarrage de PostgreSQL.
set -eu
mot_de_passe="$(cat /run/secrets/mot_de_passe_api)"
psql -v ON_ERROR_STOP=1 --username postgres --dbname "$POSTGRES_DB" -v passe="$mot_de_passe" <<'SQL'
CREATE ROLE api_anonyme NOLOGIN;
CREATE ROLE api_authentificateur LOGIN NOINHERIT;
CREATE ROLE api_proprietaire NOLOGIN;
SELECT format('ALTER ROLE api_authentificateur PASSWORD %L', :'passe') \gexec
GRANT api_anonyme TO api_authentificateur;
GRANT CONNECT ON DATABASE controle_acces_simulation TO api_authentificateur;
GRANT SELECT ON TABLE personnes, identifiants, portes, autorisations TO api_proprietaire;
CREATE SCHEMA api AUTHORIZATION api_proprietaire;
SQL

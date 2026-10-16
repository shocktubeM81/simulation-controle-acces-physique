#!/bin/sh
# Appelé automatiquement une seule fois, lors de la création du volume PostgreSQL.
set -eu
export PGPASSWORD="$(cat /run/secrets/mot_de_passe_postgres)"
mot_de_passe="$(cat /run/secrets/mot_de_passe_api)"
psql -v ON_ERROR_STOP=1 --username postgres --dbname "$POSTGRES_DB" -v passe="$mot_de_passe" <<'SQL'
CREATE ROLE api_anonyme NOLOGIN;
CREATE ROLE api_authentificateur LOGIN NOINHERIT;
SELECT format('ALTER ROLE api_authentificateur PASSWORD %L', :'passe') \gexec
GRANT api_anonyme TO api_authentificateur;
GRANT CONNECT ON DATABASE controle_acces_simulation TO api_authentificateur;
SQL

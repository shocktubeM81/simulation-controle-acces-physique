#!/bin/sh
# Configuration rejouable après le démarrage du service PostgreSQL.
set -eu
mot_de_passe="$(cat /run/secrets/mot_de_passe_api)"
psql -v ON_ERROR_STOP=1 --username postgres --dbname controle_acces_simulation \
  -v "passe=$mot_de_passe" -f /opt/laboratoire/docker/configurer-roles-api.sql
psql -v ON_ERROR_STOP=1 --username postgres --dbname controle_acces_simulation \
  -f /opt/laboratoire/sql/interface-api.sql

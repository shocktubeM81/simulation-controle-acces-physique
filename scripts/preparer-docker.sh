#!/usr/bin/env bash
# Préparation non destructive des secrets du laboratoire Docker.
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
command -v openssl >/dev/null || { echo "Installer openssl." >&2; exit 1; }
command -v docker >/dev/null || { echo "Installer Docker et Docker Compose." >&2; exit 1; }
docker compose version >/dev/null

umask 077
mkdir -p secrets

if [[ ! -e secrets/postgres.txt ]]; then
    openssl rand -hex 32 > secrets/postgres.txt
    echo "Secret PostgreSQL créé."
fi
if [[ ! -e secrets/api.txt ]]; then
    openssl rand -hex 32 > secrets/api.txt
    echo "Secret API créé."
fi

if [[ ! -e .env.docker.api ]]; then
    mot_de_passe="$(cat secrets/api.txt)"
    printf 'PGRST_DB_URI=postgres://api_authentificateur:%s@base-de-donnees:5432/controle_acces_simulation\n' "$mot_de_passe" > .env.docker.api
    unset mot_de_passe
    echo "Configuration PostgREST créée."
fi
chmod 600 secrets/postgres.txt secrets/api.txt .env.docker.api
echo "Préparation terminée. Aucun mot de passe n'a été affiché."

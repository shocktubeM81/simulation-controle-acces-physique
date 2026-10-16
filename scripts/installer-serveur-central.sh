#!/usr/bin/env bash
# Installation du serveur central conteneurisé, sans modifier PostgreSQL sur l'hôte.
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

for outil in docker openssl curl; do
    command -v "$outil" >/dev/null || {
        echo "Commande absente : $outil. Consulter INSTALLATION.md." >&2
        exit 1
    }
done
docker compose version >/dev/null

bash scripts/preparer-docker.sh
docker compose up -d --build

echo "Vérification de l'interface locale..."
for tentative in $(seq 1 30); do
    if bash scripts/verifier-installation.sh >/dev/null 2>&1; then
        bash scripts/verifier-installation.sh
        echo "Serveur central prêt."
        exit 0
    fi
    sleep 2
done
docker compose ps
echo "Échec du test. Consulter : docker compose logs --tail=60" >&2
exit 1

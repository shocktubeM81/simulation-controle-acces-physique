#!/usr/bin/env bash
# Installation ou réparation non destructive de la simulation centrale Docker.
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

for outil in docker openssl curl; do
    command -v "$outil" >/dev/null || { echo "Commande absente : $outil." >&2; exit 1; }
done
docker compose version >/dev/null

bash scripts/preparer-docker.sh

echo "Démarrage de PostgreSQL..."
docker compose up -d --wait base-de-donnees

echo "Configuration des rôles et de l'API..."
docker compose exec -T -u 0 base-de-donnees sh /opt/laboratoire/docker/initialiser-api.sh

echo "Actualisation du cache de schéma PostgREST..."
docker compose exec -T -u 0 base-de-donnees \
  psql -v ON_ERROR_STOP=1 -U postgres -d controle_acces_simulation \
  -c "NOTIFY pgrst, 'reload schema';"

echo "Démarrage de PostgREST..."
docker compose up -d interface-api

echo "Vérification de l’API sur 127.0.0.1:3000..."
for tentative in $(seq 1 10); do
    if bash scripts/verifier-installation.sh >/dev/null 2>&1; then
        bash scripts/verifier-installation.sh
        echo "Serveur central prêt."
        exit 0
    fi
    echo "Tentative $tentative/10 : API pas encore validée."
    sleep 2
done
docker compose ps
echo "Échec de la vérification. Détails :" >&2
bash scripts/verifier-installation.sh || true
docker compose logs --tail=30 interface-api || true
exit 1

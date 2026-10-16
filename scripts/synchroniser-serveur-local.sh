#!/usr/bin/env bash
# Un instantané fictif par SSH authentifié : aucune ouverture du port 3000 sur le LAN.
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [[ $# -ne 1 ]]; then
    echo "Usage : bash scripts/synchroniser-serveur-local.sh UTILISATEUR@ORDINATEUR" >&2
    exit 2
fi
for outil in ssh sudo docker; do
    command -v "$outil" >/dev/null || { echo "Commande absente : $outil" >&2; exit 1; }
done

# Aucun secret SSH n'est monté dans le conteneur; ssh fonctionne sur l'hôte.
# StrictHostKeyChecking=yes impose une clé d'hôte déjà vérifiée dans known_hosts.
ssh -T -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=5 "$1" \
    'curl --fail --silent --show-error --max-time 5 --request POST http://127.0.0.1:3000/rpc/exporter_autorisations' \
    | sudo docker compose -f compose.local.yaml run --rm -T importer-sqlite

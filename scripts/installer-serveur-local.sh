#!/usr/bin/env bash
# Construit l'image ARM64 de diagnostic sans modifier le réseau ni les données.
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
command -v docker >/dev/null || { echo "Docker est requis : bash scripts/preparer-raspberry-pi.sh" >&2; exit 1; }
sudo docker compose version >/dev/null
sudo docker compose -f compose.local.yaml build diagnostic-reseau cache-sqlite importer-sqlite
echo "Images ARM64 de diagnostic et de cache SQLite construites. Aucun service permanent n'a été lancé."

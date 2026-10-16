#!/usr/bin/env bash
# Prépare l'image de diagnostic ARM64 sans modifier Debian ni sa configuration réseau.
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
command -v docker >/dev/null || { echo "Docker est requis. Voir INSTALLATION.md." >&2; exit 1; }
docker compose version >/dev/null
docker compose -f compose.local.yaml build
echo "Image du serveur local prête (diagnostic TCP uniquement)."

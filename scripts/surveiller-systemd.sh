#!/usr/bin/env bash
# Vérification indépendante du résultat du dernier service de synchronisation.
set -Eeuo pipefail
: "${SYNC_PROJECT:?Repertoire du depot absent}"
cd "$SYNC_PROJECT"
docker compose -f compose.local.yaml run --rm -T surveillance-cache

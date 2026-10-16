#!/usr/bin/env bash
# Test de connectivité TCP avec l'image Docker locale (Raspberry Pi).
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
if [[ $# -lt 1 || $# -gt 2 ]]; then
    echo "Utilisation : bash scripts/tester-reseau.sh ADRESSE_IP_ORDINATEUR [PORT]" >&2
    exit 2
fi
docker compose -f compose.local.yaml run --rm diagnostic-reseau "$1" "${2:-5050}"

#!/usr/bin/env bash
# Test TCP entre le Raspberry Pi (client) et l'EliteBook (serveur).
# Ne change ni les services, ni les pare-feu, ni les interfaces.
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

adresse="${1:-}"
port="${2:-5050}"

if [[ -z "$adresse" ]]; then
    echo "Utilisation : bash scripts/tester-reseau.sh ADRESSE_IPV4_CENTRALE [PORT]" >&2
    exit 2
fi

if [[ ! -x build/serveur-local ]]; then
    echo "Client non compilé : lancer bash scripts/installer-serveur-local.sh" >&2
    exit 1
fi

echo "Test TCP vers ${adresse}:${port}"
./build/serveur-local "$adresse" "$port"

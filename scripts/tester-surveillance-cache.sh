#!/usr/bin/env bash
# Tests simulés : aucune modification de l'horloge ou de SQLite.
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
for entree in "0:NORMAL" "899:NORMAL" "900:RETARD" "3599:RETARD" "3600:EXPIRE"; do
  age="${entree%%:*}"
  attendu="${entree##*:}"
  sortie="$(sudo docker compose -f compose.local.yaml run --rm -T surveillance-cache --simuler-age-s "$age")"
  [[ "$sortie" == "CACHE_$attendu "* ]] || {
    echo "ECHEC age=$age : $sortie" >&2; exit 1;
  }
  echo "OK : age=$age secondes => $attendu"
done
echo "Tests temporels reussis sans toucher au reseau, au cache ou aux donnees."

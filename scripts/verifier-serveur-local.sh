#!/usr/bin/env bash
# Vérification non destructive après installation : décisions et fraîcheur.
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
compose=(sudo docker compose -f compose.local.yaml)

# Exiger d'abord un cache synchronisé : ne jamais initialiser des droits fictifs ici.
normal="$("${compose[@]}" run --rm -T surveillance-cache)"
[[ "$normal" == CACHE_NORMAL\ * ]] || {
  echo "Cache indisponible ou périmé : $normal" >&2; exit 1;
}
echo "OK : $normal"
autorise="$("${compose[@]}" run --rm -T cache-sqlite verifier-sync FICTIF-0001 Laboratoire)"
refuse="$("${compose[@]}" run --rm -T cache-sqlite verifier-sync FICTIF-0003 Laboratoire)"
[[ "$autorise" == AUTORISE && "$refuse" == REFUSE ]] || {
  echo "Décisions inattendues : 0001=$autorise; 0003=$refuse" >&2; exit 1;
}
echo "OK : FICTIF-0001 Laboratoire => AUTORISE"
echo "OK : FICTIF-0003 Laboratoire => REFUSE"
for minuteur in controle-acces-synchronisation.timer controle-acces-surveillance.timer; do
  systemctl is-active --quiet "$minuteur" || {
    echo "Minuteur inactif : $minuteur" >&2; exit 1;
  }
  echo "OK : $minuteur actif"
done
echo "Validation locale terminée. Les volumes SQLite n'ont pas été modifiés."

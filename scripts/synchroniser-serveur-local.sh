#!/usr/bin/env bash
# Transfert SSH authentifié; un échec ne doit jamais rafraîchir le cache SQLite.
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage : bash $0 COMPTE@SERVEUR [FICHIER_CLE_PRIVEE]" >&2
  exit 2
fi
cible="$1"
cle="${2:-}"
for outil in ssh docker mktemp; do
  command -v "$outil" >/dev/null || { echo "Commande absente : $outil" >&2; exit 1; }
done
# Une copie temporaire ne sera transmise à SQLite que si SSH a réussi.
umask 077
temporaire="$(mktemp)"
trap 'rm -f "$temporaire"' EXIT
options=(-T -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=5)
if [[ -n "$cle" ]]; then
  options+=(-i "$cle" -o IdentitiesOnly=yes)
fi
ssh "${options[@]}" "$cible" exporter-autorisations > "$temporaire"
# L'export JSON est limité et vérifié à l'importation.
if [[ ! -s "$temporaire" ]]; then
  echo "Export vide : importation annulée." >&2
  exit 1
fi
if [[ "$EUID" == 0 ]]; then
  docker compose -f compose.local.yaml run --rm -T importer-sqlite < "$temporaire"
else
  sudo docker compose -f compose.local.yaml run --rm -T importer-sqlite < "$temporaire"
fi

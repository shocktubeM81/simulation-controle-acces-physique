#!/usr/bin/env bash
# Exécuté par systemd avec droits root, SSH sous un utilisateur non privilégié.
set -Eeuo pipefail
: "${SYNC_USER:?Utilisateur local absent}"
: "${SYNC_TARGET:?Cible SSH absente}"
: "${SYNC_PROJECT:?Répertoire du dépôt absent}"
home="$(getent passwd "$SYNC_USER" | cut -d: -f6)"
[[ -n "$home" ]] || { echo "Utilisateur inconnu" >&2; exit 1; }
cd "$SYNC_PROJECT"
umask 077
instantane="$(mktemp /run/controle-acces/snapshot.XXXXXXXX)"
trap 'rm -f "$instantane"' EXIT
runuser -u "$SYNC_USER" -- ssh -T -o BatchMode=yes \
  -o StrictHostKeyChecking=yes -o IdentitiesOnly=yes \
  -o ConnectTimeout=5 \
  -i "$home/.ssh/id_ed25519_controle_sync" \
  "$SYNC_TARGET" exporter-autorisations > "$instantane"
[[ -s "$instantane" ]] || { echo "Instantané vide : import annulé" >&2; exit 1; }
docker compose -f compose.local.yaml run --rm -T importer-sqlite < "$instantane"

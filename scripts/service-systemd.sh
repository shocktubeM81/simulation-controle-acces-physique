#!/usr/bin/env bash
# Un seul point d'entree pour les deux services periodiques systemd.
set -Eeuo pipefail
[[ "$EUID" -eq 0 ]] || { echo "Service administrateur requis." >&2; exit 1; }
: "${SYNC_PROJECT:?Repertoire du depot absent}"
cd "$SYNC_PROJECT"

case "${1:-}" in
  synchroniser)
    : "${SYNC_USER:?Utilisateur SSH absent}"
    : "${SYNC_TARGET:?Cible SSH absente}"
    home="$(getent passwd "$SYNC_USER" | cut -d: -f6)"
    [[ -n "$home" ]] || { echo "Utilisateur inconnu." >&2; exit 1; }
    # Une connexion interrompue ne doit jamais actualiser le cache.
    umask 077
    instantane="$(mktemp /run/controle-acces/snapshot.XXXXXXXX)"
    trap 'rm -f "$instantane"' EXIT
    runuser -u "$SYNC_USER" -- ssh -T -o BatchMode=yes \
      -o StrictHostKeyChecking=yes -o IdentitiesOnly=yes -o ConnectTimeout=5 \
      -i "$home/.ssh/id_ed25519_controle_sync" \
      "$SYNC_TARGET" exporter-autorisations > "$instantane"
    [[ -s "$instantane" ]] || { echo "Export vide : import annule." >&2; exit 1; }
    docker compose -f compose.local.yaml run --rm -T importer-sqlite < "$instantane"
    ;;
  surveiller)
    docker compose -f compose.local.yaml run --rm -T surveillance-cache
    ;;
  *)
    echo "Usage interne : service-systemd.sh synchroniser|surveiller" >&2
    exit 2
    ;;
esac

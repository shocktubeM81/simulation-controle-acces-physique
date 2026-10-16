#!/usr/bin/env bash
# Installé par root hors du dépôt. Exécute SSH en utilisateur ordinaire.
set -Eeuo pipefail
: "${SYNC_USER:?Utilisateur SSH manquant}"
: "${SYNC_TARGET:?Cible SSH manquante}"
: "${SYNC_PROJECT:?Répertoire projet manquant}"
cd "$SYNC_PROJECT"
# Le fichier SSH est la clé technique dédiée de l'utilisateur; pas d'agent requis.
runuser -u "$SYNC_USER" -- ssh -T -o BatchMode=yes \
  -o StrictHostKeyChecking=yes -o IdentitiesOnly=yes \
  -o ConnectTimeout=5 \
  -i "/home/$SYNC_USER/.ssh/id_ed25519_controle_sync" \
  "$SYNC_TARGET" exporter-autorisations > /run/controle-acces-snapshot.json
docker compose -f compose.local.yaml run --rm -T importer-sqlite \
  < /run/controle-acces-snapshot.json
rm -f /run/controle-acces-snapshot.json

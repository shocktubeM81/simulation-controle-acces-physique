#!/usr/bin/env bash
# Choisit le traitement periodique demandé par systemd.
set -Eeuo pipefail
case "$1" in
  synchroniser) exec /usr/local/libexec/controle-acces/synchroniser-systemd.sh ;;
  surveiller) exec /usr/local/libexec/controle-acces/surveiller-systemd.sh ;;
  *) echo "Commande interne inconnue." >&2; exit 2 ;;
esac

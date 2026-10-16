#!/usr/bin/env bash
# Construit l'image ARM64 de diagnostic sans modifier le réseau ni les données.
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
command -v docker >/dev/null || { echo "Docker est requis : bash scripts/preparer-raspberry-pi.sh" >&2; exit 1; }
sudo docker compose version >/dev/null
sudo docker compose -f compose.local.yaml build diagnostic-reseau cache-sqlite importer-sqlite surveillance-cache
echo "Images locales construites."
if [[ -f /etc/controle-acces/synchronisation.conf ]]; then
  echo "Mise a jour des services systemd du projet..."
  configuration=/etc/controle-acces/synchronisation.conf
  utilisateur="$(sudo sed -n 's/^SYNC_USER=//p' "$configuration")"
  cible="$(sudo sed -n 's/^SYNC_TARGET=//p' "$configuration")"
  [[ -n "$utilisateur" && -n "$cible" ]] || { echo "Configuration systemd incomplete." >&2; exit 1; }
  sudo bash scripts/installer-timer-raspberry-pi.sh "$utilisateur" "$cible"
  sudo bash scripts/installer-surveillance.sh
fi

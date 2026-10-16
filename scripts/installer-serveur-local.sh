#!/usr/bin/env bash
# Reconstruit le laboratoire Raspberry Pi et met à jour les unités déjà configurées.
# Ne modifie ni le réseau système ni les volumes de données.
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
command -v docker >/dev/null || { echo "Docker est requis : bash scripts/preparer-raspberry-pi.sh" >&2; exit 1; }
sudo docker compose version >/dev/null
sudo docker compose -f compose.local.yaml build diagnostic-reseau cache-sqlite
echo "Images locales construites."
if [[ -f /etc/controle-acces/synchronisation.conf ]]; then
  echo "Mise a jour des services systemd du projet..."
  configuration=/etc/controle-acces/synchronisation.conf
  utilisateur="$(sudo sed -n 's/^SYNC_USER=//p' "$configuration")"
  cible="$(sudo sed -n 's/^SYNC_TARGET=//p' "$configuration")"
  [[ -n "$utilisateur" && -n "$cible" ]] || { echo "Configuration systemd incomplete." >&2; exit 1; }
  sudo bash scripts/installer-timer-raspberry-pi.sh "$utilisateur" "$cible"
  sudo bash scripts/installer-surveillance.sh
else
  echo "Première installation : configurer et valider la clé SSH dédiée avant d'activer les minuteurs."
fi

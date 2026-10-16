#!/usr/bin/env bash
# Installation/reinstallation idempotente du moniteur.
# Active automatiquement le timer uniquement si le timer de synchronisation
# est déjà actif et après validation des tests simulés.
set -Eeuo pipefail
[[ "${EUID}" -eq 0 ]] || { echo "Utiliser sudo." >&2; exit 1; }
cd "$(dirname "${BASH_SOURCE[0]}")/.."
[[ -f /etc/controle-acces/synchronisation.conf ]] || {
  echo "Configuration de synchronisation absente : installer d'abord le timer de synchronisation." >&2
  exit 1
}
for entree in "0:NORMAL" "900:RETARD" "3600:EXPIRE"; do
  age="${entree%%:*}"; attendu="${entree##*:}"
  sortie="$(docker compose -f compose.local.yaml run --rm -T surveillance-cache --simuler-age-s "$age")"
  [[ "$sortie" == "CACHE_$attendu "* ]] || {
    echo "Test de seuil echoue : $sortie" >&2; exit 1;
  }
done
install -d -o root -g root -m 0755 /usr/local/libexec/controle-acces
install -o root -g root -m 0755 scripts/surveiller-systemd.sh \
  /usr/local/libexec/controle-acces/surveiller-systemd.sh
install -o root -g root -m 0644 systemd/controle-acces-surveillance.service \
  /etc/systemd/system/controle-acces-surveillance.service
install -o root -g root -m 0644 systemd/controle-acces-surveillance.timer \
  /etc/systemd/system/controle-acces-surveillance.timer
systemctl daemon-reload
systemctl start controle-acces-surveillance.service
if systemctl is-active --quiet controle-acces-synchronisation.timer; then
  systemctl enable --now controle-acces-surveillance.timer
  echo "Surveillance installee, testee et activee (toutes les minutes)."
else
  echo "Surveillance installee et testee, mais timer non active : synchronisation inactive."
fi

#!/usr/bin/env bash
# Préparer le timer; ne jamais l'activer avant un test réussi de l'identité restreinte.
set -Eeuo pipefail
[[ "${EUID}" == 0 ]] || { echo "Utiliser sudo." >&2; exit 1; }
[[ $# == 2 ]] || { echo "Usage : sudo bash $0 UTILISATEUR_LOCAL COMPTE_EXPORT@ORDINATEUR" >&2; exit 2; }
utilisateur="$1"; cible="$2"
[[ "$utilisateur" =~ ^[a-z_][a-z0-9_-]*$ ]] || exit 2
[[ "$cible" =~ ^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+$ ]] || exit 2
getent passwd "$utilisateur" >/dev/null || { echo "Utilisateur local absent." >&2; exit 1; }
cd "$(dirname "${BASH_SOURCE[0]}")/.."
projet="$(pwd -P)"
[[ "$projet" != *'"'* && "$projet" != *'$'* && "$projet" != *'\\'* ]] || { echo "Chemin invalide." >&2; exit 1; }
home="$(getent passwd "$utilisateur" | cut -d: -f6)"
[[ -f "$home/.ssh/id_ed25519_controle_sync" ]] || { echo "Clé technique absente." >&2; exit 1; }
# Ne pas activer un timer avec une identité inconnue ou une clé SSH non validée.
echo "Vérification préalable de l'identité SSH restreinte..."
runuser -u "$utilisateur" -- ssh -T -o BatchMode=yes -o StrictHostKeyChecking=yes \
  -o IdentitiesOnly=yes -o ConnectTimeout=5 \
  -i "$home/.ssh/id_ed25519_controle_sync" "$cible" exporter-autorisations \
  | python3 -c 'import sys,json; data=json.load(sys.stdin); assert data["schema_version"] == 1'
install -d -o root -g root -m 0700 /etc/controle-acces
printf 'SYNC_USER=%s\nSYNC_TARGET=%s\nSYNC_PROJECT="%s"\n' \
  "$utilisateur" "$cible" "$projet" > /etc/controle-acces/synchronisation.conf
chmod 0600 /etc/controle-acces/synchronisation.conf
install -d -o root -g root -m 0755 /usr/local/libexec/controle-acces
install -o root -g root -m 0755 scripts/synchroniser-systemd.sh \
  /usr/local/libexec/controle-acces/synchroniser-systemd.sh
install -o root -g root -m 0644 systemd/controle-acces-synchronisation.service \
  /etc/systemd/system/controle-acces-synchronisation.service
install -o root -g root -m 0644 systemd/controle-acces-synchronisation.timer \
  /etc/systemd/system/controle-acces-synchronisation.timer
systemctl daemon-reload
echo "Unités installées, mais timer NON activé."
echo "Tester : sudo systemctl start controle-acces-synchronisation.service"
echo "Puis : sudo systemctl status controle-acces-synchronisation.service"
echo "Après validation : sudo systemctl enable --now controle-acces-synchronisation.timer"

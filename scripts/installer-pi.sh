#!/usr/bin/env bash
# Installation et mise à jour du serveur local Raspberry Pi (Debian ARM64).
set -Eeuo pipefail
cd "$(dirname "$0")/.."

erreur() { printf 'Erreur : %s\n' "$*" >&2; exit 1; }

preparer_docker() {
  if command -v docker >/dev/null && sudo docker compose version >/dev/null 2>&1; then
    return
  fi
  [[ "$(uname -m)" == "aarch64" ]] || erreur "Système ARM64 requis."
  . /etc/os-release
  [[ "${VERSION_CODENAME:-}" == "trixie" ]] || erreur "Installation Docker prévue pour Debian 13 (trixie)."
  if command -v docker >/dev/null; then
    erreur "Docker présent, Compose absent : vérifier l'installation avant toute modification."
  fi
  for paquet in docker.io docker-compose podman-docker containerd runc; do
    if dpkg-query -W -f='${Status}' "$paquet" 2>/dev/null | grep -q 'install ok installed'; then
      erreur "Paquet potentiellement conflictuel : $paquet."
    fi
  done
  sudo apt-get update
  sudo apt-get install -y ca-certificates curl
  sudo install -m 0755 -d /etc/apt/keyrings
  sudo curl --fail --silent --show-error --location \
    https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
  sudo chmod a+r /etc/apt/keyrings/docker.asc
  sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/debian
Suites: ${VERSION_CODENAME}
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
  sudo apt-get update
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  sudo systemctl enable --now docker
  sudo docker compose version
}

preparer_cle() {
  [[ "$EUID" -ne 0 ]] || erreur "Créer la clé avec le compte utilisateur, sans sudo."
  local cle="$HOME/.ssh/id_ed25519_controle_sync"
  umask 077
  mkdir -p "$HOME/.ssh"
  if [[ -e "$cle" || -e "$cle.pub" ]]; then
    [[ -f "$cle" && -f "$cle.pub" ]] ||
      erreur "Clé SSH incomplète : aucune clé existante remplacée."
    echo "Clé de synchronisation existante conservée."
  else
    ssh-keygen -q -t ed25519 -N '' -f "$cle" -C "controle-acces-sync"
    echo "Nouvelle clé SSH de synchronisation créée."
  fi
  echo "Clé publique : $cle.pub"
}

configurer() {
  [[ "$EUID" -eq 0 ]] || erreur "Utiliser sudo pour installer systemd."
  [[ $# -eq 2 ]] || erreur "Usage : sudo bash scripts/installer-pi.sh configurer UTILISATEUR COMPTE@HOTE"
  local utilisateur="$1" cible="$2" projet home configuration age attendu sortie entree nom extension
  [[ "$utilisateur" =~ ^[a-z_][a-z0-9_-]*$ ]] || erreur "Utilisateur invalide."
  [[ "$cible" =~ ^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+$ ]] || erreur "Cible SSH invalide."
  getent passwd "$utilisateur" >/dev/null || erreur "Utilisateur local absent."
  projet="$(pwd -P)"
  [[ "$projet" != *'"'* && "$projet" != *'$'* && "$projet" != *'\'* && "$projet" != *$'\n'* ]] ||
    erreur "Chemin du projet incompatible avec le fichier de configuration."
  home="$(getent passwd "$utilisateur" | cut -d: -f6)"
  [[ -f "$home/.ssh/id_ed25519_controle_sync" ]] || erreur "Clé de synchronisation absente."

  # L'export doit être authentifié et décodable avant la pose des unités.
  echo "Vérification de l'identité SSH restreinte..."
  runuser -u "$utilisateur" -- ssh -T -o BatchMode=yes -o StrictHostKeyChecking=yes \
    -o IdentitiesOnly=yes -o ConnectTimeout=5 \
    -i "$home/.ssh/id_ed25519_controle_sync" "$cible" exporter-autorisations |
    python3 -c 'import sys,json; data=json.load(sys.stdin); assert data["schema_version"] == 1'

  # Les seuils sont testés sans modifier la base ni l'horloge.
  for entree in 0:NORMAL 900:RETARD 3600:EXPIRE; do
    age="${entree%%:*}"; attendu="${entree##*:}"
    sortie="$(docker compose -f compose.local.yaml run --rm -T surveillance-cache --simuler-age-s "$age")"
    [[ "$sortie" == "CACHE_$attendu "* ]] || erreur "Test temporel échoué : $sortie"
  done

  install -d -o root -g root -m 0700 /etc/controle-acces
  configuration=/etc/controle-acces/synchronisation.conf
  printf 'SYNC_USER=%s\nSYNC_TARGET=%s\nSYNC_PROJECT="%s"\n' \
    "$utilisateur" "$cible" "$projet" > "$configuration"
  chmod 0600 "$configuration"
  install -d -o root -g root -m 0755 /usr/local/libexec/controle-acces
  install -o root -g root -m 0755 scripts/service-systemd.sh \
    /usr/local/libexec/controle-acces/service-systemd.sh
  for nom in synchronisation surveillance; do
    for extension in service timer; do
      install -o root -g root -m 0644 "systemd/controle-acces-$nom.$extension" \
        "/etc/systemd/system/controle-acces-$nom.$extension"
    done
  done
  systemctl daemon-reload

  if systemctl is-active --quiet controle-acces-synchronisation.timer; then
    systemctl start controle-acces-surveillance.service
    systemctl enable --now controle-acces-surveillance.timer
    echo "Unités actualisées : les deux minuteurs restent actifs."
  else
    echo "Unités prêtes; minuteurs non activés automatiquement."
    echo "Tester : sudo systemctl start controle-acces-synchronisation.service"
    echo "Après validation : sudo systemctl enable --now controle-acces-synchronisation.timer"
    echo "Puis : sudo systemctl enable --now controle-acces-surveillance.timer"
  fi
}

installer() {
  [[ "$EUID" -ne 0 ]] || erreur "Exécuter l'installation sans sudo."
  preparer_docker
  # Toutes les tâches locales utilisent cette image Docker commune.
  sudo docker compose -f compose.local.yaml build diagnostic-reseau cache-sqlite
  preparer_cle
  if sudo test -f /etc/controle-acces/synchronisation.conf; then
    local utilisateur cible configuration=/etc/controle-acces/synchronisation.conf
    utilisateur="$(sudo sed -n 's/^SYNC_USER=//p' "$configuration")"
    cible="$(sudo sed -n 's/^SYNC_TARGET=//p' "$configuration")"
    [[ -n "$utilisateur" && -n "$cible" ]] || erreur "Configuration de synchronisation incomplète."
    sudo bash scripts/installer-pi.sh configurer "$utilisateur" "$cible"
  else
    echo "Premier déploiement : installer la clé publique au central, puis configurer systemd."
  fi
}

case "${1:-installer}" in
  installer) [[ $# -le 1 ]] || erreur "Usage : bash scripts/installer-pi.sh"; installer ;;
  configurer) shift; configurer "$@" ;;
  *) erreur "Usage : bash scripts/installer-pi.sh [installer] ou sudo bash scripts/installer-pi.sh configurer UTILISATEUR COMPTE@HOTE" ;;
esac

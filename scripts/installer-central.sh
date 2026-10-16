#!/usr/bin/env bash
# Installer le serveur central ou autoriser une clé SSH pour l'export fictif.
set -Eeuo pipefail
cd "$(dirname "$0")/.."

erreur() { echo "Erreur : $*" >&2; exit 1; }

preparer_secrets() {
  command -v openssl >/dev/null || erreur "OpenSSL requis."
  umask 077
  mkdir -p secrets
  [[ -e secrets/postgres.txt ]] || openssl rand -hex 32 > secrets/postgres.txt
  [[ -e secrets/api.txt ]] || openssl rand -hex 32 > secrets/api.txt
  if [[ ! -e .env.docker.api ]]; then
    printf 'PGRST_DB_URI=postgres://api_authentificateur:%s@base-de-donnees:5432/controle_acces_simulation\n' \
      "$(cat secrets/api.txt)" > .env.docker.api
  fi
  chmod 0600 secrets/postgres.txt secrets/api.txt .env.docker.api
}

installer_serveur() {
  [[ "$EUID" -ne 0 ]] || erreur "Exécuter avec l'utilisateur autorisé à Docker, sans sudo."
  command -v docker >/dev/null || erreur "Docker requis."
  docker compose version >/dev/null
  preparer_secrets
  docker compose up -d --wait base-de-donnees
  docker compose exec -T -u 0 base-de-donnees sh /opt/laboratoire/docker/initialiser-api.sh
  docker compose exec -T -u 0 base-de-donnees \
    psql -v ON_ERROR_STOP=1 -U postgres -d controle_acces_simulation \
    -c "NOTIFY pgrst, 'reload schema';"
  docker compose up -d interface-api
  for tentative in {1..10}; do
    if bash scripts/verifier.sh central >/dev/null 2>&1; then
      bash scripts/verifier.sh central
      echo "Serveur central prêt."
      return 0
    fi
    sleep 2
  done
  docker compose ps
  docker compose logs --tail=30 interface-api || true
  erreur "API non validée après 10 essais."
}

installer_export() {
  [[ "$EUID" -eq 0 ]] || erreur "Utiliser sudo pour le compte export."
  [[ $# -eq 1 && -f "$1" && -r "$1" ]] ||
    erreur "Usage : sudo bash scripts/installer-central.sh export CHEMIN_CLE_PUBLIQUE"
  local identite commande home fichier attendu
  identite="$(cat "$1")"
  [[ "$identite" =~ ^ssh-ed25519[[:space:]]+[A-Za-z0-9+/=]+([[:space:]].*)?$ ]] ||
    erreur "Clé publique ED25519 invalide."
  commande="/usr/local/libexec/controle-acces/exporter-autorisations"
  install -d -o root -g root -m 0755 /usr/local/libexec/controle-acces
  install -o root -g root -m 0755 scripts/exporter-autorisations-ssh.sh "$commande"
  if ! id -u controle-export >/dev/null 2>&1; then
    useradd --system --create-home --home-dir /var/lib/controle-export \
      --shell /bin/sh --user-group controle-export
  fi
  # Autoriser les clés SSH tout en interdisant le mot de passe.
  usermod --password "*" controle-export
  home="$(getent passwd controle-export | cut -d: -f6)"
  [[ "$home" == "/var/lib/controle-export" ]] || erreur "Répertoire de controle-export inattendu."
  install -d -o controle-export -g controle-export -m 0700 "$home/.ssh"
  fichier="$home/.ssh/authorized_keys"
  attendu="restrict,command=\"$commande\" $identite"
  if [[ -e "$fichier" ]]; then
    [[ "$(cat "$fichier")" == "$attendu" ]] ||
      erreur "Le compte possède une configuration SSH différente : aucune modification."
  else
    printf '%s\n' "$attendu" > "$fichier"
  fi
  chown controle-export:controle-export "$fichier"
  chmod 0600 "$fichier"
  echo "Identité SSH restreinte installée."
}

case "${1:-serveur}" in
  serveur) [[ $# -le 1 ]] || erreur "Usage : bash scripts/installer-central.sh"; installer_serveur ;;
  export) shift; installer_export "$@" ;;
  *) erreur "Usage : installer-central.sh [serveur] | export CHEMIN_CLE_PUBLIQUE" ;;
esac

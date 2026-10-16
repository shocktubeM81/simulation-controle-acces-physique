#!/usr/bin/env bash
# Installer un compte système restreint, puis autoriser UNE clé publique dédiée.
# Usage : sudo bash scripts/installer-acces-export-central.sh /chemin/cle.pub
set -Eeuo pipefail
[[ "$EUID" == 0 ]] || { echo "Exécuter avec sudo" >&2; exit 1; }
[[ $# == 1 && -r "$1" ]] || { echo "Usage : sudo bash $0 /chemin/cle.pub" >&2; exit 2; }
cd "$(dirname "${BASH_SOURCE[0]}")/.."
identite="$(cat "$1")"
[[ "$identite" =~ ^ssh-ed25519[[:space:]]+[A-Za-z0-9+/=]+([[:space:]].*)?$ ]] || {
  echo "Clé publique ED25519 invalide." >&2; exit 1;
}
commande="/usr/local/libexec/controle-acces/exporter-autorisations"
install -d -m 0755 /usr/local/libexec/controle-acces
install -o root -g root -m 0755 scripts/exporter-autorisations-ssh.sh "$commande"
if ! id -u controle-export >/dev/null 2>&1; then
  useradd --system --create-home --home-dir /var/lib/controle-export \
    --shell /bin/sh --user-group controle-export
fi
# Le champ de mot de passe « * » ne peut pas authentifier par mot de passe,
# mais évite le statut de compte verrouillé qui peut bloquer une clé publique.
usermod --password "*" controle-export
home="$(getent passwd controle-export | cut -d: -f6)"
[[ "$home" == "/var/lib/controle-export" ]] || {
  echo "Compte controle-export existant avec un autre répertoire : intervention nécessaire." >&2; exit 1;
}
install -d -o controle-export -g controle-export -m 0700 "$home/.ssh"
# Le compte ne peut pas modifier authorized_keys. Ne jamais écraser
# les autres clés sans vérification explicite.
fichier="$home/.ssh/authorized_keys"
ligne_attendue="restrict,command=\"$commande\" $identite"
if [[ -e "$fichier" ]]; then
  if [[ "$(cat "$fichier")" != "$ligne_attendue" ]]; then
    echo "Le fichier $fichier contient une autre configuration." >&2
    echo "Aucune clé modifiée. Examiner son contenu avant toute correction." >&2
    exit 1
  fi
  echo "La clé restreinte attendue est déjà installée."
else
  printf '%s\n' "$ligne_attendue" > "$fichier"
fi
chown controle-export:controle-export "$fichier"
chmod 0600 "$fichier"
echo "Clé restreinte installée pour controle-export."
echo "Une demande SSH exécute uniquement l'export; aucun terminal ni tunnel n'est autorisé."

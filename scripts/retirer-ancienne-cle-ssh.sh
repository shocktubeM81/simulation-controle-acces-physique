#!/usr/bin/env bash
# Retire uniquement la clé PUBLIQUE temporaire du projet du compte personnel.
# Par défaut : aperçu; appliquer avec --appliquer après vérification.
# Usage (sur l'ordinateur central, SANS sudo) :
#   bash scripts/retirer-ancienne-cle-ssh.sh ~/ancienne-cle.pub
#   bash scripts/retirer-ancienne-cle-ssh.sh ~/ancienne-cle.pub --appliquer
set -Eeuo pipefail

erreur() { printf 'ERREUR : %s\n' "$*" >&2; exit 1; }

[[ "${EUID}" -ne 0 ]] || erreur "Exécuter avec le compte personnel, sans sudo."
[[ $# -ge 1 && $# -le 2 ]] || erreur "Usage : bash $0 ANCIENNE_CLE_PUBLIQUE [--appliquer]"
[[ $# -ne 2 || "$2" == "--appliquer" ]] || erreur "Seule l'option --appliquer est acceptée."
[[ -f "$1" && -r "$1" && ! -L "$1" ]] || erreur "Fichier de clé publique introuvable ou non régulier : $1"
command -v ssh-keygen >/dev/null || erreur "ssh-keygen est requis."

# Refuser la nouvelle clé de service et les clés personnelles sans marqueur
# de projet : on ne doit retirer que l'ancienne clé de laboratoire.
read -r type cle commentaire reste < "$1" || true
[[ "$type" == "ssh-ed25519" && "$cle" =~ ^[A-Za-z0-9+/=]+$ \
   && "$commentaire" == "simulation-controle-acces" && -z "${reste:-}" ]] \
  || erreur "Cette clé ne correspond pas à l'ancienne identité simulation-controle-acces."

dossier="$HOME/.ssh"
autorise="$dossier/authorized_keys"
[[ -d "$dossier" && -f "$autorise" && ! -L "$autorise" ]] \
  || erreur "Fichier authorized_keys introuvable ou lien symbolique : aucune modification."

# Chercher le couple exact 'ssh-ed25519 BASE64' (avec ou sans options SSH).
# Un seul résultat est permis afin d'éviter toute suppression ambiguë.
nombre="$(awk -v cible="$cle" '
  { for (i=1; i<NF; i++) if ($i=="ssh-ed25519" && $(i+1)==cible) { n++; break } }
  END { print n+0 }
' "$autorise")"
[[ "$nombre" -eq 1 ]] || erreur "Nombre de correspondances : $nombre (attendu : 1). Aucune modification."

empreinte="$(ssh-keygen -lf "$1" -E sha256)"
printf 'Clé temporaire à retirer : %s\n' "$empreinte"
printf 'Fichier concerné : %s\n' "$autorise"
printf 'Correspondance unique trouvée; les autres entrées seront conservées.\n'

if [[ "${2:-}" != "--appliquer" ]]; then
  echo "APERÇU uniquement. Relancer avec --appliquer pour effectuer le retrait."
  exit 0
fi

umask 077
copie="$(mktemp "$dossier/authorized_keys.sauvegarde.XXXXXXXX")"
temporaire="$(mktemp "$dossier/authorized_keys.nouveau.XXXXXXXX")"
trap 'rm -f -- "$temporaire"' EXIT
cp -p -- "$autorise" "$copie"
awk -v cible="$cle" '
  {
    supprimer=0
    for (i=1; i<NF; i++) {
      if ($i=="ssh-ed25519" && $(i+1)==cible) { supprimer=1; break }
    }
    if (!supprimer) print
  }
' "$autorise" > "$temporaire"
chmod 0600 "$temporaire"
mv -f -- "$temporaire" "$autorise"
trap - EXIT
echo "Clé temporaire retirée du seul compte $(id -un)."
echo "Sauvegarde locale (mode privé) : $copie"
echo "Vérifier l'échec de l'ancienne clé, puis le succès de l'identité controle-export."

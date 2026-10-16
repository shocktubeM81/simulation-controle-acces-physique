#!/usr/bin/env bash
# Clé technique séparée, sans phrase secrète, exclusivement pour une commande SSH forcée.
set -Eeuo pipefail
cle="$HOME/.ssh/id_ed25519_controle_sync"
umask 077
mkdir -p "$HOME/.ssh"
if [[ -e "$cle" || -e "$cle.pub" ]]; then
    echo "Une clé de synchronisation existe déjà; aucune clé remplacée."
else
    ssh-keygen -q -t ed25519 -N '' -f "$cle" -C "controle-acces-sync"
    echo "Clé créée; installer uniquement la clé publique sur le serveur central."
fi
echo "Clé publique à copier vers le serveur central :"
cat "$cle.pub"
echo "La clé privée reste sur le Raspberry Pi (permissions 600)."

#!/usr/bin/env bash
# Installation reproductible du serveur local sur Raspberry Pi (Debian ARM64).
# Ne change ni le réseau, ni SSH, ni les comptes utilisateurs.
set -Eeuo pipefail

journal() { printf '\n==> %s\n' "$*"; }
erreur() { printf 'ERREUR : %s\n' "$*" >&2; exit 1; }

racine="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$racine"

[[ -r /etc/os-release ]] || erreur "Impossible d'identifier le système."
# shellcheck disable=SC1091
source /etc/os-release
[[ "${ID:-}" == "debian" || "${ID_LIKE:-}" == *debian* ]] || erreur "Script prévu pour Debian ou un système dérivé."
[[ "$(uname -m)" == "aarch64" ]] || erreur "Architecture non prise en charge ici : $(uname -m) (ARM64 attendu)."
command -v sudo >/dev/null || erreur "sudo est requis."
command -v apt-get >/dev/null || erreur "APT est requis."

journal "Système : ${PRETTY_NAME:-Linux} — $(uname -m)"
journal "Installation des dépendances (réexécutable)"
sudo apt-get update
sudo apt-get install -y git ca-certificates build-essential cmake sqlite3 libsqlite3-dev

journal "Compilation des programmes C++"
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 2

journal "Vérification des exécutables"
test -x build/serveur-local || erreur "Exécutable build/serveur-local absent."
test -x build/serveur-central || erreur "Exécutable build/serveur-central absent."

journal "Informations réseau (aucune modification)"
ip -br -4 addr
ip route

journal "Versions installées"
cmake --version | head -n 1
sqlite3 --version | head -n 1

journal "Installation du serveur local terminée."
printf 'Pour tester la connexion : ./build/serveur-local ADRESSE_IPV4_ELITEBOOK 5050\n'
printf 'Le test requiert un serveur TCP en écoute sur l\x27EliteBook.\n'

#!/usr/bin/env bash
# Prépare Docker sur Raspberry Pi OS / Debian 13 ARM64, sans modifier SSH ni le réseau.
set -Eeuo pipefail

erreur() { echo "Erreur : $*" >&2; exit 1; }
[[ "$(uname -m)" == "aarch64" ]] || erreur "Un système ARM64 est requis."
source /etc/os-release
[[ "${VERSION_CODENAME:-}" == "trixie" ]] || erreur "Ce script vise Debian 13 (trixie). Voir les instructions officielles pour un autre système."

if command -v docker >/dev/null && sudo docker compose version >/dev/null 2>&1; then
    echo "Docker et Compose sont déjà disponibles."
    exit 0
fi
if command -v docker >/dev/null; then
    erreur "Docker est déjà installé mais Compose est absent ou inaccessible : vérifier manuellement avant de modifier les paquets."
fi

for paquet in docker.io docker-compose podman-docker containerd runc; do
    if dpkg-query -W -f='${Status}' "$paquet" 2>/dev/null | grep -q "install ok installed"; then
        erreur "Paquet potentiellement conflictuel déjà installé : $paquet. Vérifier avant toute modification."
    fi
done

echo "Installation de Docker depuis le dépôt officiel, avec vérification de signature APT."
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl --fail --silent --show-error --location \
  https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Utiliser l'architecture de la machine et le nom de la distribution.
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
sudo docker version
sudo docker compose version
echo "Docker et Compose sont installés. Utiliser sudo docker pour les commandes du laboratoire."

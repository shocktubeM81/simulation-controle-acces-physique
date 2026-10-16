#!/usr/bin/env bash
# Test de la persistance SQLite sur plusieurs exécutions de conteneurs éphémères.
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
compose=(sudo docker compose -f compose.local.yaml)
echo "Initialisation idempotente du cache SQLite fictif..."
"${compose[@]}" run --rm cache-sqlite initialiser
echo "Vérification des décisions..."
autorise=$("${compose[@]}" run --rm -T cache-sqlite verifier FICTIF-0001 Laboratoire)
refuse=$("${compose[@]}" run --rm -T cache-sqlite verifier FICTIF-0003 Laboratoire)
[[ "$autorise" == "AUTORISE" ]] || { echo "ERREUR : autorisation inattendue : $autorise" >&2; exit 1; }
[[ "$refuse" == "REFUSE" ]] || { echo "ERREUR : refus inattendu : $refuse" >&2; exit 1; }
echo "OK : FICTIF-0001 -> $autorise"
echo "OK : FICTIF-0003 -> $refuse"
echo "OK : données accessibles après arrêt et recréation des conteneurs."
echo "Ce test utilise des données fictives statiques et un fichier SQLite DISTINCT du cache synchronisé."

#!/usr/bin/env bash
# Vérifie les deux décisions attendues de l'API locale et son interface d'écoute.
set -Eeuo pipefail

for outil in curl ss; do
  command -v "$outil" >/dev/null || { echo "Commande absente : $outil" >&2; exit 1; }
done

verifier() {
  local code="$1"
  local attendu="$2"
  local reponse
  reponse="$(curl --fail --silent --show-error --max-time 5 \
    -X POST http://127.0.0.1:3000/rpc/verifier_acces \
    -H 'Content-Type: application/json' \
    -d "{\"code_identifiant\":\"$code\",\"nom_porte\":\"Laboratoire\"}")"

  if [[ "$reponse" == "[{\"decision\":\"$attendu\"}]" ]]; then
    printf 'OK : %s -> %s\n' "$code" "$attendu"
  else
    printf 'ERREUR : %s : résultat inattendu : %s\n' "$code" "$reponse" >&2
    exit 1
  fi
}

verifier FICTIF-0001 AUTORISE
verifier FICTIF-0003 REFUSE

ecoutes="$(ss -H -ltn '( sport = :3000 )')"
if [[ "$ecoutes" == *"127.0.0.1:3000"* ]] && [[ "$ecoutes" != *"0.0.0.0:3000"* ]] && [[ "$ecoutes" != *"[::]:3000"* ]]; then
  echo "OK : PostgREST est limité à 127.0.0.1:3000"
else
  printf 'ERREUR : interface d’écoute inattendue :\n%s\n' "$ecoutes" >&2
  exit 1
fi
echo 'Tous les essais sont réussis.'

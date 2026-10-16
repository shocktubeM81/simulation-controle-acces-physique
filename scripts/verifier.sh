#!/usr/bin/env bash
# Verifications reproductibles sans modifier les autorisations synchronisees.
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

erreur() { echo "ECHEC : $*" >&2; exit 1; }

central() {
  local code attendu reponse ecoutes
  for paire in FICTIF-0001:AUTORISE FICTIF-0003:REFUSE; do
    code="${paire%%:*}"; attendu="${paire##*:}"
    reponse="$(curl --fail --silent --show-error --max-time 5 \
      -X POST http://127.0.0.1:3000/rpc/verifier_acces \
      -H 'Content-Type: application/json' \
      -d "{\"code_identifiant\":\"$code\",\"nom_porte\":\"Laboratoire\"}")"
    [[ "$reponse" == "[{\"decision\":\"$attendu\"}]" ]] || erreur "$code : $reponse"
    echo "OK : $code => $attendu"
  done
  ecoutes="$(ss -H -ltn '( sport = :3000 )')"
  [[ "$ecoutes" == *"127.0.0.1:3000"* && "$ecoutes" != *"0.0.0.0:3000"* && "$ecoutes" != *"[::]:3000"* ]] ||
    erreur "API non limitee a 127.0.0.1:3000."
  echo "OK : PostgREST local seulement."
}

pi() {
  local age autorise refuse minuteur
  age="$(sudo docker compose -f compose.local.yaml run --rm -T surveillance-cache)"
  [[ "$age" == CACHE_NORMAL\ * ]] || erreur "Cache perime ou absent : $age"
  echo "OK : $age"
  autorise="$(sudo docker compose -f compose.local.yaml run --rm -T cache-sqlite verifier-sync FICTIF-0001 Laboratoire)"
  refuse="$(sudo docker compose -f compose.local.yaml run --rm -T cache-sqlite verifier-sync FICTIF-0003 Laboratoire)"
  [[ "$autorise" == AUTORISE && "$refuse" == REFUSE ]] || erreur "Decisions inattendues."
  echo "OK : FICTIF-0001 AUTORISE, FICTIF-0003 REFUSE"
  for minuteur in controle-acces-synchronisation.timer controle-acces-surveillance.timer; do
    systemctl is-active --quiet "$minuteur" || erreur "Minuteur inactif : $minuteur"
    echo "OK : $minuteur actif"
  done
}

seuils() {
  local entree age attendu sortie
  for entree in 0:NORMAL 899:NORMAL 900:RETARD 3599:RETARD 3600:EXPIRE; do
    age="${entree%%:*}"; attendu="${entree##*:}"
    sortie="$(sudo docker compose -f compose.local.yaml run --rm -T surveillance-cache --simuler-age-s "$age")"
    [[ "$sortie" == "CACHE_$attendu "* ]] || erreur "Age $age : $sortie"
    echo "OK : age=$age => $attendu"
  done
}

cache_statique() {
  local autorise refuse
  # Les donnees de demonstration sont dans un autre fichier SQLite.
  sudo docker compose -f compose.local.yaml run --rm -T cache-sqlite initialiser
  autorise="$(sudo docker compose -f compose.local.yaml run --rm -T cache-sqlite verifier FICTIF-0001 Laboratoire)"
  refuse="$(sudo docker compose -f compose.local.yaml run --rm -T cache-sqlite verifier FICTIF-0003 Laboratoire)"
  [[ "$autorise" == AUTORISE && "$refuse" == REFUSE ]] || erreur "Cache statique incorrect."
  echo "OK : cache statique distinct du cache synchronise."
}

journal_evenements() {
  # Tests sur bases temporaires seulement; aucun evenement d'exploitation ajoute.
  sudo docker compose -f compose.local.yaml run --rm --no-deps -T \
    --entrypoint python3 journal-evenements \
    -B /usr/local/share/controle-acces/tests/test_journal_evenements.py
}

certificats_journal() {
  # Autorites et cles de test ephemeres uniquement, sans acces reseau.
  python3 -B serveur-local/tests/test_certificats_journal.py
}

case "${1:-}" in
  central) [[ $# -eq 1 ]] || erreur "Usage : verifier.sh central"; central ;;
  pi) [[ $# -eq 1 ]] || erreur "Usage : verifier.sh pi"; pi ;;
  certificats-journal) [[ $# -eq 1 ]] || erreur "Usage : verifier.sh certificats-journal"; certificats_journal ;;
  journal) [[ $# -eq 1 ]] || erreur "Usage : verifier.sh journal"; journal_evenements ;;
  seuils) [[ $# -eq 1 ]] || erreur "Usage : verifier.sh seuils"; seuils ;;
  cache-statique) [[ $# -eq 1 ]] || erreur "Usage : verifier.sh cache-statique"; cache_statique ;;
  reseau)
    [[ $# -ge 2 && $# -le 3 ]] || erreur "Usage : verifier.sh reseau IP [PORT]"
    sudo docker compose -f compose.local.yaml run --rm diagnostic-reseau "$2" "${3:-5050}"
    ;;
  *) erreur "Usage : verifier.sh central|pi|seuils|cache-statique|journal|certificats-journal|reseau IP [PORT]" ;;
esac

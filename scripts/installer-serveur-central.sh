#!/usr/bin/env bash
# Installe ou vérifie le laboratoire central, sans effacer les données existantes.
set -Eeuo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

BASE="controle_acces_simulation"
PROPRIETAIRE="${UTILISATEUR_BD:-$USER}"
CONFIG=".env.api"

journal() { printf '\n==> %s\n' "$*"; }
erreur() { printf 'ERREUR : %s\n' "$*" >&2; exit 1; }

for outil in psql createdb sudo openssl docker curl cmake; do
    command -v "$outil" >/dev/null || erreur "Commande manquante : $outil. Voir INSTALLATION.md."
done
docker compose version >/dev/null || erreur "Docker Compose est absent."
[[ "$PROPRIETAIRE" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]] || erreur "Nom de rôle PostgreSQL invalide."
git check-ignore -q "$CONFIG" || erreur "$CONFIG n'est pas exclu par .gitignore."
[[ -t 0 ]] || erreur "L'installation doit être exécutée dans un terminal interactif."

journal "Vérification du rôle PostgreSQL : $PROPRIETAIRE"
if [[ "$(sudo -u postgres psql -d postgres -Atqc "SELECT 1 FROM pg_roles WHERE rolname = '$PROPRIETAIRE'")" != "1" ]]; then
    erreur "Le rôle $PROPRIETAIRE n'existe pas. Le créer selon INSTALLATION.md."
fi

journal "Vérification de la base $BASE"
if [[ "$(sudo -u postgres psql -d postgres -Atqc "SELECT 1 FROM pg_database WHERE datname = '$BASE'")" != "1" ]]; then
    sudo -u postgres createdb --owner="$PROPRIETAIRE" "$BASE"
    journal "Base créée"
else
    journal "Base existante conservée"
fi

journal "Installation non destructive de la structure SQL"
psql -h 127.0.0.1 -U "$PROPRIETAIRE" -d "$BASE" \
    -v ON_ERROR_STOP=1 -f base-de-donnees/structure.sql

journal "Vérification des données fictives"
compte="$(psql -h 127.0.0.1 -U "$PROPRIETAIRE" -d "$BASE" -At -v ON_ERROR_STOP=1 \
    -c "SELECT (SELECT count(*) FROM personnes) + (SELECT count(*) FROM identifiants) + (SELECT count(*) FROM portes) + (SELECT count(*) FROM autorisations)")"

if [[ "$compte" == "0" ]]; then
    psql -h 127.0.0.1 -U "$PROPRIETAIRE" -d "$BASE" \
        -v ON_ERROR_STOP=1 -f base-de-donnees/donnees-fictives.sql
else
    journal "Données existantes conservées ($compte lignes au total)"
fi

journal "Installation des rôles techniques"
sudo -u postgres psql -d "$BASE" -v ON_ERROR_STOP=1 \
    -f base-de-donnees/roles-api.sql

journal "Installation de la fonction de décision (API)"
psql -h 127.0.0.1 -U "$PROPRIETAIRE" -d "$BASE" \
    -v ON_ERROR_STOP=1 -f base-de-donnees/interface-api.sql

if [[ ! -e "$CONFIG" ]]; then
    journal "Création d'un mot de passe technique aléatoire et de $CONFIG"
    mot_de_passe="$(openssl rand -hex 32)"
    # Le secret n'est transmis à PostgreSQL que par l'entrée standard.
    printf "ALTER ROLE api_authentificateur PASSWORD '%s';\n" "$mot_de_passe" \
        | sudo -u postgres psql -d "$BASE" -v ON_ERROR_STOP=1 >/dev/null

    umask 077
    printf 'PGRST_DB_URI=postgres://api_authentificateur:%s@127.0.0.1:5432/%s\n' \
        "$mot_de_passe" "$BASE" > "$CONFIG"
    chmod 600 "$CONFIG"
    unset mot_de_passe
else
    [[ -f "$CONFIG" ]] || erreur "$CONFIG existe mais n'est pas un fichier ordinaire."
    chmod 600 "$CONFIG"
    journal "$CONFIG existe déjà : secret et configuration conservés"
fi

journal "Démarrage de PostgREST"
docker compose up -d --remove-orphans

journal "Vérification de l'API locale (jusqu'à 15 tentatives)"
reussi=0
for tentative in $(seq 1 15); do
    reponse="$(curl --max-time 2 -fsS -X POST http://127.0.0.1:3000/rpc/verifier_acces \
        -H 'Content-Type: application/json' \
        -d '{"code_identifiant":"FICTIF-0001","nom_porte":"Laboratoire"}' 2>/dev/null)" || true
    if [[ "$reponse" == *'"decision":"AUTORISE"'* ]]; then
        reussi=1
        break
    fi
    sleep 1
done

if [[ "$reussi" != "1" ]]; then
    docker compose ps
    erreur "L'API ne répond pas comme prévu. Consulter : docker compose logs --tail=50 interface-api"
fi

journal "Installation validée : décision AUTORISE sur http://127.0.0.1:3000"
printf 'Pour tester un refus, consulter documentation/interface-api.md.\n'

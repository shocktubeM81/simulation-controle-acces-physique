# Interface API — installation Docker

Le serveur central est constitué de deux conteneurs Docker Compose : PostgreSQL (réseau privé uniquement) et PostgREST (exposé uniquement à `127.0.0.1:3000`).

Depuis la racine du dépôt, sur l'ordinateur :

```bash
bash scripts/installer-central.sh
docker compose ps
bash scripts/verifier.sh central
```

Les fichiers `base-de-donnees/structure.sql` et `donnees-fictives.sql` initialisent le volume PostgreSQL lors de sa première création. Ensuite, à chaque installation, le script attend que PostgreSQL soit disponible et applique `docker/configurer-roles-api.sql` et `base-de-donnees/interface-api.sql`. Cette deuxième phase est relançable, notamment après une interruption. Les fichiers de configuration SQL sont montés par dossiers plutôt qu'individuellement : les modifications récupérées par Git restent visibles dans le conteneur. Les données fictives existantes sont conservées.

Le rôle de connexion PostgREST peut uniquement passer au rôle `api_anonyme`. Celui-ci dispose du droit d'exécuter une seule fonction de vérification des autorisations, et ne possède aucun accès direct aux tables. La fonction utilise un rôle propriétaire technique distinct, doté uniquement des droits nécessaires.

Les secrets se trouvent uniquement dans `secrets/` et `.env.docker.api`, hors du suivi Git. PostgREST reçoit toutefois son URI de connexion dans l'environnement du conteneur; cet environnement peut être consulté par une personne ayant accès à Docker. L'accès à Docker doit donc rester restreint.

Les API HTTP locales ne disposent **pas encore d'authentification client**. Ne pas rendre le port accessible au réseau local ou à Internet.

### Vérifications manuelles

```bash
curl -fsS -X POST http://127.0.0.1:3000/rpc/verifier_acces \
  -H 'Content-Type: application/json' \
  -d '{"code_identifiant":"FICTIF-0001","nom_porte":"Laboratoire"}'
```

Résultat attendu : `[{"decision":"AUTORISE"}]`.

### Maintenance

```bash
docker compose logs --tail=50
docker compose down
```

Pour supprimer volontairement toutes les données fictives du volume de ce projet :

```bash
docker compose down --volumes
```

Cette commande est destructive pour les données du laboratoire. Voir également [INSTALLATION.md](../INSTALLATION.md).

# Interface réseau expérimentale — PostgREST

L'API utilise le logiciel libre PostgREST au lieu d'un serveur HTTP écrit sur mesure. La base PostgreSQL reste installée sur Ubuntu; seul PostgREST fonctionne en conteneur Docker.

**Portée : laboratoire local seulement.** Dans cette première version, l'API accepte les requêtes sans authentification HTTP, mais écoute exclusivement sur `127.0.0.1:3000`. Il ne faut ni publier ce port sur Internet, ni changer son adresse d'écoute pour `0.0.0.0`. Avant une utilisation sur le réseau du Raspberry Pi, nous ajouterons une authentification et une protection du transport adaptées.

## 1. Préparer les rôles de base de données

Depuis la racine du dépôt :

```bash
sudo -u postgres psql -d controle_acces_simulation -v ON_ERROR_STOP=1 \
  -f base-de-donnees/roles-api.sql
```

Définir ensuite le mot de passe du compte technique **sans l'écrire dans Git** :

```bash
sudo -u postgres psql -d controle_acces_simulation
```

Dans l'invite `psql`, saisir :

```text
\password api_authentificateur
\q
```

Choisir pour ce laboratoire un mot de passe long composé de lettres et de chiffres, sans caractères nécessitant un encodage dans une URL.

## 2. Installer la fonction exposée par l'API

```bash
psql -h 127.0.0.1 -U david -d controle_acces_simulation \
  -v ON_ERROR_STOP=1 -f base-de-donnees/interface-api.sql
```

Seule la fonction `api.verifier_acces` est accessible au rôle `api_anonyme`. Aucun droit de lecture des tables `public` n'est accordé à ce rôle. La fonction s'exécute avec les droits de son propriétaire pour calculer uniquement la décision.

## 3. Configurer la connexion locale

Créer sur l'EliteBook un fichier de configuration **privé**, à la racine du dépôt :

```bash
nano .env.api
```

Y inscrire une ligne en remplaçant `REMPLACER_MOT_DE_PASSE` par le mot de passe choisi à l'étape 1 :

```dotenv
PGRST_DB_URI=postgres://api_authentificateur:REMPLACER_MOT_DE_PASSE@127.0.0.1:5432/controle_acces_simulation
```

Puis restreindre les permissions :

```bash
chmod 600 .env.api
```

Le fichier `.env.api` figure dans `.gitignore` et **ne doit jamais être publié**. Si le mot de passe contient des caractères spéciaux, la valeur de connexion URI doit être correctement encodée.

## 4. Démarrer PostgREST

```bash
docker compose up -d
docker compose ps
docker compose logs --tail=30 interface-api
```

Le service `interface-api` est accessible uniquement depuis l'EliteBook à l'adresse `http://127.0.0.1:3000`.

## 5. Tester les décisions d'accès

Accès autorisé :

```bash
curl -sS -X POST http://127.0.0.1:3000/rpc/verifier_acces \
  -H 'Content-Type: application/json' \
  -d '{"code_identifiant":"FICTIF-0001","nom_porte":"Laboratoire"}'
```

Réponse attendue :

```json
[{"decision":"AUTORISE"}]
```

Accès refusé :

```bash
curl -sS -X POST http://127.0.0.1:3000/rpc/verifier_acces \
  -H 'Content-Type: application/json' \
  -d '{"code_identifiant":"FICTIF-0003","nom_porte":"Laboratoire"}'
```

Réponse attendue :

```json
[{"decision":"REFUSE"}]
```

Pour voir les codes de statut et les erreurs HTTP, ajouter `-i` à `curl`.

## 6. Arrêter le service

```bash
docker compose down
```

Cette commande arrête PostgREST, mais n'efface **pas** la base PostgreSQL sur Ubuntu.

## Limites

- Aucune authentification de client API pour le moment : utilisation sur `localhost` uniquement.
- Aucun mécanisme d'identification cryptographique des cartes fictives.
- Aucune ouverture vers le Raspberry Pi tant qu'un contrôle d'accès réseau et une authentification appropriés ne sont pas en place.
- PostgREST est un composant standard réutilisé; le code C++ initial reste un banc d'essai TCP indépendant.

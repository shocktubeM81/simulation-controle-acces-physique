# Installation de la simulation de contrôle d'accès

Ce laboratoire utilise un **ordinateur Linux** (serveur central) et un **Raspberry Pi 4** (serveur local). Les données sont fictives; le prototype ne doit pas commander une porte réelle.

## Exigences

| Machine | Matériel | Logiciels |
|---|---|---|
| Ordinateur central | Ordinateur Linux, stockage pour Docker, connexion réseau | Ubuntu/Debian, Git, Docker Engine + Compose, OpenSSL, curl, OpenSSH Server, `ss` |
| Raspberry Pi | Raspberry Pi 4, alimentation stable, stockage, réseau IP | Debian 13 ARM64 (trixie), Git, OpenSSH Client, Python 3, sudo; Docker installé par le script |
| Contrôleur | Aucun pour cette phase | ESP32 prévu ultérieurement |

Les deux machines doivent avoir une heure synchronisée et le Raspberry Pi doit pouvoir se connecter au **port SSH** du central. Le port de PostgREST (3000) reste accessible exclusivement sur `127.0.0.1` du central.

## 1. Installer le serveur central

Prérequis : Docker Engine et Docker Compose disponibles pour l'utilisateur de connexion.

```bash
git clone https://github.com/shocktubeM81/simulation-controle-acces-physique.git
cd simulation-controle-acces-physique
bash scripts/installer-central.sh
bash scripts/verifier.sh central
```

Le script prépare les secrets localement, sans les publier, puis lance PostgreSQL et PostgREST.

## 2. Préparer le Raspberry Pi

```bash
git clone https://github.com/shocktubeM81/simulation-controle-acces-physique.git
cd simulation-controle-acces-physique
bash scripts/installer-pi.sh
```

Le script installe Docker et Compose si nécessaires sur Debian 13 ARM64, construit les images et crée une paire SSH dédiée si elle est absente. Les clés déjà présentes ne sont pas remplacées.

## 3. Autoriser l'export SSH

**Sur le Pi**, remplacer `COMPTE_CENTRAL` et `IP_CENTRAL` par les valeurs de l'ordinateur :

```bash
scp ~/.ssh/id_ed25519_controle_sync.pub COMPTE_CENTRAL@IP_CENTRAL:~/controle-sync.pub
```

**Sur l'ordinateur central**, depuis le dépôt :

```bash
sudo bash scripts/installer-central.sh export ~/controle-sync.pub
```

Cette commande crée `controle-export`, limité à l'export des autorisations fictives. Le mot de passe de connexion ne donne pas accès à ce compte.

**Sur le Pi**, vérifier l'empreinte de l'hôte distant, puis tester :

```bash
ssh -T -o BatchMode=yes -o IdentitiesOnly=yes \
  -i ~/.ssh/id_ed25519_controle_sync \
  controle-export@IP_CENTRAL exporter-autorisations
```

La réponse attendue est un document JSON fictif, avec `schema_version` égal à 1.

## 4. Activer le fonctionnement périodique

**Sur le Pi** :

```bash
sudo bash scripts/installer-pi.sh configurer "$(id -un)" controle-export@IP_CENTRAL
sudo systemctl start controle-acces-synchronisation.service
sudo systemctl status controle-acces-synchronisation.service --no-pager
```

**Seulement après la réussite de cette première synchronisation**, activer les minuteurs :

```bash
sudo systemctl enable --now controle-acces-synchronisation.timer
sudo systemctl enable --now controle-acces-surveillance.timer
bash scripts/verifier.sh pi
```

La synchronisation est planifiée environ toutes les 5 minutes; la surveillance s'exécute environ toutes les minutes. Les seuils simulés sont documentés dans `documentation/politique-synchronisation.md`.

## 5. Mettre à jour une installation existante

Depuis le dépôt correspondant, sur chaque machine :

```bash
git pull --ff-only origin main
```

Puis, sur le central : `bash scripts/installer-central.sh`.

Sur le Raspberry Pi :

```bash
bash scripts/installer-pi.sh
bash scripts/verifier.sh pi
```

L'installateur réutilise la configuration SSH existante, met à jour les unités `systemd` et conserve les volumes SQLite. Pour tester une **branche**, sélectionner cette branche avec Git au lieu de tirer `main`.

## 6. Diagnostics facultatifs

Sur le Pi :

```bash
bash scripts/verifier.sh seuils
bash scripts/verifier.sh cache-statique
```

Pour le banc d'essai TCP historique, démarrer le serveur C++ de diagnostic sur l'ordinateur, puis lancer sur le Pi :

```bash
bash scripts/verifier.sh reseau IP_CENTRAL 5050
```

Le cache statique et le test TCP sont indépendants des décisions du cache synchronisé.

## Sécurité et limites

- Ne jamais publier `secrets/`, `.env.docker.api` ou les clés privées.
- Ne jamais utiliser `docker compose down --volumes` pour une mise à jour ordinaire : cela supprime les données persistantes.
- Les services `systemd` appellent Docker avec les droits root depuis un dépôt modifiable par l'utilisateur : **prototype académique uniquement**.
- Le Wi-Fi/Ethernet vers un futur ESP32 n'est pas encore implémenté.

Voir `documentation/conventions-code.md` pour l'organisation des programmes C++ et les critères de commentaires.

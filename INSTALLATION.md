# Installation de la simulation

Deux appareils sous Linux sont prévus : un **ordinateur** (serveur central) et un **Raspberry Pi** (serveur local). Le logiciel s'installe sans configuration liée au nom des appareils. Le dépôt est public; **les secrets restent locaux**.

## Prérequis

- Sur l'ordinateur : Linux (Debian ou Ubuntu), Docker avec le module Compose, Git et OpenSSL.
- Sur le Raspberry Pi : Debian ou Raspberry Pi OS 64 bits, accès SSH et réseau fonctionnel.
- Les appareils doivent pouvoir communiquer sur un réseau local de confiance.

## 1. Ordinateur — serveur central

```bash
git clone https://github.com/shocktubeM81/simulation-controle-acces-physique.git
cd simulation-controle-acces-physique
bash scripts/installer-serveur-central.sh
```

Le script génère des secrets, démarre PostgreSQL et PostgREST dans Docker, crée les données fictives à la première exécution et vérifie les autorisations. Il n'installe **rien dans PostgreSQL de l'ordinateur**.

Si le dépôt existe déjà : `git pull --ff-only`, puis relancer le script.

Vérification ultérieure :

```bash
bash scripts/verifier-installation.sh
```

Arrêter les services sans perdre les données :

```bash
docker compose down
```

**Réinitialiser uniquement les données de simulation :**

```bash
docker compose down --volumes
bash scripts/installer-serveur-central.sh
```

⚠️ `--volumes` efface définitivement **les données du volume Docker de ce projet**. Ne pas utiliser cette option pour simplement arrêter les services.

## 2. Raspberry Pi — serveur local

```bash
git clone https://github.com/shocktubeM81/simulation-controle-acces-physique.git
cd simulation-controle-acces-physique
bash scripts/preparer-raspberry-pi.sh
bash scripts/installer-serveur-local.sh
```

Le premier script installe Docker Engine et Compose depuis le dépôt officiel sur Debian 13 ARM64 si nécessaire; il exige `sudo` et ne modifie pas la configuration SSH. Le second construit l'image de diagnostic. Examiner le script avant de l'exécuter; les autres distributions demandent une adaptation.

Cette image contient le client C++ de diagnostic réseau et un premier prototype autonome de cache SQLite (autorisations fictives et statiques). Pour vérifier les décisions et la persistance du volume entre conteneurs :

```bash
bash scripts/tester-sqlite-local.sh
```

La **synchronisation** des permissions, leur expiration et la communication authentifiée avec le serveur central restent à développer. Le moteur Docker et Compose doivent préalablement être installés sur le Raspberry Pi.

## 3. Essai réseau (facultatif)

Sur l'ordinateur, identifier son adresse Ethernet avec `ip -br -4 addr`, puis démarrer :

```bash
./build/serveur-central ADRESSE_IPV4_ORDINATEUR 5050
```

Pour obtenir l'exécutable sur l'ordinateur, installer CMake et un compilateur C++, puis lancer `cmake -S . -B build && cmake --build build`. Ce banc d'essai TCP n'est pas un service de sécurité et doit rester sur un réseau local de confiance.

Depuis le Raspberry Pi :

```bash
sudo docker compose -f compose.local.yaml run --rm diagnostic-reseau ADRESSE_IPV4_ORDINATEUR 5050
```

L'adresse est un paramètre de la commande et n'est pas inscrite dans le code.

## 4. Migration depuis l'ancien laboratoire

Si un ancien PostgREST fonctionne déjà sur le port 3000, l'arrêter **avant le premier démarrage** de la nouvelle configuration. Ne pas supprimer l'ancienne base PostgreSQL tant que le déploiement Docker n'a pas été testé.

Les anciens fichiers `.env.api` et les anciennes bases installées sur l'hôte ne sont pas employés par le nouveau Compose. Ils peuvent être retirés séparément après validation.

## Sécurité et limites

- L'API de démonstration est accessible seulement sur `127.0.0.1:3000`.
- PostgreSQL est privé au réseau Docker, sans port publié sur l'ordinateur.
- Les secrets locaux (`secrets/`, `.env.docker.api`) sont ignorés par Git.
- La communication sécurisée entre l'ordinateur et le Raspberry Pi **reste à concevoir** avant d'ouvrir l'API au réseau.

Détails : [architecture et sécurité](documentation/securite.md), [Raspberry Pi](documentation/raspberry-pi.md), [interface API](documentation/interface-api.md).

## 5. Synchronisation expérimentale (première version)

Sur **l'ordinateur**, après `git pull --ff-only origin main`, réexécuter :

```bash
bash scripts/installer-serveur-central.sh
curl --fail --silent --show-error -X POST \
  http://127.0.0.1:3000/rpc/exporter_autorisations
```

La réponse attendue est un document JSON contenant `schema_version`,
`captured_at`, `personnes`, `portes`, `identifiants` et `autorisations`.
Ce document contient uniquement les données fictives du laboratoire.

Sur le **Raspberry Pi**, après `git pull --ff-only origin main` :

```bash
bash scripts/installer-serveur-local.sh
bash scripts/tester-sqlite-local.sh
```

Vérifier d'abord que le Raspberry Pi peut établir une connexion **SSH
authentifiée par clé** vers l'ordinateur. Examiner l'empreinte de la clé
du serveur lors de la première connexion (ne pas accepter une empreinte
inconnue sans vérification). La synchronisation fonctionne en mode
`BatchMode=yes`, **sans saisie interactive de mot de passe SSH**.
Les clés SSH ne doivent pas être publiées dans GitHub.

```bash
bash scripts/synchroniser-serveur-local.sh UTILISATEUR@ADRESSE_ORDINATEUR
sudo docker compose -f compose.local.yaml run --rm cache-sqlite \
  verifier-sync FICTIF-0001 Laboratoire
sudo docker compose -f compose.local.yaml run --rm cache-sqlite \
  verifier-sync FICTIF-0003 Laboratoire
```

**Sécurité :** le port 3000 central reste attaché à `127.0.0.1`;
il n'est pas ouvert au réseau du Raspberry Pi. Le Raspberry Pi utilise SSH
et une commande `curl` exécutée à distance pour obtenir les données.
Le conteneur SQLite lui-même n'a aucun accès réseau.

**Limites :** prototype manuel, données fictives, pas d'ordonnancement
automatique des synchronisations, compte SSH distant non restreint et
politique de révocation à améliorer. Voir
[politique et sécurité](documentation/politique-synchronisation.md).

## 6. Connexion SSH restreinte et synchronisation périodique

La configuration précédente avec un compte SSH personnel est réservée au
diagnostic. Pour automatiser, utiliser une **nouvelle** identité limitée à
l'export fictif. Le timer **n'est pas activé automatiquement**.

Sur le Raspberry Pi, après mise à jour du dépôt :

```bash
bash scripts/preparer-cle-synchronisation.sh
scp ~/.ssh/id_ed25519_controle_sync.pub david@ADRESSE_ORDINATEUR:~/controle-sync.pub
```

Sur l'ordinateur, mettre à jour le dépôt puis :

```bash
sudo bash scripts/installer-acces-export-central.sh ~/controle-sync.pub
```

Cette étape crée `controle-export` avec une clé `authorized_keys` forcée à
exécuter uniquement l'export de PostgREST sur boucle locale. Ne jamais y
copier une clé privée. Les autres clés SSH du compte personnel ne sont pas
modifiées automatiquement.

De retour sur le Raspberry Pi, vérifier la nouvelle identité :

```bash
ssh -T -o BatchMode=yes -o IdentitiesOnly=yes \
  -i ~/.ssh/id_ed25519_controle_sync \
  controle-export@ADRESSE_ORDINATEUR exporter-autorisations
```

La réponse doit contenir un JSON fictif. Ensuite, pour préparer
l'automatisation :

```bash
sudo bash scripts/installer-timer-raspberry-pi.sh \
  "$(id -un)" controle-export@ADRESSE_ORDINATEUR
sudo systemctl start controle-acces-synchronisation.service
sudo systemctl status controle-acces-synchronisation.service --no-pager
```

Si ce lancement manuel est réussi, activer la périodicité :

```bash
sudo systemctl enable --now controle-acces-synchronisation.timer
systemctl list-timers controle-acces-synchronisation.timer
```

Consulter les journaux :

```bash
sudo journalctl -u controle-acces-synchronisation.service -n 40 --no-pager
```

L'ancien accès libre du Raspberry Pi au compte personnel reste actif jusqu'à
ce que **l'ancienne clé** soit retirée manuellement de
`~/.ssh/authorized_keys` sur l'ordinateur. Ne retirer que la ligne concernée
après avoir validé la clé restreinte et le service.

**Limite de ce prototype :** le timer s'exécute en root pour Docker et charge
les fichiers Compose depuis un dépôt modifiable par l'utilisateur. Ce modèle
ne convient pas à une production sans durcissement. Les valeurs temporelles
sont des hypothèses de simulation; voir
[politique de synchronisation](documentation/politique-synchronisation.md).

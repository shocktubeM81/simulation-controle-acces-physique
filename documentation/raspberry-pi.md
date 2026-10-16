# Mise en service du Raspberry Pi 4 — serveur local

Cette procédure est destinée au Raspberry Pi 4 du laboratoire de simulation de contrôle d'accès. Elle ne modifie pas la configuration du serveur central sur l'EliteBook.

## Objectif de cette première étape

- Démarrer un Raspberry Pi 4 sous Linux.
- L'intégrer au réseau local, de préférence par Ethernet.
- Accéder à son terminal par SSH depuis l'EliteBook.
- Vérifier qu'il dispose de son propre environnement (ARM64, adresse IP, stockage).

**La synchronisation des autorisations et le réseau de production ne sont pas encore configurés.** L'API PostgREST sur l'EliteBook doit continuer à n'écouter que sur `127.0.0.1:3000`.

## Installation automatisée sur le Raspberry Pi existant

Si le Raspberry Pi possède déjà Debian, une connexion SSH et une connexion Internet, l'installation de l'environnement logiciel peut être automatisée.

Sur le Raspberry Pi (et non sur l'EliteBook) :

```bash
sudo apt-get update
sudo apt-get install -y git
mkdir -p ~/projets
cd ~/projets
git clone https://github.com/shocktubeM81/simulation-controle-acces-physique.git
cd simulation-controle-acces-physique
bash scripts/installer-serveur-local.sh
```

Si le dépôt est déjà cloné, ne pas le cloner une deuxième fois. Se placer dans son dossier, récupérer les mises à jour et relancer le script :

```bash
cd ~/projets/simulation-controle-acces-physique
git pull --ff-only origin main
bash scripts/installer-serveur-local.sh
```

Le script vérifie Debian et l'architecture ARM64, installe Git, CMake, le compilateur C++ et SQLite, puis compile les deux programmes et affiche l'état du réseau. Il peut être relancé sans réinstaller le système ni toucher à la configuration SSH ou au réseau.

**Important :** cette automatisation prépare l'environnement; elle ne lance aucun service permanent et ne configure pas encore la synchronisation avec PostgreSQL. Le test TCP entre les deux machines sera effectué séparément.

---

## 1. Choisir le système d'exploitation

Si le Raspberry Pi possède déjà un système Linux fonctionnel avec SSH, **ne pas le réinstaller** : passer à l'étape 3.

Pour une nouvelle installation, utiliser **Raspberry Pi OS Lite (64 bits)**, sans interface graphique, avec une carte microSD (ou un autre support de démarrage compatible).

Sur un autre ordinateur, installer [Raspberry Pi Imager](https://www.raspberrypi.com/software/) et choisir :

- Appareil : Raspberry Pi 4 ;
- Système : Raspberry Pi OS Lite (64 bits) ;
- Stockage : support destiné au Raspberry Pi (**son contenu sera effacé**).

Dans les réglages de personnalisation d'Imager :

- Nom de la machine : `controle-acces-local` ;
- Nom d'utilisateur : `david` (ou un autre nom, à réutiliser dans les commandes) ;
- Mot de passe local fort ;
- Fuseau horaire : `America/Toronto` ;
- SSH : activé, avec **authentification par clé publique** de préférence ;
- Ethernet : connexion recommandée (aucun mot de passe Wi-Fi à configurer si elle est utilisée).

Pour copier la clé publique SSH de l'EliteBook dans l'outil Imager :

```bash
cat ~/.ssh/id_ed25519.pub
```

Copier **uniquement la clé publique** affichée, jamais `~/.ssh/id_ed25519` (clé privée).

## 2. Brancher l'équipement

Insérer le support préparé, brancher le Raspberry Pi par Ethernet au réseau de laboratoire (ou au même réseau local que l'EliteBook), puis raccorder son alimentation.

Laisser le démarrage se terminer avant d'effectuer les vérifications SSH.

## 3. Tester depuis l'EliteBook

Sur l'EliteBook :

```bash
getent hosts controle-acces-local.local
ping -c 3 controle-acces-local.local
ssh david@controle-acces-local.local
```

Si le nom `.local` ne se résout pas, obtenir l'adresse IPv4 du Raspberry Pi depuis la liste DHCP du routeur, puis se connecter directement :

```bash
ssh david@ADRESSE_IP_DU_PI
```

Si le compte utilisateur est différent, remplacer `david`.

Au premier contact SSH, vérifier l'empreinte de la clé hôte du Raspberry Pi avant de l'accepter. Une erreur `Permission denied (publickey)` signifie généralement que la clé publique autorisée ou le nom d'utilisateur ne correspond pas.

## 4. Vérifier le Raspberry Pi après connexion SSH

Les commandes suivantes s'exécutent **sur le Raspberry Pi**, après connexion SSH :

```bash
hostnamectl
uname -m
ip -br addr
ip route
df -h /
```

Pour une installation 64 bits, `uname -m` devrait indiquer `aarch64`.

Mettre à jour le système :

```bash
sudo apt update
sudo apt upgrade
```

Si une mise à jour exige un redémarrage, l'effectuer avant de poursuivre.

## 5. Installer uniquement les outils initiaux

Sur le Raspberry Pi :

```bash
sudo apt install -y git cmake g++ sqlite3 libsqlite3-dev
```

Il n'est pas nécessaire d'installer PostgreSQL, PostgREST ou Docker sur le Raspberry Pi pour l'instant.

## 6. Tester la connexion entre les deux machines

Sur l'EliteBook, obtenir l'adresse IPv4 de son interface Ethernet :

```bash
ip -br -4 addr
```

Lorsque l'interface Ethernet est identifiée, démarrer le serveur de diagnostic TCP avec **l'adresse de cette interface** et non `127.0.0.1` :

```bash
./build/serveur-central ADRESSE_ETHERNET_ELITEBOOK 5050
```

Sur le Raspberry Pi, cloner le dépôt (HTTPS en lecture seule si aucune clé GitHub n'est configurée) :

```bash
git clone https://github.com/shocktubeM81/simulation-controle-acces-physique.git
cd simulation-controle-acces-physique
cmake -S . -B build
cmake --build build
./build/serveur-local ADRESSE_ETHERNET_ELITEBOOK 5050
```

Ce test ne doit être exécuté que sur un réseau local de confiance. Si un pare-feu bloque le port, adapter de façon restrictive sa configuration à l'adresse IP du Raspberry Pi. Ne jamais rediriger le port 5050 vers Internet.

## Suite

Après validation de SSH et du réseau physique, nous créerons une base SQLite locale et définirons la synchronisation des autorisations. L'accès distant à l'API centrale nécessitera un mécanisme d'authentification des clients et de protection des communications avant toute ouverture de PostgREST.

Référence : [documentation officielle Raspberry Pi](https://www.raspberrypi.com/documentation/computers/getting-started.html).

## Test réseau automatisé

Une fois le serveur central démarré sur l'EliteBook avec `./build/serveur-central 10.0.0.106 5050`, lancer depuis le Raspberry Pi :

```bash
git pull --ff-only origin main
bash scripts/tester-reseau.sh 10.0.0.106 5050
```

Le script utilise le client C++ déjà compilé et confirme la connexion ainsi que l'accusé de réception. Il ne démarre pas lui-même le serveur central et ne modifie pas le réseau. Les adresses du laboratoire sont des exemples de configuration locale et pourront changer si le serveur DHCP leur en attribue d'autres.

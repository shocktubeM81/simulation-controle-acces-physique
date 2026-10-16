# Simulation d'une architecture de contrôle d'accès physique

Projet étudiant de simulation d'un **système de contrôle d'accès physique distribué**, reposant sur des données fictives et des technologies libres. Le dépôt documente à la fois l'architecture logicielle et le banc d'essai matériel pour faciliter les essais, la validation et la reproduction.

> **Portée :** démonstrateur académique. Il ne constitue pas un système homologué ou prêt à contrôler une porte réelle.

## 1. Architecture

| Niveau | Rôle | Implémentation actuelle ou envisagée |
| --- | --- | --- |
| **Serveur central** | Gestion des données fictives, des autorisations et de leur exportation | Ordinateur Linux, PostgreSQL et PostgREST dans Docker Compose |
| **Serveur local** | Conservation d'un cache d'autorisations, synchronisation et vérifications locales | Raspberry Pi, SQLite, synchronisation SSH restreinte et minuteurs systemd |
| **Microcontrôleur de démonstration** | Interface d'affichage et expérimentation des communications avec le serveur local | Waveshare ESP32-C6-LCD-1.47; test LCD validé, communications à développer |
| **Entrées/sorties de porte** | Lecture d'identifiant, détection d'état et commande d'un actionneur de démonstration | Étape future; éventuellement un second ESP32 sans écran |

La **décision d'autorisation** doit provenir du serveur local et de son cache; l'ESP32 ne doit pas devenir une copie autonome de la base d'autorisations. Une première interface HTTP/JSON sur le réseau local est envisagée, mais n'est **pas encore implémentée**. Voir [la conception du contrôleur ESP32](documentation/controleur-esp32.md).

Les outils historiques de diagnostic TCP et de cache SQLite statique restent distincts du cache d'autorisations synchronisé `autorisations-synchronisees.sqlite3`.

## 2. Matériel

### 2.1. Configuration de référence du laboratoire

Les équipements ci-dessous constituent la **configuration effectivement retenue pour les essais**. Ces références servent à reproduire les résultats et à identifier les contraintes matérielles; elles **ne sont pas des exigences exclusives** de l'architecture.

| Équipement | Modèle ou version de référence | Usage | État |
| --- | --- | --- | --- |
| Ordinateur central | **HP EliteBook 840 G6**, architecture x86-64 | Hébergement du serveur central et environnement de développement | Utilisé |
| Serveur local | **Raspberry Pi 4**, architecture ARM64 | Cache local, synchronisation et futurs échanges IP avec le contrôleur | Utilisé |
| Carte de prototypage | **Waveshare ESP32-C6-LCD-1.47**, version standard, sans connecteurs à broches présoudés | Premiers essais d'interface et de communication | Affichage LCD autonome validé |
| Réseau | Réseau IP local entre le central et le Raspberry Pi; Wi-Fi 2,4 GHz prévu pour l'ESP32 | Communication entre les niveaux | Partie central ↔ Pi utilisée; liaison ESP32 à développer |

**Détails à relever pour une reproduction stricte :** capacité RAM et révision du Raspberry Pi 4, révision matérielle de la carte Waveshare (si indiquée), versions du micrologiciel ESP32 et références des futurs périphériques. Ces valeurs ne sont pas inventées lorsqu'elles n'ont pas encore été vérifiées.

### 2.2. Waveshare ESP32-C6-LCD-1.47

**Référence de la carte actuellement disponible :** `ESP32-C6-LCD-1.47` (SKU Waveshare **28563**, sans suffixe `-M`). Il s'agit de la carte avec écran, et **non** de la variante tactile ni d'un ESP32 DevKit générique.

- **Microcontrôleur de l’exemplaire testé :** Espressif **ESP32-C6FH8**, révision silicium **v0.2**, architecture RISC-V, jusqu’à 160 MHz.
- **Mémoire flash détectée :** **8 Mo**, confirmés avec `esptool flash_id`. La fiche constructeur consultée décrit une variante de 4 Mo; vérifier la puce et la capacité de chaque exemplaire.
- **Écran :** LCD TFT couleur de 1,47 po, résolution **172 × 320 pixels**, contrôleur **ST7789**, interface SPI; **non tactile**.
- **Communications sans fil :** Wi-Fi 2,4 GHz (Wi-Fi 6) et Bluetooth Low Energy 5; IEEE 802.15.4 également pris en charge par l'ESP32-C6.
- **Connexion et alimentation :** port USB-C, utilisable pour la programmation et l'alimentation de la carte.
- **Périphériques intégrés :** emplacement microSD/TF, DEL RGB, boutons `BOOT` et `RST`.
- **Entrées/sorties :** broches GPIO accessibles sur la carte; l'écran emploie notamment **GPIO6/7** (SPI), **GPIO14/15** (CS/DC) et **GPIO21/22** (RST/rétroéclairage). Le lecteur microSD partage GPIO6/7 et utilise GPIO4 (CS) et GPIO5 (MISO); la DEL RGB utilise GPIO8. Vérifier les fonctions et conflits de brochage avant d'ajouter des périphériques.
- **État du projet :** test LCD compilé, téléversé et validé après coupure d’alimentation. Affichage autonome à 50 % de luminosité; Wi-Fi, microSD, LED RGB et communications Raspberry Pi non testés par ce programme.

Documentation constructeur : [ESP32-C6-LCD-1.47 — Waveshare](https://docs.waveshare.com/ESP32-C6-LCD-1.47). Le schéma et le brochage du constructeur doivent être consultés avant tout raccordement. Waveshare recommande de **limiter le rétroéclairage à 50 %** pour éviter une surchauffe de l'écran.

### 2.3. Périphériques et évolutions envisagés — non requis actuellement

- **Second ESP32 sans écran (modèle à sélectionner) :** acquisition des entrées physiques et commande de sorties pour une ou deux portes fictives.
- **Lecteur RFID/NFC (modèle à sélectionner) :** lecture d'identifiants de démonstration; un module PN532 pourrait être étudié.
- **Capteur de porte :** contact magnétique ou interrupteur simulant l'ouverture et la fermeture.
- **Signalisation :** DEL ou lampe basse tension indiquant une autorisation, un refus ou un état de fonctionnement.
- **Actionneur :** relais ou interface de commande adaptée pour simuler une serrure ou un contacteur; **aucune charge secteur ni serrure réelle** n'est prévue au stade initial.
- **Variantes réseau :** Ethernet ou PoE, ou remplacement d'un équipement par un matériel aux capacités équivalentes.

Les GPIO de l'ESP32 utilisent une logique **3,3 V** : une bobine de relais, de contacteur ou une charge de puissance ne doit jamais être raccordée directement à une broche. Prévoir un circuit d'interface, des protections et une alimentation adaptés à l'actionneur.

## 3. Logiciels et dépendances

Les versions ci-dessous décrivent la **configuration de référence** ou, lorsqu'il s'agit de conteneurs, les versions explicitement déclarées dans le dépôt. Les versions non encore mesurées sur les machines sont laissées à vérifier plutôt que présumées.

### 3.1. Ordinateur central — HP EliteBook

- **Système d'exploitation de référence :** Ubuntu **26.04.1 LTS**, x86-64.
- **Git :** récupération du dépôt, suivi des changements et collaboration.
- **Docker Engine :** exécution isolée des services.
- **Docker Compose (plugin v2) :** déploiement défini dans [`compose.yaml`](compose.yaml).
- **OpenSSH Server :** export des autorisations vers le Raspberry Pi au moyen d'un compte et d'une clé dédiés.
- **OpenSSL :** génération locale des secrets utilisés par les services.
- **curl :** essais de l'API et vérification des réponses HTTP.
- **`ss` (paquet `iproute2`) :** contrôle des ports d'écoute.

**Services lancés dans les conteneurs (sans installation PostgreSQL hôte requise) :**

- **PostgreSQL 18.1** : image `postgres:18.1`, base de données centrale.
- **PostgREST v16.3** : image `postgrest/postgrest:v16.3`, interface REST vers les fonctions SQL prévues.

Le port de PostgREST reste lié à `127.0.0.1:3000` sur l'ordinateur central; il n'est pas publié sur le réseau local.

### 3.2. Serveur local — Raspberry Pi 4

- **Système d'exploitation de référence :** Debian **13 (trixie)**, architecture ARM64.
- **Git :** synchronisation du code du dépôt.
- **OpenSSH Client :** récupération des autorisations par une connexion SSH authentifiée.
- **Python 3 :** importation et surveillance des instantanés d'autorisations.
- **Docker Engine et plugin Docker Compose :** construction et exécution des services de [`compose.local.yaml`](compose.local.yaml).
- **systemd :** déclenchement périodique de la synchronisation et de la surveillance.
- **sudo :** installation initiale des services et opérations nécessitant les droits d'administration.

**Dépendances intégrées aux images Docker locales :**

- **Debian trixie-slim** : environnement d'exécution et de compilation.
- **SQLite 3** (bibliothèque `libsqlite3`) : stockage des autorisations sur le serveur local.
- **Compilateur C++ compatible C++20, CMake et make** : compilation des programmes du serveur local.
- **Python 3** : traitements d'importation et de surveillance à l'intérieur des conteneurs.

Les outils de compilation et les bibliothèques sont installés **dans les images Docker** par [`docker/Dockerfile.local`](docker/Dockerfile.local) : il n'est pas nécessaire de les installer séparément sur l'hôte pour suivre la procédure normale.

### 3.3. Développement ESP32 — configuration validée

Le programme de test LCD est situé dans `controleur-esp32/`. Il se compile indépendamment des programmes serveur à la racine.

- **Hôte de compilation :** Ubuntu 26.04.1 LTS, x86-64, sur HP EliteBook 840 G6.
- **Visual Studio Code 1.142.0**, avec Remote – SSH pour le développement distant.
- **Extension officielle Espressif IDF 2.3.0**, installée sur l’hôte de compilation.
- **ESP-IDF v5.3.6**, installé avec Espressif Installation Manager.
- **LVGL 8.3.11**, conservé dans les composants du contrôleur.
- **Pilote ST7789 et adaptation LVGL issus de l’exemple Waveshare**, avec initialisation SPI autonome et rétroéclairage limité à 50 %.
- **Interface USB Serial/JTAG** pour le téléversement et le diagnostic.

La compilation, le téléversement et l’affichage après coupure d’alimentation ont été validés. Les communications réseau restent à implémenter.

Voir le [guide d’installation et du premier test LCD](documentation/installation-esp32.md).

### 3.4. Logiciels utiles, mais facultatifs

- **VS Code avec Git** : édition, révision du code et développement à distance.
- **Client SSH** : administration distante du serveur central et du Raspberry Pi.
- **Client SQL ou outils PostgreSQL** : inspection ponctuelle des données fictives.
- **Outils de mesure et de diagnostic réseau** : vérification des échanges pendant les essais.

## 4. Installation et vérification

Le guide [**INSTALLATION.md**](INSTALLATION.md) décrit les prérequis, la mise en place des clés SSH, les commandes d'installation, l'activation des services et les diagnostics.

**Sur l'ordinateur central :**

```bash
git clone https://github.com/shocktubeM81/simulation-controle-acces-physique.git
cd simulation-controle-acces-physique
bash scripts/installer-central.sh
bash scripts/verifier.sh central
```

**Sur le Raspberry Pi :**

```bash
git clone https://github.com/shocktubeM81/simulation-controle-acces-physique.git
cd simulation-controle-acces-physique
bash scripts/installer-pi.sh
```

L'installation initiale du Raspberry Pi demande ensuite l'autorisation de sa clé publique sur le serveur central et l'activation des unités systemd selon [INSTALLATION.md](INSTALLATION.md). Le script `scripts/verifier.sh pi` permet de contrôler le fonctionnement local.

**Attention aux branches :** les commandes ci-dessus récupèrent `main` par défaut. Pour tester des fonctions encore en développement, sélectionner explicitement la branche voulue et vérifier sa documentation.

## 5. Reproductibilité et traçabilité

Pour chaque essai significatif, consigner au minimum :

- **Matériel :** fabricant, modèle exact, variante, révision PCB (si disponible) et périphériques raccordés.
- **Systèmes d'exploitation :** distribution, version, architecture et version du noyau.
- **Logiciels :** versions de Docker/Compose, images utilisées, outils de compilation, SDK ESP32 et bibliothèques.
- **Code :** branche, identifiant de commit Git et fichiers de configuration pertinents, **sans publier de secrets**.
- **Essai :** câblage, alimentation, réseau utilisé, procédure, résultat et anomalies.

Les matériels équivalents restent admissibles, à condition de **documenter les substitutions** et de refaire les essais concernés. La configuration décrite ici est un **point de référence reproductible**, pas une exigence de marque ou de modèle.

## 6. Principes et limites de sécurité

Le fonctionnement et les choix techniques peuvent être examinés publiquement. La sécurité ne repose pas sur l'obscurité du code, mais sur l'authentification, le moindre privilège, le cloisonnement et les protocoles éprouvés.

- N'utiliser que des **identifiants fictifs et des données fictives** dans le laboratoire.
- Conserver les **clés privées, mots de passe et fichiers de secrets hors de Git**.
- Ne pas exposer l'API expérimentale non authentifiée sur le réseau ou sur Internet.
- Ne pas confondre une décision logicielle avec la conception de la sûreté des personnes (évacuation, panne d'alimentation, incendie).
- Ne pas utiliser ce prototype pour commander une porte ou une serrure en service.

Pour approfondir : [principes de sécurité](documentation/securite.md), [conception initiale de l'ESP32](documentation/controleur-esp32.md) et [conventions de code C++](documentation/conventions-code.md).

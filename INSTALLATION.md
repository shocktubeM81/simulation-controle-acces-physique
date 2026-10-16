# Installation reproductible

Cette procédure déploie **une simulation pédagogique** sur deux machines Linux. Toutes les données d'identifiants et de portes sont fictives. Aucun contrôleur de porte réel n'est requis à cette étape.

## 1. Matériel et logiciels

| Équipement | Minimum pour suivre la procédure validée | Logiciels |
|---|---|---|
| Ordinateur (serveur central) | Ordinateur Linux, accès réseau, espace disque disponible pour Docker | Ubuntu ou Debian, Docker Engine et Compose, Git, OpenSSL, curl, OpenSSH Server |
| Raspberry Pi (serveur local) | Raspberry Pi 4 testé, alimentation stable, stockage compatible, réseau joignant l'ordinateur | Debian 13 **ARM64** (trixie), Git, OpenSSH Client; Docker et Compose installés par le script |
| Contrôleur de porte | **Non nécessaire actuellement** | ESP32 prévu dans une phase ultérieure |

**Recommandé pour les essais :** liaison Ethernet et au moins 16 Go de stockage libre sur le Raspberry Pi. Ces valeurs sont des recommandations pratiques, **pas des exigences minimales mesurées**. Les deux machines doivent avoir une heure synchronisée; l'import refuse les instantanés décalés de plus de 60 s.

Prérequis réseau : le Raspberry Pi doit pouvoir joindre le **port SSH** de l'ordinateur central. PostgreSQL n'est pas exposé au réseau et PostgREST reste accessible uniquement par `127.0.0.1:3000` sur l'ordinateur. Aucune redirection Internet de ports n'est requise.

Les exemples utilisent `IP_ORDINATEUR` et `UTILISATEUR_ORDINATEUR` comme paramètres **à remplacer**, et non comme noms à saisir littéralement.

## 2. Ordinateur — initialiser le serveur central

Avec Docker Engine et Docker Compose déjà installés :

```bash
git clone https://github.com/shocktubeM81/simulation-controle-acces-physique.git
cd simulation-controle-acces-physique
bash scripts/installer-serveur-central.sh
bash scripts/verifier-installation.sh
```

Le script crée les secrets localement (exclus de Git), initialise PostgreSQL et les données fictives, puis démarre PostgREST. Il est relançable sans effacer volontairement les volumes.

Le service SSH de l'ordinateur central doit être opérationnel avant l'étape 4. Ne pas ouvrir le port 3000 au réseau.

## 3. Raspberry Pi — préparer et construire

```bash
git clone https://github.com/shocktubeM81/simulation-controle-acces-physique.git
cd simulation-controle-acces-physique
bash scripts/preparer-raspberry-pi.sh
bash scripts/installer-serveur-local.sh
bash scripts/preparer-cle-synchronisation.sh
```

Le premier script prépare Docker Engine et Compose sur Debian 13 ARM64; le deuxième compile le C++ et les outils Python dans Docker. À la première installation, les minuteurs ne sont pas activés tant que l'identité SSH n'est pas validée. La clé privée de synchronisation **reste sur le Raspberry Pi**.

## 4. Autoriser une seule commande d'export SSH

**Sur le Raspberry Pi**, copier uniquement la clé **publique**. Remplacer les valeurs en majuscules par celles de l'ordinateur :

```bash
scp ~/.ssh/id_ed25519_controle_sync.pub \
  UTILISATEUR_ORDINATEUR@IP_ORDINATEUR:~/controle-sync.pub
```

**Sur l'ordinateur central**, depuis le dépôt :

```bash
sudo bash scripts/installer-acces-export-central.sh ~/controle-sync.pub
```

Ce script crée ou vérifie `controle-export`, avec la clé SSH restreinte à la commande d'export. Il n'ouvre pas d'accès général au compte personnel.

**Sur le Raspberry Pi**, vérifier la clé de l'hôte SSH lors de la première connexion, puis tester :

```bash
ssh -T -o BatchMode=yes -o IdentitiesOnly=yes \
  -i ~/.ssh/id_ed25519_controle_sync \
  controle-export@IP_ORDINATEUR exporter-autorisations
```

La réponse attendue est un JSON fictif incluant `schema_version`, `captured_at`, `personnes`, `identifiants`, `portes` et `autorisations`.

## 5. Activer la synchronisation et la surveillance

**Sur le Raspberry Pi**, depuis le dépôt :

```bash
sudo bash scripts/installer-timer-raspberry-pi.sh \
  "$(id -un)" controle-export@IP_ORDINATEUR
sudo systemctl start controle-acces-synchronisation.service
sudo systemctl status controle-acces-synchronisation.service --no-pager
```

Si le service a terminé avec succès, activer les deux minuteurs :

```bash
sudo systemctl enable --now controle-acces-synchronisation.timer
sudo bash scripts/installer-surveillance.sh
```

Les durées du laboratoire sont environ **5 minutes entre les synchronisations** et **1 minute entre les vérifications de surveillance**. Un échec SSH ne doit jamais rafraîchir artificiellement l'horodatage SQLite.

## 6. Valider la chaîne

**Sur le Raspberry Pi** :

```bash
bash scripts/tester-surveillance-cache.sh
bash scripts/verifier-serveur-local.sh
```

Le dernier test vérifie le cache synchronisé récent, `FICTIF-0001` autorisé à `Laboratoire`, `FICTIF-0003` refusé et les deux minuteurs actifs. Il est **non destructif**.

Pour voir les journaux :

```bash
sudo journalctl -u controle-acces-synchronisation.service \
  -u controle-acces-surveillance.service -n 30 --no-pager
```

## 7. Mises à jour ultérieures

**Sur chaque machine concernée** : se placer dans son clone du dépôt et lancer :

```bash
git pull --ff-only origin main
```

**Sur l'ordinateur central**, si du code serveur a changé :

```bash
bash scripts/installer-serveur-central.sh
```

**Sur le Raspberry Pi**, la mise à jour habituelle est :

```bash
bash scripts/installer-serveur-local.sh
bash scripts/verifier-serveur-local.sh
```

Si l'identité SSH et la configuration systemd existent déjà, l'installateur local reconstruit l'image, vérifie la liaison SSH et réinstalle les deux unités de service. Il ne supprime pas les volumes.

**Ne pas utiliser `docker compose down --volumes` dans une mise à jour :** cette commande efface les données persistantes du projet.

## 8. Diagnostics et limites

- `bash scripts/tester-sqlite-local.sh` : test autonome du **cache statique**, distinct du cache synchronisé.
- `bash scripts/tester-reseau.sh IP_ORDINATEUR` : essai TCP C++ **non chiffré et non authentifié**, pour le laboratoire uniquement (serveur TCP de diagnostic à lancer préalablement sur l'ordinateur).
- `bash scripts/synchroniser-serveur-local.sh controle-export@IP_ORDINATEUR ~/.ssh/id_ed25519_controle_sync` : synchronisation manuelle de dépannage.

Ce prototype n'est **pas adapté à une installation de sûreté réelle**. Les services `systemd` lancent Docker avec les droits root depuis un dépôt modifiable par l'utilisateur; la politique des portes sensibles, les alertes externes et l'intégration du futur ESP32 restent à développer.

Pour comprendre le code, consulter [les conventions C++](documentation/conventions-code.md), [la sécurité](documentation/securite.md) et [la politique de synchronisation](documentation/politique-synchronisation.md).

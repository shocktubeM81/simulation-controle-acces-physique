# Installation du laboratoire

Ce guide permet de préparer le serveur central sous Ubuntu, de compiler les premiers programmes C++ et de créer la base de données PostgreSQL **entièrement fictive**.

Les commandes sont exécutées depuis la racine du dépôt, sauf indication contraire.

## Installation automatisée sur Ubuntu

Pour un serveur Ubuntu sur lequel PostgreSQL et Docker sont déjà installés, une seule commande prépare la base fictive, les rôles techniques, l'API PostgREST et effectue un test HTTP :

```bash
bash scripts/installer-serveur-central.sh
```

Pour vérifier à tout moment les deux décisions attendues et la restriction d'écoute locale :

```bash
bash scripts/verifier-installation.sh
```

Le script peut être relancé : il conserve la base et les données existantes, évite de réimporter les jeux fictifs et ne remplace pas un fichier `.env.api` déjà présent. Il crée un mot de passe technique aléatoire seulement lors de la première configuration. **Il n'efface aucune donnée.** Lors d'une réinstallation sur une autre machine, le rôle PostgreSQL correspondant au compte Ubuntu doit préalablement exister et être utilisable en connexion locale avec `psql` (voir les étapes manuelles ci-dessous). Le script demande les privilèges `sudo`, et éventuellement le mot de passe de connexion PostgreSQL du propriétaire.

**Sur l'EliteBook déjà configuré :** exécuter le script permet de vérifier et de remettre en place les composants sans repartir de zéro. Il ne remplace pas le mot de passe technique ni la configuration déjà opérationnelle.

Les fichiers de configuration locaux contenant des secrets sont exclus par `.gitignore`.

Si une étape échoue, consulter [la configuration détaillée de l'API](documentation/interface-api.md), puis relancer le script une fois le problème corrigé.

---

## 1. Récupérer le dépôt

Sur une nouvelle machine :

```bash
git clone git@github.com:shocktubeM81/simulation-controle-acces-physique.git
cd simulation-controle-acces-physique
```

Si le dépôt est déjà cloné :

```bash
cd ~/UQAT/GEN0002/simulation-controle-acces-physique
git pull --ff-only origin main
```

Le chemin `~/UQAT/GEN0002/...` correspond au poste de développement initial; il n'est pas requis sur les autres ordinateurs.

## 2. Vérifier les logiciels nécessaires

```bash
g++ --version
cmake --version
psql --version
```

Si des logiciels manquent sur Ubuntu :

```bash
sudo apt update
sudo apt install -y build-essential cmake postgresql postgresql-client
```

Docker est facultatif pour cette première étape.

## 3. Préparer PostgreSQL

Vérifier que PostgreSQL fonctionne :

```bash
sudo systemctl status postgresql
```

Au besoin :

```bash
sudo systemctl start postgresql
```

### Compte PostgreSQL

Sur l'EliteBook de développement, le rôle PostgreSQL `david` est **déjà configuré**. Il n'est pas nécessaire de le recréer.

Sur une autre machine, créer un rôle réservé à l'expérience si aucun rôle adéquat n'existe :

```bash
sudo -u postgres createuser --pwprompt controle_acces
```

Dans ce cas, remplacer `david` par `controle_acces` dans les commandes de création et de connexion ci-dessous. Conserver le mot de passe hors du dépôt Git.

## 4. Créer la base fictive

Sur l'EliteBook :

```bash
sudo -u postgres createdb --owner=david controle_acces_simulation
```

Sur une autre machine utilisant le rôle `controle_acces` :

```bash
sudo -u postgres createdb --owner=controle_acces controle_acces_simulation
```

Créer la base une seule fois. Si elle existe déjà, ne pas répéter cette étape.

## 5. Créer les tables

Sur l'EliteBook :

```bash
psql -h 127.0.0.1 -U david -d controle_acces_simulation \
  -v ON_ERROR_STOP=1 -f base-de-donnees/structure.sql
```

Sur une autre machine, remplacer `david` par le nom du rôle PostgreSQL créé à l'étape 3.

Les tables initiales sont `personnes`, `identifiants`, `portes` et `autorisations`.

## 6. Insérer les données fictives

```bash
psql -h 127.0.0.1 -U david -d controle_acces_simulation \
  -v ON_ERROR_STOP=1 -f base-de-donnees/donnees-fictives.sql
```

**Important :** exécuter le fichier de données fictives **une seule fois** sur une base vide. Il n'est pas conçu pour être réexécuté sans réinitialisation.

## 7. Vérifier une autorisation

```bash
psql -h 127.0.0.1 -U david -d controle_acces_simulation \
  -v ON_ERROR_STOP=1 -f base-de-donnees/verifier-acces.sql
```

Résultat attendu pour l'identifiant `FICTIF-0001` à la porte `Laboratoire` :

```text
     code    |    porte    | decision
-------------+-------------+----------
 FICTIF-0001 | Laboratoire | AUTORISE
```

Pour tester un refus, modifier la valeur `FICTIF-0001` en `FICTIF-0003` dans `base-de-donnees/verifier-acces.sql`, puis relancer la commande.

Pour consulter les tables :

```bash
psql -h 127.0.0.1 -U david -d controle_acces_simulation -c '\dt'
```

## 8. Compiler les premiers programmes C++

```bash
cmake -S . -B build
cmake --build build
```

Pour un premier essai TCP sur l'ordinateur central :

Terminal 1 :

```bash
./build/serveur-central 127.0.0.1 5050
```

Terminal 2 :

```bash
./build/serveur-local 127.0.0.1 5050
```

L'expérience TCP est indépendante de PostgreSQL à ce stade.

## 9. Installer l'interface API locale

Après les étapes PostgreSQL, suivre le [guide PostgREST](documentation/interface-api.md) pour créer les rôles API, configurer Docker et tester les décisions par HTTP sur `127.0.0.1:3000`.

## Serveur local — Raspberry Pi 4

La préparation de Raspberry Pi OS, de SSH, du réseau Ethernet et du premier essai TCP entre les deux ordinateurs est décrite dans le [guide Raspberry Pi](documentation/raspberry-pi.md).


## Installation automatisée du Raspberry Pi

Sur le Raspberry Pi 4 (Debian 13 ARM64), exécuter `bash scripts/installer-serveur-local.sh` depuis le dépôt après son clonage. Voir le [guide du Raspberry Pi](documentation/raspberry-pi.md) pour la procédure complète.

## Précautions

- N'utiliser que des données fictives.
- Ne pas ajouter de mots de passe ou de fichiers de configuration secrets à Git.
- Les services de démonstration ne sont pas conçus pour être exposés à Internet.
- Ne pas ouvrir PostgreSQL aux autres machines : un service réseau intermédiaire sera choisi et configuré lors d'une étape ultérieure.

Pour les détails du schéma SQL, voir [la documentation de la base de données](documentation/base-de-donnees.md). Pour les essais TCP, voir [la documentation réseau](documentation/reseau.md).

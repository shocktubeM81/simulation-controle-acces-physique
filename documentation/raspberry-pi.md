# Raspberry Pi — serveur local

Le Raspberry Pi 4 exécute le cache SQLite, un moteur C++ de décision et les services de synchronisation et de surveillance. Les conteneurs sont **éphémères** : les données persistent dans un volume Docker.

## Prérequis

- Raspberry Pi 4 avec alimentation et carte de stockage, Debian 13 ARM64 (`trixie`).
- Accès réseau au serveur central, Git, Python 3, OpenSSH Client et sudo.
- Docker et Compose sont préparés par l'installateur si absents.

Les commandes complètes de déploiement initial, y compris l'échange de clés SSH, sont regroupées dans [INSTALLATION.md](../INSTALLATION.md).

## Installation et mise à jour

```bash
bash scripts/installer-pi.sh
bash scripts/verifier.sh pi
```

Sur une machine neuve, les minuteurs doivent être configurés et activés **après** une synchronisation SSH manuelle validée, conformément au guide principal.

## Modes de décision

- `cache-sqlite verifier CODE PORTE` : données fictives **statiques** (`autorisations.sqlite3`), réservées aux diagnostics.
- `cache-sqlite verifier-sync CODE PORTE` : données du serveur central (`autorisations-synchronisees.sqlite3`), avec vérification de leur fraîcheur et des dates d'autorisation.

L'accès au cache synchronisé est limité à l'exécution locale : le conteneur ne possède pas d'interface réseau. La récupération des instantanés se fait depuis l'hôte par une clé SSH dédiée et un compte à commande forcée.

## Diagnostics facultatifs

```bash
bash scripts/verifier.sh seuils
bash scripts/verifier.sh cache-statique
bash scripts/verifier.sh reseau IP_CENTRAL 5050
```

Le test du cache statique n'efface ni ne remplace le cache synchronisé. Le diagnostic TCP est non authentifié : il ne doit pas servir à actionner une porte.

## Limites

Le prototype utilise Docker avec des permissions d'administration via systemd; les unités et fichiers de déploiement doivent être durcis pour une véritable installation. La gestion de portes sensibles, l'ESP32, l'audit avancé et les alertes externes restent à développer.

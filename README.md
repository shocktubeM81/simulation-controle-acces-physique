# Simulation d'une architecture de contrôle d'accès physique

Projet étudiant de simulation d'un contrôle d'accès distribué, avec données fictives et technologies libres.

## Architecture

- **Ordinateur (serveur central)** : PostgreSQL et PostgREST, déployés avec Docker Compose.
- **Raspberry Pi (serveur local)** : cache SQLite synchronisé par SSH restreint, minuterie systemd et surveillance périodique du cache.
- **Contrôleur de porte** : microcontrôleur ESP32 et entrées/sorties physiques (étape ultérieure).

Les scripts TCP et le cache SQLite statique servent encore aux diagnostics pédagogiques; les décisions synchronisées utilisent le cache distinct `autorisations-synchronisees.sqlite3`.

## Installation

Suivre les quelques commandes dans [INSTALLATION.md](INSTALLATION.md). Pour les prérequis matériels et logiciels ainsi que les commandes exactes, consulter ce guide. La [structure C++ et les conventions de commentaires](documentation/conventions-code.md) sont documentées séparément.

## Principes

Le fonctionnement et les choix techniques sont documentés publiquement. La sécurité ne repose pas sur l'obscurité du code, mais sur l'authentification, le moindre privilège, le cloisonnement et les protocoles éprouvés. Consulter [les principes de sécurité](documentation/securite.md).

Cette simulation ne constitue pas un système de sécurité prêt à être déployé.

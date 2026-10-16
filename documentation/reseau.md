# Premier essai de communication réseau

## Objectif

Vérifier une connexion TCP/IP réelle entre deux processus C++.

- **Serveur central :** écoute sur une adresse IPv4 et un port configurables.
- **Serveur local :** établit une connexion, envoie un message et reçoit un accusé de réception.

Les messages sont fictifs. Cette version ne comprend ni authentification, ni chiffrement, ni protocole applicatif robuste. Elle ne doit pas être exposée directement à Internet.

## Compiler

Depuis la racine du dépôt :

```bash
cmake -S . -B build
cmake --build build
```

## Essai sur un même ordinateur

Dans un premier terminal :

```bash
./build/serveur-central 127.0.0.1 5050
```

Dans un second terminal :

```bash
./build/serveur-local 127.0.0.1 5050
```

Le serveur central affiche le message reçu. Le serveur local affiche l'accusé de réception. Arrêter le serveur central avec `Ctrl+C`.

## Essai avec deux ordinateurs sur un réseau de laboratoire

Sur l'ordinateur central, utiliser son adresse IPv4 Ethernet ou `0.0.0.0` pour écouter sur les interfaces IPv4 :

```bash
./build/serveur-central 0.0.0.0 5050
```

Sur le Raspberry Pi, compiler le même projet et remplacer `ADRESSE_ELITEBOOK` par l'adresse IPv4 Ethernet de l'EliteBook :

```bash
./build/serveur-local ADRESSE_ELITEBOOK 5050
```

Le pare-feu doit autoriser uniquement les connexions nécessaires en provenance du réseau de laboratoire. Ne pas effectuer de redirection de port vers Internet.

## Limites de cette étape

Cet exemple sert uniquement à valider le transport TCP. TCP est un flux d'octets : les limites des messages ne sont pas garanties par `recv`. Le protocole applicatif, la gestion des erreurs et la sécurisation des échanges seront conçus dans les prochaines étapes.

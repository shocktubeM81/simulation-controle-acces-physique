# Organisation et conventions du code

## Objectif

Le dépôt doit permettre à une autre équipe de **comprendre, compiler, tester et reproduire** la simulation. Les commentaires expliquent les choix, les hypothèses et les cas limites; ils ne paraphrasent pas les instructions.

## Répartition des responsabilités

| Dossier ou fichier | Responsabilité |
|---|---|
| `serveur-central/principal.cpp` | Serveur TCP **de diagnostic seulement**, distinct de PostgreSQL/PostgREST |
| `serveur-local/principal.cpp` | Client TCP de diagnostic |
| `serveur-local/controle-local.cpp` | Interface CLI : paramètres, commande choisie, codes de retour |
| `serveur-local/cache-sqlite.hpp` | Interface du moteur de décision local |
| `serveur-local/cache-sqlite.cpp` | SQLite, données d'essai, fraîcheur et requêtes de décision |
| `serveur-local/importer-snapshot.py` | Validation et import atomique d'un instantané reçu par SSH |
| `serveur-local/surveiller-cache.py` | Évaluation indépendante de l'âge du cache |
| `configuration/` | Paramètres et hypothèses de simulation |
| `scripts/` | Installation, exploitation et vérifications reproductibles |
| `systemd/` | Synchronisation et surveillance périodiques |

`controle-local` utilise deux bases distinctes : `autorisations.sqlite3` (jeu d'essai statique) et `autorisations-synchronisees.sqlite3` (cache central validé). **Ne pas fusionner les modes de diagnostic et d'exploitation.**

## Conventions C++

- **C++20**; compilation via **CMake**, y compris dans l'image Docker. Pas de seconde commande de compilation manuelle en parallèle.
- Noms de fonctions et variables en français, cohérents et explicites; classes en PascalCase.
- Garder `main()` court : lecture des arguments, appels aux composants, retour d'erreur.
- Chaque module doit avoir une responsabilité claire. Extraire des fichiers supplémentaires lorsqu'une interface ou un domaine autonome apparaît, pas uniquement pour réduire le nombre de lignes.
- Utiliser `const`, la gestion automatique des ressources (RAII) et les requêtes SQL préparées dès qu'ils apportent une garantie concrète.
- Préférer un test automatique à un commentaire qui promet un comportement non vérifié.

## Politique de commentaires

Commentaires **pertinents** :

```cpp
// Un cache non synchronisé ne peut jamais autoriser une entrée.
if (dernier < 0) {
    // ...
}
```

Commentaires **inutiles** :

```cpp
// Incrémente le compteur.
++compteur;
```

Commenter en priorité : les invariants de sécurité (refus par défaut, validité des données), le choix des chemins SQLite, les hypothèses de temps, l'ordre des transactions et les compromis propres au laboratoire. Pour une interface publique non triviale, documenter le contrat (entrées, comportement, erreur) une fois dans le fichier d'en-tête.

Un `TODO` doit décrire un manque réel : par exemple, le moteur C++ utilise encore une limite de fraîcheur codée en dur de 3 600 secondes, alors que le moniteur lit `configuration/politique-synchronisation.json`. Cette divergence devra être corrigée avant d'utiliser plusieurs profils de portes.

## Vérifications

**Sur le Raspberry Pi**, après avoir suivi `INSTALLATION.md` :

```bash
bash scripts/installer-serveur-local.sh
bash scripts/tester-surveillance-cache.sh
bash scripts/verifier-serveur-local.sh
```

La dernière commande exige une synchronisation récente et des minuteurs actifs. Elle ne modifie pas les données. Les programmes TCP de diagnostic ne sont pas une preuve de sécurité réseau.

Pour compiler les programmes C++ **hors Docker** sur Linux, installer `cmake`, `g++` et `libsqlite3-dev` :

```bash
cmake -S . -B build
cmake --build build
```

La construction produit `serveur-central`, `serveur-local` (TCP de diagnostic) et `controle-local` (SQLite). Ce dernier s'attend au chemin `/donnees` prévu dans le conteneur; pour les essais fonctionnels, privilégier Docker Compose.

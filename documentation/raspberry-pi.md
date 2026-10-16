# Raspberry Pi — serveur local

Le Raspberry Pi doit disposer de Debian 13 ARM64 et d'une connexion réseau vers l'ordinateur. Le script de préparation installe Docker Engine et Compose depuis le dépôt officiel (avec `sudo`) si nécessaire. Pour un autre système, suivre la documentation Docker applicable.

Le dépôt ne dépend pas du nom de machine ni de l'utilisateur Linux.

```bash
git clone https://github.com/shocktubeM81/simulation-controle-acces-physique.git
cd simulation-controle-acces-physique
bash scripts/preparer-raspberry-pi.sh
bash scripts/installer-serveur-local.sh
```

Le fichier `compose.local.yaml` construit les exécutables C++ de diagnostic et SQLite dans des conteneurs Debian ARM64. Les outils s'exécutent dans des conteneurs éphémères. Après configuration SSH, deux minuteurs systemd lancent périodiquement la synchronisation et la surveillance.

Pour tester le réseau Ethernet, lancer d'abord le serveur TCP de diagnostic sur l'ordinateur, puis :

```bash
sudo docker compose -f compose.local.yaml run --rm diagnostic-reseau ADRESSE_IPV4_ORDINATEUR 5050
```

Les deux appareils doivent appartenir à un réseau autorisé à échanger des connexions TCP. Les adresses sont choisies au moment de l'essai, sans les fixer dans les fichiers source.

## Cache SQLite local (prototype)

Après mise à jour du dépôt :

```bash
bash scripts/installer-serveur-local.sh
bash scripts/tester-sqlite-local.sh
```

Le test initialise un volume Docker nommé `controle-acces-local_donnees_locales`, puis lance **de nouveaux conteneurs éphémères** pour vérifier les décisions `FICTIF-0001` et `FICTIF-0003` à la porte `Laboratoire`. Il vérifie ainsi la persistance entre les conteneurs, mais **pas encore** après un redémarrage matériel.

Pour vérifier manuellement :

```bash
sudo docker compose -f compose.local.yaml run --rm cache-sqlite initialiser
sudo docker compose -f compose.local.yaml run --rm cache-sqlite verifier FICTIF-0001 Laboratoire
sudo docker compose -f compose.local.yaml run --rm cache-sqlite verifier FICTIF-0003 Laboratoire
```

Le conteneur SQLite fonctionne **sans réseau** (`network_mode: none`), sans privilèges élevés et avec un système de fichiers en lecture seule, à l'exception du volume des données. Il ne contient que des autorisations **fictives et statiques**, dont les identifiants sont volontairement publiés dans le dépôt. Cette **base statique de diagnostic** ne se synchronise pas. La base `autorisations-synchronisees.sqlite3`, séparée, est alimentée par SSH restreint, avec vérification de fraîcheur et des dates d'autorisation.

**Attention :** ne pas utiliser ce prototype pour protéger une porte réelle : une autorisation révoquée au central resterait valide dans ce cache statique **de diagnostic**. Les décisions du cache synchronisé sont évaluées séparément avec `verifier-sync`. Une stratégie explicite de validité et de révocation, ainsi que l'authentification et le chiffrement des communications, seront nécessaires avant une mise en service.

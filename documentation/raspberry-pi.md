# Raspberry Pi — serveur local

Le Raspberry Pi doit disposer de Debian 13 ARM64 et d'une connexion réseau vers l'ordinateur. Le script de préparation installe Docker Engine et Compose depuis le dépôt officiel (avec `sudo`) si nécessaire. Pour un autre système, suivre la documentation Docker applicable.

Le dépôt ne dépend pas du nom de machine ni de l'utilisateur Linux.

```bash
git clone https://github.com/shocktubeM81/simulation-controle-acces-physique.git
cd simulation-controle-acces-physique
bash scripts/preparer-raspberry-pi.sh
bash scripts/installer-serveur-local.sh
```

Le fichier `compose.local.yaml` construit une image Debian avec le programme C++ de diagnostic. Il ne lance pas de service permanent.

Pour tester le réseau Ethernet, lancer d'abord le serveur TCP de diagnostic sur l'ordinateur, puis :

```bash
sudo docker compose -f compose.local.yaml run --rm diagnostic-reseau ADRESSE_IPV4_ORDINATEUR 5050
```

Les deux appareils doivent appartenir à un réseau autorisé à échanger des connexions TCP. Les adresses sont choisies au moment de l'essai, sans les fixer dans les fichiers source.

**Étapes non encore implémentées :** cache SQLite persistant, synchronisation, contrôle d'accès du Raspberry Pi à l'API centrale et liaison avec le microcontrôleur. Aucune API non authentifiée ne doit être exposée pour accélérer ces étapes.

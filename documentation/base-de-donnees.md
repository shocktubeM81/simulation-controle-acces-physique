# Base de données fictive

PostgreSQL est maintenant installé **dans Docker**, indépendamment des bases présentes sur l'ordinateur. Le fichier [INSTALLATION.md](../INSTALLATION.md) contient les commandes courtes.

La première initialisation du volume crée les tables `personnes`, `identifiants`, `portes` et `autorisations`, insère six personnes fictives et installe une fonction de décision accessible par PostgREST.

Pour consulter les tables :

```bash
docker compose exec base-de-donnees psql -U postgres -d controle_acces_simulation -c '\dt'
```

Pour vérifier les décisions :

```bash
bash scripts/verifier-installation.sh
```

Les scripts SQL sont appliqués **uniquement à la création initiale du volume**. Une modification du schéma nécessitera des migrations explicites; ne pas supprimer le volume pour effectuer une mise à jour normale.

La commande `docker compose down` conserve les données. La commande `docker compose down --volumes` efface celles du laboratoire de façon permanente.

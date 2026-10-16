# Base de données fictive (PostgreSQL)

Cette étape utilise PostgreSQL déjà installé sur l'ordinateur central. Aucune application C++ personnalisée n'est nécessaire pour exécuter les requêtes SQL.

## 1. Créer une base distincte

Sur l'EliteBook, la base est créée avec le rôle PostgreSQL `david` déjà configuré :

```bash
sudo -u postgres createdb --owner=david controle_acces_simulation
```

Si la base existe déjà, ne pas répéter cette commande.

## 2. Créer les tables et insérer les données fictives

Depuis la racine du dépôt :

```bash
psql -h 127.0.0.1 -U david -d controle_acces_simulation -v ON_ERROR_STOP=1 -f base-de-donnees/structure.sql
psql -h 127.0.0.1 -U david -d controle_acces_simulation -v ON_ERROR_STOP=1 -f base-de-donnees/donnees-fictives.sql
```

**Attention :** le fichier de données fictives est destiné à une base vide. Son exécution répétée créera des doublons de personnes et entraînera une erreur d'unicité sur les codes d'identifiants. Cette erreur déclenchera une annulation de la transaction.

## 3. Vérifier une décision d'accès

```bash
psql -h 127.0.0.1 -U david -d controle_acces_simulation -v ON_ERROR_STOP=1 -f base-de-donnees/verifier-acces.sql
```

L'exemple évalue `FICTIF-0001` sur `Laboratoire` et doit retourner `AUTORISE`. Dans `base-de-donnees/verifier-acces.sql`, modifier `FICTIF-0001` pour `FICTIF-0003` : le résultat doit être `REFUSE`.

## Modèle initial

- `personnes` : individus fictifs et état du compte;
- `identifiants` : codes de simulation liés à une personne;
- `portes` : portes fictives actives ou inactives;
- `autorisations` : permission d'une personne sur une porte, avec dates optionnelles.

**Limites :** les codes `FICTIF-...` ne sont pas des identifiants sécurisés et ne doivent pas servir à authentifier une personne dans un déploiement réel. La gestion des événements, le contrôle des horaires, l'API réseau et la synchronisation locale seront ajoutés après validation du modèle.

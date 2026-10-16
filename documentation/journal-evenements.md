# Journal local des événements

## Portée et état

Cette première étape fournit un journal SQLite local et des tests reproductibles. Les 14 tests du module passent avec Python 3.12.14 et SQLite 3.53.1 sur le poste de préparation; la construction Docker ARM64 et l'exécution sur le Raspberry Pi restent à valider.

Le bouton BOOT n'envoie pas encore d'événement. Aucun serveur HTTP, port d'écoute ou accès direct ESP32 vers SQLite n'est ajouté. Le conteneur de journal s'exécute avec `network_mode: none`.

Les enregistrements de cette étape portent toujours `origine = TEST_LOCAL`. Ils ne prouvent pas qu'un contrôleur a effectivement produit l'événement.

## Ce qui est enregistré

Le seul type accepté est `SORTIE_MANUELLE_SIMULEE`. Une demande de sortie, un déverrouillage simulé et un passage physique sont des faits différents. Le journal ne prétend identifier ni une personne ni un franchissement de porte.

Le message contient exactement :

```json
{
  "version": 1,
  "id_evenement": "a4c71422-e011-4ca7-b140-14310bec83f5",
  "porte": "PORTE-01",
  "type": "SORTIE_MANUELLE_SIMULEE"
}
```

- `id_evenement` : UUID v4 canonique, conservé lors d'un renvoi.
- `porte` : identifiant technique de 1 à 32 caractères, lettres majuscules, chiffres, tirets et caractères de soulignement.
- `controleur` : contexte fourni par l'opérateur local, hors du JSON. Dans le futur transport, il devra provenir de l'authentification de l'équipement et de ses droits, jamais d'une déclaration libre du message.
- `recu_a_utc` : date de réception attribuée par le Pi lors de l'insertion; ce n'est pas l'heure garantie de l'appui.
- `origine` : `TEST_LOCAL`, fixé par le programme.
- `numero` : ordre local d'insertion.

Tout champ supplémentaire, notamment un nom, un mot de passe, un contrôleur ou une date déclarés dans le JSON, est refusé. Le message est limité à 1 024 octets. Les clés JSON répétées et les versions non prises en charge sont refusées.

## Stockage et limites

- Base `/donnees/journal-evenements.sqlite3`, dans le volume Docker dédié `journal_evenements`.
- Aucun montage du volume des caches d'autorisations dans le conteneur de journal.
- Exécution non root, racine du conteneur en lecture seule et capacités retirées.
- Nouveau fichier de base créé avec permissions Unix `0600`; répertoire de données de l'image en `0700`.
- Requêtes SQL paramétrées et transaction d'écriture; accusé de réception produit après validation du commit.
- Même couple contrôleur/UUID et même contenu : une seule ligne, date d'origine conservée, réponse `DEJA_PRESENT`.
- Même couple contrôleur/UUID mais autre contenu : erreur `CONFLIT_EVENEMENT`, sans modification de la ligne.
- Le module ne propose ni modification ni suppression d'événement.

Cette base n'est ni chiffrée au repos ni inviolable. Un administrateur du Pi ou de Docker peut lire, modifier ou supprimer ses fichiers. Aucun mécanisme de rétention, sauvegarde/restauration, limitation de débit ou audit des consultations n'est encore ajouté. Ne pas y introduire de données personnelles réelles à cette étape.

L'accusé de réception SQLite ne garantit pas la conservation après une défaillance du support de stockage. Le stockage et les sauvegardes devront être vérifiés avant tout usage sensible.

## 1. Préparer le Pi

Vérifier l'hôte et son horloge :

```bash
hostname
timedatectl show -p NTPSynchronized -p TimeUSec
openssl version
sudo docker compose version
```

L'hôte doit être le Raspberry Pi et l'horloge synchronisée. Pour le banc, Debian 13 ARM64 et Docker Compose 5.6.0 ont été relevés.

Depuis la copie du dépôt sur le Pi, sélectionner la branche dédiée sans écraser de changements locaux :

```bash
git status --short
git fetch origin
git switch feature/journal-evenements-securise
git pull --ff-only origin feature/journal-evenements-securise
```

Lorsqu'aucune branche locale de ce nom n'existe, Git peut la créer depuis la branche distante correspondante; sinon utiliser explicitement `git switch --track origin/feature/journal-evenements-securise`.

## 2. Construire et tester sans données d'exploitation

```bash
sudo docker compose -f compose.local.yaml build journal-evenements
bash scripts/verifier.sh journal
```

Les tests emploient seulement des bases temporaires sous `/tmp`. Ils vérifient les événements invalides, la minimisation des données, les horodatages, les doublons, les conflits, les écritures concurrentes et le refus d'utiliser une base d'autorisations.

Résultat attendu : 14 tests et `OK`. Le service du journal ne modifie pas les images ni les minuteurs des services existants.

## 3. Initialiser et faire un essai local

```bash
sudo docker compose -f compose.local.yaml run --rm -T journal-evenements initialiser
```

Résultat attendu : `{"statut": "JOURNAL_PRET"}`.

Envoyer le message fictif d'exemple :

```bash
printf '%s\n' '{"version":1,"id_evenement":"a4c71422-e011-4ca7-b140-14310bec83f5","porte":"PORTE-01","type":"SORTIE_MANUELLE_SIMULEE"}' |
  sudo docker compose -f compose.local.yaml run --rm -T journal-evenements enregistrer --controleur SECTEUR-01
```

Résultat attendu au premier envoi : `ENREGISTRE`, avec une date UTC attribuée par le Pi. Rejouer exactement la même commande : attendre `DEJA_PRESENT` et la même date.

Lire les dernières lignes :

```bash
sudo docker compose -f compose.local.yaml run --rm -T journal-evenements lire --limite 20
```

La lecture doit montrer une seule ligne pour le couple contrôleur/UUID d'exemple. Une nouvelle demande distincte devra utiliser un nouvel UUID; une retransmission doit conserver l'UUID initial.

Les fichiers persistent après suppression du conteneur éphémère. Ne pas utiliser `docker compose down -v`, qui supprimerait les volumes du projet.

## 4. Contrôler l'isolation

```bash
sudo docker compose -f compose.local.yaml config
```

Pour `journal-evenements`, vérifier `network_mode: none`, l'absence de ports publiés et le volume dédié. Ne pas publier la configuration complète d'autres services si elle contient des valeurs locales.

## 5. Étape suivante : transport authentifié

Avant tout envoi depuis l'ESP32 :

1. Ajouter un canal TLS avec vérification du serveur et authentification propre à chaque contrôleur.
2. Associer le contrôleur authentifié à ses portes autorisées côté Pi.
3. Générer les secrets localement, prévoir révocation et renouvellement, et les conserver hors de Git et des journaux.
4. Définir les accusés de réception, délais, retransmissions et limites de file; ne jamais affirmer qu'un événement est enregistré avant son accusé.
5. Tester le rejet des clients inconnus, certificats invalides, messages modifiés et doublons.
6. Définir séparément les futurs événements d'identification, de décision et de passage; n'enregistrer que les données nécessaires, avec accès restreint et durée de conservation explicite.

Le Wi-Fi masqué et son mot de passe ne remplacent pas cette authentification applicative. Le TCP de diagnostic historique et l'API expérimentale non authentifiée ne seront pas utilisés comme transport du journal.

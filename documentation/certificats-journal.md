# Préparer l'identité TLS du Pi et du contrôleur

## Portée

Cette étape prépare des certificats pour une future connexion HTTPS avec authentification mutuelle (mTLS). Aucun service réseau n'est ouvert et le programme ESP32 n'est pas modifié.

Les 10 tests cryptographiques ont été exécutés avec OpenSSL 3.3.0 et Python 3.12.14 sur le poste de préparation. Ils ont également été validés sur l'EliteBook avec OpenSSL 3.5.5. OpenSSL 3.x et Python 3 sont nécessaires; aucune dépendance Python externe n'est ajoutée.

## Identités et séparation

- Autorité privée du banc : clé EC P-256 chiffrée par phrase de protection, conservée sur l'EliteBook.
- Pi : certificat de rôle `serverAuth`, avec SAN IPv4 `192.168.81.1`.
- ESP32 : certificat de rôle `clientAuth`, identité technique `SECTEUR-01` et URI `urn:controle-acces:controleur:SECTEUR-01`.
- Droits préparés : seule `PORTE-01` est associée au contrôleur, avec empreinte SHA-256 de son certificat.

Ces identités désignent des équipements, pas des personnes. Le [service HTTPS](journal-https.md) vérifie le certificat client, son empreinte et ses droits sur la porte.

L'autorité est valable 365 jours et les certificats d'équipement 90 jours. Le renouvellement et la révocation devront être intégrés avant expiration; ils ne sont pas automatisés par cet outil de préparation initiale.

## 1. Tester sur l'EliteBook

Utiliser le terminal de l'EliteBook, hors d'une session SSH vers le Pi. Depuis la racine du dépôt :

```bash
hostname
git pull --ff-only origin feature/journal-evenements-securise
bash scripts/verifier.sh certificats-journal
```

Résultat attendu : 10 tests et `OK`. Les clés de ces tests sont éphémères et ne servent jamais au banc réel.

Les tests couvrent la chaîne de confiance, l'adresse IP du serveur, les rôles des certificats, leur correspondance avec les clés, l'empreinte autorisée et le refus d'écraser des clés existantes. Ils vérifient aussi que la phrase de protection n'est pas placée dans les arguments des processus ni affichée.

## 2. Générer localement les certificats du banc

Vérifier l'horloge de l'EliteBook :

```bash
timedatectl show -p NTPSynchronized -p TimeUSec
```

Lancer sans sudo dans un terminal interactif :

```bash
python3 scripts/preparer-certificats-journal.py
```

Choisir et confirmer une phrase de protection longue, au minimum 16 octets UTF-8 exigés; viser au moins 20 caractères. La phrase n'est pas affichée et n'est pas enregistrée par l'outil. Elle est transmise à OpenSSL par son entrée standard, jamais dans la commande ni une variable d'environnement.

Conserver la phrase dans un gestionnaire de mots de passe. Elle protège la clé d'autorité et ne doit être ni le mot de passe Wi-Fi ni un secret partagé avec le contrôleur.

L'outil refuse de démarrer si le dossier de destination existe ou si Git ne l'ignore pas. Si une génération échoue après création du dossier, conserver les fichiers pour inspection; ne pas relancer en écrasant les clés.

Résultat attendu : `CERTIFICATS_VALIDES`, avec adresse du Pi, identifiant technique, porte et empreinte publique. Aucun contenu de clé privée n'est affiché.

## 3. Fichiers produits

Tout reste sous `secrets/journal-pki/`, exclu de Git et du contexte Docker :

| Dossier | Contenu et destination |
| --- | --- |
| `autorite/` | Clé d'autorité chiffrée et certificat public; restent sur l'EliteBook |
| `pi/` | Clé serveur, certificat serveur, certificat public d'autorité et liste des contrôleurs; seuls ces fichiers sont destinés au Pi |
| `esp32/` | Clé client, certificat client et certificat public d'autorité; destinés au micrologiciel du contrôleur |
| `travail/` | Requêtes de certificat et extensions techniques utilisées |

Les dossiers sont créés avec mode Unix `0700` et les fichiers finaux avec mode `0600`. Les clés d'équipement sont non chiffrées pour leur futur usage automatique; elles restent des secrets à protéger. La clé client ne devra pas être copiée sur le Pi, et la clé serveur ne devra pas être embarquée dans l'ESP32.

Ne pas copier le dossier entier sur le Pi. Ne jamais publier les clés, la phrase de protection, les sauvegardes de ce dossier ou les futurs binaires embarquant la clé client.

## 4. Vérifier sans régénérer

```bash
python3 scripts/preparer-certificats-journal.py --verifier
git check-ignore secrets/journal-pki/autorite/ca.cle.pem
```

L'outil vérifie les certificats, leurs usages et leur période de validité, l'adresse serveur, les correspondances clés/certificats d'équipement et l'empreinte du contrôleur. La vérification ne demande pas de déchiffrer la clé d'autorité; elle ne remplace donc pas un test de récupération de cette clé et de sa phrase dans une sauvegarde protégée.

## 5. Avant de connecter l'ESP32

Il reste à mettre en place et tester :

1. Déployer et valider le [service HTTPS du Pi](journal-https.md), qui exige le certificat client et contrôle les empreintes et droits par porte.
2. Le transfert des seuls fichiers serveur au Pi par SSH authentifié, avec permissions adaptées au service.
3. Une horloge correcte sur l'ESP32 pour vérifier les dates des certificats, même après coupure d'alimentation.
4. Le client HTTPS qui vérifie la chaîne et l'adresse du Pi; aucune option de désactivation de ces vérifications ne doit être activée.
5. Les accusés de réception persistants et les retransmissions sans doublons.
6. Les procédures de renouvellement, retrait d'un certificat et restauration des secrets.

Une clé embarquée dans un micrologiciel peut être extraite si l'équipement ou le binaire est compromis. Aucune protection par chiffrement de flash, secure boot ou composant sécurisé n'est revendiquée à cette étape.

Références : [OpenSSL — création des clés](https://docs.openssl.org/3.5/man1/openssl-genpkey/), [certificats X.509](https://docs.openssl.org/3.5/man1/openssl-x509/), [extensions et usages](https://docs.openssl.org/3.5/man5/x509v3_config/).


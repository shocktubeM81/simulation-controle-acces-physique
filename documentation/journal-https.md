# Installer la réception HTTPS du journal

## Portée et prérequis

Le service accepte uniquement des événements fictifs de sortie manuelle sur
`POST /v1/evenements`. Il ne commande aucune serrure et ne fournit aucune route
de consultation. Le bouton BOOT de l'ESP32 n'est pas encore raccordé à ce service.

Configuration de référence :

- Raspberry Pi 4 ARM64, Debian 13, Docker Compose 5.6.0.
- Point d'accès actif sur `192.168.81.1/24`, Ethernet pour l'administration.
- Certificats préparés selon [certificats-journal.md](certificats-journal.md).
- Horloge du Pi synchronisée et contrôleur mémoire cgroups actif.
- Image `debian:trixie-slim`, Python 3, OpenSSL 3 et paquet Debian
  `python3-aiohttp`, installés par le Dockerfile du journal.

Les paquets suivent les mises à jour Debian; relever leurs versions et
l'identifiant d'image pour reproduire un déploiement. Les tests de préparation
passent avec Python 3.12.14, aiohttp 3.11.16 et 3.14.5. La construction ARM64 et
l'exécution de ces nouveaux tests sur le Pi doivent être validées avant démarrage.

## 1. Construire et tester sur le Pi

Depuis la racine de la copie du dépôt du Raspberry Pi :

~~~bash
hostname
git branch --show-current
git status --short
git pull --ff-only origin feature/journal-evenements-securise
sudo docker compose -f compose.local.yaml build journal-evenements
bash scripts/verifier.sh journal
bash scripts/verifier.sh journal-https
~~~

La branche attendue est `feature/journal-evenements-securise`.
Les suites attendues sont respectivement 14 et 15 tests, terminés par `OK`.
Les tests HTTPS utilisent une PKI temporaire, des bases temporaires et la boucle
locale du conteneur sans réseau externe; ils ne montent pas les clés du banc et
n'ajoutent pas d'événements au journal d'exploitation.

Relever les versions de l'image construite :

~~~bash
sudo docker compose -f compose.local.yaml run --rm -T --entrypoint dpkg-query journal-evenements -W python3 python3-aiohttp openssl
sudo docker image inspect controle-acces-journal:local --format '{{.Id}}'
~~~

## 2. Transférer uniquement les fichiers serveur

Depuis l'EliteBook, à la racine du dépôt :

~~~bash
ssh david@10.0.0.111 'umask 077; mkdir -p "$HOME/.config/controle-acces/journal-pki"; chmod 700 "$HOME/.config/controle-acces/journal-pki"'
scp secrets/journal-pki/pi/{ca.cert.pem,serveur.cert.pem,serveur.cle.pem,controleurs.json} david@10.0.0.111:.config/controle-acces/journal-pki/
ssh david@10.0.0.111 'chmod 600 "$HOME/.config/controle-acces/journal-pki/"*'
~~~

Adapter le compte et l'adresse Ethernet à son banc. Ne jamais transférer les
dossiers `autorite/` ou `esp32/` au Pi. Ne pas régénérer les certificats déjà valides.

Sur le Pi :

~~~bash
cd "$HOME/.config/controle-acces/journal-pki"
openssl verify -x509_strict -CAfile ca.cert.pem -purpose sslserver -verify_ip 192.168.81.1 serveur.cert.pem
timedatectl show -p NTPSynchronized -p TimeUSec
~~~

Attendre `serveur.cert.pem: OK` et une horloge correcte.

## 3. Installer les secrets pour le conteneur non root

Le conteneur utilise l'UID et le GID numériques `10001:10001`.
Les fichiers personnels en mode `0600` ne sont pas directement lisibles par cet
utilisateur. Installer une copie réservée au service, hors du dépôt :

~~~bash
sudo install -d -o root -g 10001 -m 0750 /etc/controle-acces/journal-pki
for fichier in ca.cert.pem serveur.cert.pem serveur.cle.pem controleurs.json; do
  sudo install -o root -g 10001 -m 0640 \
    "$HOME/.config/controle-acces/journal-pki/$fichier" \
    "/etc/controle-acces/journal-pki/$fichier"
done
sudo ls -ln /etc/controle-acces/journal-pki
~~~

Attendre propriétaire `0`, groupe `10001` et permissions `-rw-r-----`.
Ces quatre fichiers sont montés en lecture seule. La clé serveur n'est jamais
ajoutée à l'image Docker. Les autres utilisateurs hôtes ne doivent pas appartenir
au groupe numérique du service.

## 4. Sauvegarder avant migration

Arrêter le serveur OpenSSL temporaire avec Ctrl+C. S'il existe déjà un service
HTTPS du journal, l'arrêter depuis la racine du dépôt :

~~~bash
sudo docker compose -f compose.local.yaml stop journal-https
~~~

Pour un journal déjà initialisé, créer une copie SQLite cohérente dans le volume :

~~~bash
sudo docker compose -f compose.local.yaml run --rm -T --entrypoint python3 journal-evenements - <<'PY'
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import os
import sqlite3
os.umask(0o077)
source = Path("/donnees/journal-evenements.sqlite3")
nom = datetime.now(timezone.utc).strftime("journal-avant-mtls-%Y%m%dT%H%M%S%fZ.sqlite3")
destination = source.with_name(nom)
with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as entree:
    fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    with closing(sqlite3.connect(destination)) as sortie:
        entree.backup(sortie)
        assert sortie.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
print("SAUVEGARDE_OK")
PY
~~~

Cette copie reste sur le même support; elle ne remplace pas une sauvegarde externe
protégée et une procédure de restauration testée. Si le journal n'existe pas encore,
utiliser d'abord la commande `initialiser` du [guide local](journal-evenements.md).

Le schéma v1 est migré vers v2 dans une transaction au premier démarrage du service
ou à la prochaine écriture. Les numéros, contenus, origines `TEST_LOCAL` et dates
existants sont conservés. La migration n'efface pas le volume. Ne pas redéployer
l'ancien code v1 sur la base migrée; il refuse le schéma v2.

## 5. Démarrer et contrôler l'exposition

Toujours depuis la racine du dépôt du Pi :

~~~bash
nmcli -f GENERAL.STATE,GENERAL.CONNECTION device show wlan0
ip -brief address show wlan0
sudo docker compose -f compose.local.yaml up -d --no-build journal-https
sudo docker compose -f compose.local.yaml ps journal-https
sudo docker compose -f compose.local.yaml logs --tail 20 journal-https
sudo docker compose -f compose.local.yaml port journal-https 8443
~~~

Si nécessaire, activer d'abord le profil du banc avec
`sudo nmcli --ask connection up controle-acces-ap`.

La publication attendue est uniquement `192.168.81.1:8443`, jamais
`0.0.0.0:8443` ou l'adresse Ethernet. Le programme écoute sur toutes les interfaces
**à l'intérieur du conteneur**; Docker limite l'adresse publiée sur l'hôte.
Le conteneur doit rester actif. Le message `CONFIGURATION_HTTPS_VALIDEE` confirme
le chargement des clés, droits et base; vérifier également l'état du conteneur et
le test HTTPS, car ce message précède l'ouverture du port.

Le service n'a pas de redémarrage automatique à cette étape. Le réseau bridge
Docker n'interdit pas les connexions sortantes; le programme ne réalise aucun
appel réseau sortant. La liaison à l'adresse Wi-Fi ne remplace pas mTLS ni une
politique de filtrage réseau.

## 6. Faire un envoi authentifié depuis l'EliteBook

Dans un terminal de l'EliteBook, ouvrir le tunnel d'administration :

~~~bash
ssh -N -L 127.0.0.1:18443:192.168.81.1:8443 david@10.0.0.111
~~~

Dans un autre terminal de l'EliteBook, à la racine du dépôt, générer un UUID neuf
pour cet essai. Conserver la variable pour tester une retransmission :

~~~bash
id_evenement=$(python3 -c 'import uuid; print(uuid.uuid4())')
message=$(printf '{"version":1,"id_evenement":"%s","porte":"PORTE-01","type":"SORTIE_MANUELLE_SIMULEE"}' "$id_evenement")
curl --silent --show-error --fail-with-body \
  --connect-timeout 5 --max-time 10 \
  --cacert secrets/journal-pki/esp32/ca.cert.pem \
  --cert secrets/journal-pki/esp32/controleur.cert.pem \
  --key secrets/journal-pki/esp32/controleur.cle.pem \
  --connect-to 192.168.81.1:8443:127.0.0.1:18443 \
  -H 'Content-Type: application/json' \
  --data-binary "$message" \
  -w '\nHTTP %{http_code}\n' \
  https://192.168.81.1:8443/v1/evenements
~~~

Le certificat serveur est toujours vérifié pour `192.168.81.1`, malgré le tunnel.
Ne pas ajouter `-k` ou `--insecure`.

Attendre HTTP `201`, statut `ENREGISTRE`, UUID et date UTC de réception.
Rejouer exactement la commande curl sans régénérer les variables :
attendre HTTP `200`, `DEJA_PRESENT` et la même date.

Sur le Pi :

~~~bash
sudo docker compose -f compose.local.yaml run --rm -T journal-evenements lire --limite 20
~~~

L'événement doit porter `origine: MTLS` et `controleur: SECTEUR-01`.
Ici le client est un outil de test utilisant la clé destinée au contrôleur;
cela ne prouve pas encore un envoi par le matériel ESP32.

## Contrôles et limites

- Certificat client absent, autorité inconnue ou rôle serveur utilisé comme client :
  refus TLS avant traitement HTTP.
- Certificat valide mais empreinte absente de `controleurs.json` :
  HTTP `403`. L'identité provient uniquement de l'empreinte du certificat TLS.
- Porte non attribuée au contrôleur : HTTP `403`.
- JSON invalide ou champs supplémentaires : HTTP `400`; corps supérieur à
  1 024 octets : HTTP `413`; corps incomplet après cinq secondes : HTTP `408`.
- Identifiant déjà utilisé avec un autre contenu **ou une autre origine** :
  HTTP `409`. Un essai `TEST_LOCAL` ne devient jamais rétroactivement `MTLS`.
- Stockage indisponible ou deux traitements déjà en cours : HTTP `503`.
  Réessayer avec le même UUID après un délai; ne pas annoncer un enregistrement
  avant un accusé de réception valide.
- SQLite est validé avant la réponse. Aucune identité personnelle, clé ou charge
  de requête n'est écrite dans les logs d'accès; ces logs sont désactivés.
- Le conteneur limite mémoire et processus et borne ses logs Docker. Cela ne
  constitue pas une protection complète contre le déni de service.
- Pour retirer un contrôleur, arrêter le service, modifier la liste privée des
  droits et redémarrer. Les droits sont chargés au démarrage. Une configuration
  vide ou invalide empêche le démarrage; arrêter le service pour révoquer tous
  les contrôleurs. Le renouvellement des certificats reste manuel.
- La base et ses sauvegardes restent non chiffrées au repos. Ne pas introduire
  d'identités réelles avant les politiques d'accès, de rétention et de restauration.
- Restent à implémenter côté ESP32 : horloge après mise sous tension, validation
  du certificat serveur, envoi mTLS, file d'attente et retransmissions.

Références : [Python SSL](https://docs.python.org/3.13/library/ssl.html),
[aiohttp serveur](https://docs.aiohttp.org/en/stable/web_reference.html),
[paquet Debian trixie](https://packages.debian.org/trixie/python3-aiohttp).


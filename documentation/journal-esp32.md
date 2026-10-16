# Envoyer les sorties simulées de l'ESP32 au journal du Pi

## Portée et limites

Chaque appui BOOT validé par l'anti-rebond ajoute un événement
`SORTIE_MANUELLE_SIMULEE` pour `PORTE-01`. Un appui maintenu ne se répète pas;
un nouvel appui distinct pendant les cinq secondes de simulation produit un
nouvel événement. La fin des cinq secondes ne produit aucun événement.

La file contient au maximum huit événements, y compris celui en cours d'envoi.
Elle est en RAM uniquement : reset, téléversement, coupure ou panne d'alimentation
perdent les événements non confirmés. Aucun stockage SD ou flash n'est ajouté.
Un événement déjà validé par le Pi reste dans SQLite même si son accusé n'a pas
atteint la carte.

La simulation locale ne dépend pas de la réception du serveur. Elle ne commande
aucune serrure, ne prouve aucun passage et n'identifie aucune personne.
Ne pas utiliser de données personnelles réelles dans ce banc.

## Fonctionnement

1. Au nouvel appui, générer un UUID v4 et essayer d'ajouter l'événement sans attente.
2. Si la file est pleine, conserver les anciens événements et refuser le nouveau.
   Afficher `Journal: PERTE RAM` et conserver l'erreur orange jusqu'au redémarrage.
   Le moniteur indique la perte. La simulation BOOT reste fonctionnelle.
3. Une tâche séparée attend le réseau et une heure SNTP reçue et récente.
4. Envoyer la tête par HTTPS mTLS à `192.168.81.1:8443/v1/evenements`.
5. Accepter seulement HTTP 201/`ENREGISTRE` ou HTTP 200/`DEJA_PRESENT`,
   avec le même UUID et un horodatage UTC de réception dans la réponse.
6. Retirer la tête uniquement après cet accusé, puis traiter la suivante.
7. Sans confirmation valide, garder le même UUID et le même contenu et attendre
   dix secondes avant un nouvel essai. Aucun ancien événement n'est écrasé.

Le serveur contrôle l'empreinte du certificat et les droits sur la porte.
Le JSON n'inclut ni identité de contrôleur déclarée librement, ni date de l'appui.
L'horodatage conservé par le Pi est la date de réception, pas une preuve de l'heure
de l'appui.

Une erreur persistante, notamment HTTP 400/403/409, bloque la tête sans la supprimer.
Corriger la configuration ou la cause côté serveur avant de poursuivre.
Aucune purge automatique n'est réalisée. Réinitialiser la carte perdrait la file.

## 1. Préparer le Raspberry Pi

Depuis la racine du dépôt du Pi :

~~~bash
ip -brief address show wlan0
systemctl is-active chrony
chronyc tracking
sudo docker compose -f compose.local.yaml ps journal-https
sudo docker compose -f compose.local.yaml run --rm -T journal-evenements lire --limite 20
~~~

Attendre `192.168.81.1/24`, chrony actif et synchronisé, et HTTPS actif sur
`192.168.81.1:8443`. Noter les dernières lignes du journal pour comparer après
les essais. Voir [installation HTTPS](journal-https.md) et [heure ESP32](heure-esp32.md).

## 2. Configurer et compiler sur l'EliteBook

À la racine du dépôt :

~~~bash
git pull --ff-only origin feature/journal-evenements-securise
source "$HOME/.espressif/tools/activate_idf_v5.3.6.sh"
cd controleur-esp32
~~~

Conserver les fichiers privés déjà utilisés pour le diagnostic mTLS :

- `main/configuration-wifi.locale.h` avec les identifiants du point d'accès;
- `main/configuration-journal.locale.cmake` activant `CONTROLE_JOURNAL_MTLS`;
- les trois PEM dans `secrets/journal-pki/esp32/`, à la racine du dépôt.

Pour une nouvelle installation seulement :

~~~bash
cp -n main/configuration-journal.exemple.cmake main/configuration-journal.locale.cmake
~~~

Activer la vérification des dates dans un sdkconfig existant si nécessaire :

~~~bash
sed -i 's/^# CONFIG_MBEDTLS_HAVE_TIME_DATE is not set$/CONFIG_MBEDTLS_HAVE_TIME_DATE=y/' sdkconfig
idf.py reconfigure
grep '^CONFIG_MBEDTLS_HAVE_TIME_DATE=' sdkconfig
idf.py build
~~~

Attendre `CONFIG_MBEDTLS_HAVE_TIME_DATE=y` et une compilation réussie.
Le code refuse les options de contournement TLS. Sans activation locale, le
journal réseau reste désactivé et le LCD affiche `Journal: desactive`.

Le binaire et les assemblages générés contiennent la clé privée client :
ne pas publier le build, les fichiers BIN/ELF ou leurs archives. Aucun secret
n'est ajouté au dépôt. Le transport conserve la vérification de l'autorité,
du SAN IP `192.168.81.1`, des dates et du certificat client. Aucune redirection
HTTP n'est suivie; TLS 1.2 est sélectionné explicitement.

SNTP demeure non authentifié. Ni secure boot ni chiffrement de flash ne sont
activés par ce programme.

## 3. Tester un appui en ligne

Après compilation :

~~~bash
idf.py -p /dev/ttyACM0 flash monitor
~~~

Attendre le Wi-Fi et la réception de l'heure. Le diagnostic vide HTTP 400 n'est
plus lancé automatiquement : le programme courant attend les appuis BOOT.

Appuyer une seule fois, puis relâcher. Attendre :

~~~text
JOURNAL: Sortie simulee en file RAM: UUID
JOURNAL: Enregistrement confirme par le Pi: UUID
~~~

Le LCD indique `Journal: confirme` après l'accusé. Le vert reste réservé à la
simulation de sortie pendant cinq secondes; le repos est bleu. Les erreurs Wi-Fi,
d'heure ou d'envoi et les pertes de file ont priorité et donnent l'orange.

Sur le Pi :

~~~bash
sudo docker compose -f compose.local.yaml run --rm -T journal-evenements lire --limite 20
~~~

Attendre une nouvelle ligne `MTLS`, avec le même UUID et `SECTEUR-01`.
Un appui prolongé ne doit ajouter qu'une ligne. Un deuxième appui distinct doit
produire un autre UUID.

## 4. Tester la reprise sans couper l'alimentation

Sur le Pi, arrêter uniquement le service HTTPS :

~~~bash
sudo docker compose -f compose.local.yaml stop journal-https
~~~

Garder le point d'accès et chrony actifs. Ne pas débrancher ni réinitialiser
l'ESP32. Faire deux appuis distincts. Vérifier que la simulation fonctionne et
que les UUID restent en attente. Le LCD signale l'erreur d'envoi.

Sur le Pi, rétablir le service :

~~~bash
sudo docker compose -f compose.local.yaml up -d --no-build journal-https
~~~

Attendre la reprise automatique. Les UUID confirmés doivent être ceux des appuis
en attente, sans création d'un nouvel UUID à chaque tentative. Vérifier les
lignes SQLite et l'absence de doublons.

Pour tester la perte d'un accusé après écriture sans dépendre d'un timing réseau,
utiliser les tests de logique ci-dessous et les tests d'idempotence du serveur.
Un simple arrêt avant écriture ne prouve pas ce cas.

## 5. Tester la saturation

Avec HTTPS arrêté et la carte toujours alimentée, produire neuf appuis distincts.
La file vide initiale en accepte huit. Le neuvième est perdu avec un message
explicite. Si des événements étaient déjà en attente, la saturation intervient
plus tôt. Les anciens restent conservés.

Rétablir HTTPS et vérifier l'envoi des huit événements retenus.
`Journal: PERTE RAM` reste affiché même après vidage : l'événement perdu ne
peut pas être récupéré et l'erreur ne doit pas disparaître silencieusement.
Ne redémarrer qu'après vérification de la livraison des événements conservés.

## Tests de logique sur ordinateur

Depuis la racine du dépôt, avec un compilateur C :

~~~bash
cc -std=gnu11 -Wall -Wextra -Werror -DJOURNAL_MTLS_PRESENT=1 \
  -I controleur-esp32/tests/diagnostic-mtls/stubs \
  controleur-esp32/tests/journal-client/test_file.c -o /tmp/test-file-journal
/tmp/test-file-journal
~~~

Pour le transport et les accusés, avec ESP-IDF installé :

~~~bash
source "$HOME/.espressif/tools/activate_idf_v5.3.6.sh"
cc -std=gnu11 -Wall -Wextra -Werror \
  -DJOURNAL_MTLS_PRESENT=1 -DCONFIG_MBEDTLS_HAVE_TIME_DATE=1 \
  -I controleur-esp32/tests/diagnostic-mtls/stubs \
  -I "$IDF_PATH/components/json/cJSON" \
  controleur-esp32/tests/diagnostic-mtls/test_diagnostic.c \
  "$IDF_PATH/components/json/cJSON/cJSON.c" -o /tmp/test-accuses-journal
/tmp/test-accuses-journal
~~~

Ces tests emploient des doubles FreeRTOS/HTTP et aucune clé réelle. Ils couvrent
FIFO, UUID, saturation, retransmission identique après échec, retrait après
confirmation, perte persistante à l'écran, réponses fragmentées ou invalides,
codes HTTP inattendus, mauvais UUID et horodatage absent ou mal formé.
Ils ne remplacent pas la compilation ESP-IDF ni le test sur la carte.

Le contrôle des accusés est testé sur hôte. La compilation et les essais de cette
version avec file RAM restent à valider sur le banc.

Références : [esp_http_client](https://github.com/espressif/esp-idf/blob/v5.3.6/components/esp_http_client/include/esp_http_client.h),
[générateur matériel](https://github.com/espressif/esp-idf/blob/v5.3.6/components/esp_hw_support/include/esp_random.h).

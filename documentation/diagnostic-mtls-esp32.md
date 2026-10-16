# Tester mTLS depuis la carte ESP32

## Objectif

Ce diagnostic vérifie une connexion HTTPS depuis l'ESP32 vers le Pi avant de
raccorder BOOT au journal. Il envoie uniquement `{}` sur `POST /v1/evenements`.
Le serveur doit répondre HTTP 400 avec `EVENEMENT_INVALIDE`, après avoir vérifié
le certificat client et son empreinte autorisée. Aucun événement n'est créé.

Le diagnostic s'exécute dans une tâche séparée, après connexion Wi-Fi et réception
d'une date SNTP plausible et récente. Les messages sont affichés sur USB.
L'interface LCD et la simulation BOOT restent indépendantes de ce test.

## Préparer le Pi

Le [service HTTPS du journal](journal-https.md), le point d'accès et
[chrony](heure-esp32.md) doivent fonctionner :

~~~bash
hostname
ip -brief address show wlan0
systemctl is-active chrony
chronyc tracking
sudo docker compose -f compose.local.yaml ps journal-https
~~~

Attendre `192.168.81.1/24`, chrony actif et synchronisé, et le service HTTPS
actif sur `192.168.81.1:8443`. Exécuter ces commandes sur le Pi, depuis la racine
de sa copie du dépôt.

Aucun tunnel SSH n'est nécessaire pour l'ESP32 : il joint le Pi directement sur
le réseau Wi-Fi privé.

## 1. Vérifier les fichiers sur l'EliteBook

Depuis la racine du dépôt :

~~~bash
git branch --show-current
git status --short
git pull --ff-only origin feature/journal-evenements-securise

for fichier in ca.cert.pem controleur.cert.pem controleur.cle.pem; do
  test -s "secrets/journal-pki/esp32/$fichier" \
    && echo "$fichier : present" \
    || echo "$fichier : MANQUANT"
done
git check-ignore secrets/journal-pki/esp32/controleur.cle.pem
~~~

Les trois fichiers doivent être présents et la clé ignorée par Git.
Ne pas afficher leur contenu. La clé d'autorité et la clé serveur ne sont pas
utilisées par la carte.

## 2. Activer volontairement le diagnostic

Toujours sur l'EliteBook :

~~~bash
source "$HOME/.espressif/tools/activate_idf_v5.3.6.sh"
cd controleur-esp32
cp -n main/configuration-journal.exemple.cmake main/configuration-journal.locale.cmake
~~~

Le fichier local active `CONTROLE_JOURNAL_MTLS`. Il est ignoré par Git.
Le CMake embarque directement les trois PEM depuis `secrets/journal-pki/esp32/`;
aucune copie dans les sources n'est nécessaire. La configuration Wi-Fi privée
doit aussi être présente. Sans activation locale, le diagnostic reste désactivé
et le mode LCD/Wi-Fi habituel peut être compilé sans PKI.

**Le micrologiciel et les fichiers de compilation contiennent désormais la clé
privée client.** Garder localement les fichiers BIN, ELF, les assemblages générés
et toute archive du dossier build. Ils sont exclus de Git et du contexte Docker.
Le dépôt reste public, sans clé ni binaire contenant une clé.

Cette étape ne configure ni chiffrement de flash ni secure boot. Une personne
ayant accès au binaire ou à la carte pourrait extraire la clé client. La
protection physique et le provisionnement par équipement restent à concevoir.

## 3. Activer explicitement les vérifications de dates

ESP-IDF 5.3.6 propose une vérification des dates X.509 désactivée par défaut.
Le dépôt active maintenant `CONFIG_MBEDTLS_HAVE_TIME_DATE=y` dans
sdkconfig.defaults. Un sdkconfig déjà créé doit aussi être mis à jour.

Dans `controleur-esp32/`, pour le sdkconfig existant du banc :

~~~bash
sed -i 's/^# CONFIG_MBEDTLS_HAVE_TIME_DATE is not set$/CONFIG_MBEDTLS_HAVE_TIME_DATE=y/' sdkconfig
idf.py reconfigure
grep '^CONFIG_MBEDTLS_HAVE_TIME_DATE=' sdkconfig
idf.py build
~~~

Attendre `CONFIG_MBEDTLS_HAVE_TIME_DATE=y`. Si nécessaire, utiliser
`idf.py menuconfig`, menu Component config → mbedTLS →
Enable mbedtls certificate expiry check.

Le code refuse de compiler le diagnostic si les dates ne sont pas vérifiées ou
si les options `CONFIG_ESP_TLS_INSECURE` ou
`CONFIG_ESP_TLS_SKIP_SERVER_CERT_VERIFY` sont activées.

La chaîne de certification est vérifiée contre l'autorité privée du banc,
l'identité serveur attendue est `192.168.81.1` (SAN IP du certificat), et les dates
sont vérifiées avec l'heure système. Aucune redirection HTTP n'est suivie.
TLS 1.2 est sélectionné explicitement pour ce diagnostic reproductible.

SNTP reste non authentifié : le contrôle des dates activé ne transforme pas la
source de temps en source de confiance cryptographique. Voir les limites du
[guide de l'heure](heure-esp32.md).

## 4. Téléverser et tester

Après compilation réussie :

~~~bash
idf.py -p /dev/ttyACM0 flash monitor
~~~

Attendre successivement :

~~~text
RESEAU: Wi-Fi connecte, IP=192.168.81.2
HORLOGE: Heure recue du Pi (SNTP): ...
MTLS_TEST: Diagnostic mTLS OK: HTTP 400 EVENEMENT_INVALIDE; aucun evenement cree
~~~

HTTP 400 est ici le résultat attendu : le message vide est volontairement
invalide. Ce test prouve la réception d'une réponse du service authentifié,
pas l'enregistrement d'une sortie physique.

Le diagnostic ne s'exécute plus après le premier succès de ce démarrage.
Il ne constitue pas une surveillance permanente de disponibilité. Tester aussi
le LCD et BOOT pendant le test. BOOT ne génère toujours aucun événement réseau.

Sur le Pi, vérifier qu'aucune ligne n'a été ajoutée par ce diagnostic :

~~~bash
sudo docker compose -f compose.local.yaml run --rm -T journal-evenements lire --limite 5
~~~

Comparer avec la lecture préalable du journal. Ne pas utiliser de données
personnelles pour cet essai.

## En cas d'échec

- `Diagnostic desactive` : vérifier le fichier CMake local, puis reconfigurer.
- Fichier PKI manquant : le build activé s'arrête; ne pas contourner la vérification.
- Pas de ligne HORLOGE : vérifier chrony sur le Pi et le point d'accès.
- Erreur de certificat : vérifier les dates, la chaîne, l'IP et les rôles;
  ne jamais désactiver la validation pour obtenir une connexion.
- HTTP 403 : certificat signé mais empreinte non autorisée par le service.
- Autre réponse, corps invalide, réponse incomplète ou supérieure à 255 octets :
  diagnostic non validé.
- Les échecs sont retentés après dix secondes, à condition que le réseau et
  l'heure soient disponibles. L'affichage et BOOT continuent dans app_main.
- Les logs ne reproduisent ni la clé, ni le certificat, ni le corps brut reçu.

Pour désactiver le diagnostic, mettre `CONTROLE_JOURNAL_MTLS OFF` dans le fichier
local ou le retirer, puis reconfigurer, reconstruire et téléverser. Cela ne
révoque pas la clé déjà embarquée; sa révocation se fait côté Pi.

## Test de logique sur un ordinateur

Ce test utilise des doubles des API HTTP et FreeRTOS, sans réseau ni vraie clé.
Depuis la racine du dépôt, avec un compilateur C et ESP-IDF installé :

~~~bash
source "$HOME/.espressif/tools/activate_idf_v5.3.6.sh"
cc -std=gnu11 -Wall -Wextra -Werror \
  -DJOURNAL_MTLS_PRESENT=1 -DCONFIG_MBEDTLS_HAVE_TIME_DATE=1 \
  -I controleur-esp32/tests/diagnostic-mtls/stubs \
  -I "$IDF_PATH/components/json/cJSON" \
  controleur-esp32/tests/diagnostic-mtls/test_diagnostic.c \
  "$IDF_PATH/components/json/cJSON/cJSON.c" \
  -o /tmp/test-diagnostic-mtls
/tmp/test-diagnostic-mtls
~~~

Les tests vérifient la configuration du client, le corps vide, les réponses
fragmentées, la validation du refus attendu, les autres codes HTTP, les réponses
invalides ou trop grandes, le nettoyage du client et le déclenchement différé.
Ils ne prouvent pas un échange TLS réel : la compilation ESP-IDF et la validation
sur la carte restent nécessaires.

Après validation de cette étape, ajouter séparément la file d'événements BOOT,
les UUID conservés lors des retransmissions et la confirmation d'enregistrement
après accusé de réception du Pi.

Références : [client HTTP ESP-IDF 5.3.6](https://github.com/espressif/esp-idf/blob/v5.3.6/components/esp_http_client/include/esp_http_client.h),
[vérification des dates](https://github.com/espressif/esp-idf/blob/v5.3.6/components/mbedtls/Kconfig),
[vérification des noms et SAN IP dans le Mbed TLS du SDK](https://github.com/espressif/mbedtls/blob/2b96dd8eebe880f304c69976b3c2fa0c5100cbb6/library/x509_crt.c).

# Transport et diagnostic mTLS de l'ESP32

Le transport mTLS vérifie l'autorité privée du banc, le SAN IP `192.168.81.1`, les dates des certificats et présente le certificat client au Pi. Les tests de connexion depuis la carte ont été validés avant la journalisation des appuis.

Pour installer et utiliser le programme courant, suivre le [guide du journal ESP32](journal-esp32.md). Le diagnostic vide HTTP 400 n'est plus lancé automatiquement; le programme attend les appuis BOOT et valide les accusés d'enregistrement.

Le module `diagnostic-mtls.c` conserve les fonctions `diagnostic_mtls_initialiser` et `diagnostic_mtls_actualiser` pour un programme de diagnostic isolé : initialiser une fois, puis transmettre l'état réseau et heure depuis app_main. Ne pas lancer simultanément ce diagnostic et le journal dans le programme normal. Le diagnostic isolé envoie `{}` et attend HTTP 400/`EVENEMENT_INVALIDE`, sans créer d'événement.

La fonction `mtls_enregistrer` est appelée uniquement depuis la tâche du journal. Elle accepte HTTP 201/`ENREGISTRE` ou HTTP 200/`DEJA_PRESENT`, avec UUID correspondant et date UTC de réception. Elle ne retire aucun élément de la file elle-même.

Les secrets restent locaux et les binaires contenant la clé privée ne doivent pas être publiés. La vérification des dates doit être activée avec `CONFIG_MBEDTLS_HAVE_TIME_DATE=y`; les options de contournement empêchent la compilation. L'heure SNTP reste non authentifiée.

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


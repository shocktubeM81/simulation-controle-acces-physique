# Synchroniser l'heure de l'ESP32 depuis le Pi

## Portée

Le contrôleur reçoit l'heure par SNTP depuis `192.168.81.1`, sans accès Internet
direct ni serveur fourni par DHCP. L'API utilisée est `esp_netif_sntp` d'ESP-IDF
5.3.6. L'affichage et le bouton BOOT continuent de fonctionner pendant l'attente.

Cette étape prépare la vérification des dates des certificats. Elle n'ajoute
aucun envoi HTTPS et ne désactive aucune vérification TLS. SNTP n'authentifie pas
l'heure reçue : un acteur capable de falsifier les réponses sur le réseau pourrait
fausser l'horloge. Le filtre de date 2024–2099 est seulement un contrôle de
cohérence, pas une protection contre une attaque ou un retour en arrière.

## 1. Fournir l'heure sur le Raspberry Pi

Configuration de référence : Debian 13 ARM64, chrony
`4.6.1-3+deb13u2`, Ethernet pour les sources NTP amont et point d'accès Wi-Fi sur
`192.168.81.1/24`. Le contrôleur utilise `192.168.81.2`.

~~~bash
sudo apt update
sudo apt install chrony
chronyc waitsync 12 0.1
chronyc tracking
chronyc sources -v
~~~

L'installation remplace éventuellement `systemd-timesyncd`.
Attendre `Leap status : Normal` et une source `^*`; la commande waitsync est
bornée à environ deux minutes. Ne pas configurer une fausse référence locale
pour contourner une absence de synchronisation amont.

Vérifier que `/etc/chrony/chrony.conf` inclut
`confdir /etc/chrony/conf.d`, puis installer la configuration du banc :

~~~bash
sudo tee /etc/chrony/conf.d/controle-acces.conf >/dev/null <<'EOF'
# Serveur NTP du banc, reserve au controleur ESP32.
bindaddress 192.168.81.1
binddevice wlan0
allow 192.168.81.2/32
EOF

sudo chronyd -p >/dev/null &&
sudo systemctl restart chrony
~~~

Vérifier :

~~~bash
systemctl is-active chrony
sudo ss -lunp 'sport = :123'
sudo chronyc accheck 192.168.81.2
sudo chronyc accheck 10.0.0.111
chronyc tracking
~~~

Résultats attendus : `active`, écoute UDP `192.168.81.1:123`,
`208 Access allowed` pour le contrôleur, `209 Access denied` pour l'adresse
Ethernet et horloge synchronisée. Adapter l'adresse Ethernet du test au banc.
Un `501 Not authorised` de chronyc indique un défaut de permission de la commande
de contrôle; ce n'est pas le résultat de la règle NTP. Utiliser sudo.

Les règles par adresse IP limitent l'accès au service mais n'authentifient pas
cryptographiquement les paquets. Ne pas ouvrir UDP 123 sur le routeur Internet.
Après redémarrage du Pi, activer le point d'accès du banc si nécessaire.

## 2. Compiler sur l'EliteBook

Depuis la racine du dépôt, sur `feature/journal-evenements-securise` :

~~~bash
git pull --ff-only origin feature/journal-evenements-securise
source "$HOME/.espressif/tools/activate_idf_v5.3.6.sh"
cd controleur-esp32
idf.py reconfigure
idf.py build
~~~

Le fichier privé de configuration Wi-Fi reste nécessaire pour joindre le Pi.
Il ne doit pas être publié. Sans ce fichier, le mode LCD reste disponible et
SNTP ne démarre pas.

La logique d'attente, de reprise et de reconnexion a été vérifiée sur un hôte
avec des doubles des API ESP-IDF. Cela ne remplace pas la compilation avec le
SDK ni le test sur la carte.

Test de logique facultatif depuis la racine du dépôt, avec un compilateur C :

~~~bash
cc -std=c11 -Wall -Wextra -Werror \
  -I controleur-esp32/tests/horloge/stubs \
  controleur-esp32/tests/horloge/test_horloge.c \
  -o /tmp/test-horloge
/tmp/test-horloge
~~~

Les doubles simulent uniquement le SDK et l'horloge; ils ne contactent pas le
Pi et ne prouvent pas la réception de paquets NTP.

## 3. Téléverser et observer

Depuis `controleur-esp32/`, dans le terminal ESP-IDF actif :

~~~bash
idf.py -p /dev/ttyACM0 flash monitor
~~~

Après acquisition de l'adresse Wi-Fi, attendre le message :

~~~text
HORLOGE: Attente SNTP depuis 192.168.81.1; heure non authentifiee
HORLOGE: Heure recue du Pi (SNTP): AAAA-MM-JJTHH:MM:SSZ
~~~

Comparer la date UTC à `date -u` sur le Pi. Le LCD affiche
`Heure recue du Pi / SNTP non authentifie`. Il n'affiche pas une horloge animée.

Le texte occupe 156 pixels sur les 172 pixels de largeur, avec huit pixels de
marge de chaque côté et retour automatique à la ligne. Vérifier que les messages
d'attente, d'erreur et de sortie BOOT restent entièrement visibles.

Tester le bouton BOOT : la simulation de sortie doit toujours fonctionner.
Le vert indique la sortie autorisée simulée, le repos reste bleu, l'orange
signale une erreur réseau ou d'heure.

## 4. Valider après coupure d'alimentation

1. Quitter le moniteur avec Ctrl+T puis X.
2. Débrancher complètement l'USB de la carte, puis la rebrancher.
3. Relancer `idf.py -p /dev/ttyACM0 monitor`.
4. Vérifier une nouvelle connexion Wi-Fi puis une nouvelle réception SNTP avec
   date UTC correcte, sans utiliser RESET pour obtenir la connexion.
5. Vérifier BOOT après synchronisation.

Un RESET seul ne valide pas le comportement après perte complète d'alimentation.
Aucun état de confiance de l'heure n'est restauré depuis la mémoire persistante.

## 5. Tester une indisponibilité de l'heure

Pendant que l'ESP32 reste connecté au Wi-Fi, sur le Pi :

~~~bash
sudo systemctl stop chrony
~~~

Couper puis rétablir l'alimentation de l'ESP32. Il doit rester utilisable et
afficher une erreur orange après environ 30 secondes sans réponse SNTP.
La sortie BOOT reste simulée localement; cela n'enregistre aucun événement.

Rétablir ensuite chrony :

~~~bash
sudo systemctl start chrony
chronyc tracking
~~~

Attendre une réception SNTP automatique sur la carte. Le délai de reprise dépend
des temporisations de lwIP; il n'est pas garanti à cinq secondes.
Vérifier aussi la reprise après désactivation puis réactivation du point d'accès.

## Comportement du module

- Initialisation SNTP au premier état Wi-Fi connecté, après initialisation réseau.
- Lecture des notifications sans attente dans app_main; aucune manipulation LVGL
  depuis une tâche réseau.
- Nouvelle acquisition demandée après une déconnexion Wi-Fi observée.
- Réessai des erreurs d'initialisation ou de démarrage de l'API au plus toutes
  les cinq secondes.
- Absence de première réponse après 30 secondes : erreur visible; les essais SNTP
  continuent selon lwIP.
- Plus de six heures sans nouvelle notification : erreur visible, mesurée avec
  le temps monotone plutôt que l'heure reçue.
- Pas de flag « TLS sûr » exposé par ce module. Une date plausible et une réponse
  SNTP ne constituent pas une preuve cryptographique de l'heure.

Avant des données personnelles ou un déploiement sensible, définir une source de
temps authentifiée ou un amorçage vérifiable avec protection contre le retour en
arrière. Le futur client HTTPS devra toujours vérifier la chaîne, l'adresse du
serveur et les dates des certificats; ne pas ajouter de contournement TLS.

Références : [API ESP-IDF 5.3.6](https://github.com/espressif/esp-idf/blob/v5.3.6/components/esp_netif/include/esp_netif_sntp.h),
[implémentation SNTP ESP-IDF](https://github.com/espressif/esp-idf/blob/v5.3.6/components/esp_netif/lwip/esp_netif_sntp.c),
[configuration chrony](https://chrony-project.org/doc/4.6/chrony.conf.html).

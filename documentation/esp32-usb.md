# ESP32-C6 vers Raspberry Pi par USB

Branche `feature/esp32-usb`, issue de la branche RFID et de sa console.
La carte a été détectée sur le Pi comme USB Serial/JTAG Espressif, `/dev/ttyACM0`.
Ce constat valide la liaison de données, pas encore le nouveau micrologiciel.

## Fonctionnement

L'option CMake `CONTROLE_JOURNAL_USB=ON` réserve USB Serial/JTAG au protocole.
Le Wi-Fi et SNTP ne sont pas démarrés, et les certificats mTLS ne sont pas intégrés
dans ce mode, même si les configurations locales existent. Le mode habituel reste
disponible sans cette option. Le LCD et le bouton BOOT gardent leur rôle de simulation.

L'ESP32 envoie `EVT ` suivi du JSON d'événement existant et d'un saut de ligne.
Le Pi valide les champs, UUID v4, taille (1024 octets) et porte (`PORTE-01`), puis
enregistre dans un volume Docker dédié, `journal_usb`, origine `USB`.
Après le commit SQLite, il répond `ACK ` suivi de l'UUID exact et d'un saut de ligne.
Un UUID déjà enregistré avec le même contenu est confirmé sans nouvelle insertion.
Un contenu différent portant le même UUID est rejeté.

La file RAM de huit places est réutilisée. L'événement en tête n'est retiré qu'après
ACK exact. Un échec conserve l'UUID et déclenche un nouvel essai après dix secondes.
Un ACK peut arriver en retard : la déduplication persistante rend la retransmission sûre.
Les événements encore dans la RAM sont perdus au reset/coupure; saturation et panne
restent visibles sur le LCD. L'heure de réception vient du Pi, sans besoin de SNTP ESP32.

Le journal USB est séparé du journal HTTPS, sans migration de ce dernier ni nouvelle
route réseau. L'identité affichée `ESP32-USB` désigne le port local configuré, sans
authentification cryptographique du matériel. Une réception confirme l'enregistrement,
pas une ouverture physique. Aucun relais n'est actionné.

## 1. Construire sur l'EliteBook

Utiliser le terminal ESP-IDF déjà configuré (version de référence 5.3.6).
Depuis le dépôt, avec un arbre de travail propre :

```bash
git status
git fetch origin
git switch feature/esp32-usb
git pull --ff-only
cd controleur-esp32
idf.py --version
idf.py -B build-usb \
  -D CONTROLE_JOURNAL_USB=ON \
  -D "SDKCONFIG=$PWD/build-usb/sdkconfig" \
  -D "SDKCONFIG_DEFAULTS=$PWD/sdkconfig.defaults;$PWD/sdkconfig.usb.defaults" \
  build
```

Le SDKCONFIG distinct dans `build-usb/` évite de modifier la configuration Wi-Fi existante.
Le profil additionnel désactive la console USB secondaire des paramètres de référence.
Si CMake refuse car USB est encore choisi comme console, ouvrir avec les mêmes options
`menuconfig`, puis choisir console UART et aucune console secondaire. Ne pas supprimer
les secrets locaux ni les anciens builds. Les fichiers de construction restent ignorés.

## 2. Téléverser

Pour cette première procédure, reconnecter temporairement la carte à l'EliteBook.
Arrêter tout moniteur série et relever le port avec `ls -l /dev/serial/by-id/` et
`ls -l /dev/ttyACM*`. Le port doit correspondre à la carte, pas à un autre périphérique.
S'il s'agit de `/dev/ttyACM0` :

```bash
idf.py -B build-usb -p /dev/ttyACM0 flash
```

Ne pas ajouter `monitor` : le port USB est réservé au protocole. Le LCD doit maintenant
indiquer `USB vers Raspberry Pi` et `Sans Wi-Fi`. Rebrancher la carte au Pi.
Le flash/reset perd la file RAM de l'ancien programme; terminer les essais en cours avant.

## 3. Démarrer le récepteur sur le Pi

```bash
cd ~/projets/simulation-controle-acces-physique
git status
git fetch origin
git switch feature/esp32-usb
git pull --ff-only
ls -l /dev/ttyACM0
sudo env USB_GID="$(stat -c '%g' /dev/ttyACM0)" \
  docker compose -f compose.local.yaml -f compose.usb.yaml \
  --profile usb up -d --build journal-usb
```

Le conteneur tourne sous UID 10001, reçoit uniquement le périphérique série et son
groupe, un volume dédié, et aucun réseau. Aucune installation Python série sur l'hôte
n'est nécessaire; `python3-serial` provient de Debian dans l'image.
Le port par défaut est `/dev/ttyACM0`. Pour un nom stable, relever le lien exact dans
`/dev/serial/by-id/`, puis fournir `USB_DEVICE` à la même commande avec `sudo env`.
Le numéro de série n'est pas codé en dur dans le dépôt.

Le récepteur redémarre avec Docker (`unless-stopped`). Il réessaie le port toutes
les deux secondes. Après un débranchement/rebranchement physique, Docker peut garder
l'ancien périphérique : relancer la commande avec `--force-recreate` au lieu de `--build`
et vérifier le port/GID. Ne pas lancer deux récepteurs ou un moniteur sur le même port.

## 4. Console et essai

```bash
sudo -v
~/rfid-test/.venv/bin/python serveur-local/console-acces.py \
  --porte 'Laboratoire' --docker-sudo --bouton usb
```

Attendre `Bouton : USB ouvert`, puis appuyer sur BOOT. La sortie simulée apparaît
dans le terminal après enregistrement, et le LCD doit afficher une confirmation.
Les anciens événements sont ignorés lors de la première connexion de la console;
lancer celle-ci avant l'appui. Les scans RFID utilisent toujours le cache synchronisé.
Le service USB enregistre même si la console est arrêtée.

Diagnostic :

```bash
sudo docker compose -f compose.local.yaml -f compose.usb.yaml logs --tail 30 journal-usb
```

Vérifier également maintien/retrait du badge, refus d'un badge inconnu, redémarrage
du récepteur sans doublon, et conservation de l'UUID après absence d'ACK. Éviter de
débrancher l'alimentation pour tester une file RAM qui doit être conservée.
L'état `USB ouvert` confirme le port ouvert et le récepteur vivant, pas l'identité ni
le chargement du bon micrologiciel : seul un appui confirmé valide le parcours.

Pour arrêter le récepteur avant un flash :

```bash
sudo docker compose -f compose.local.yaml -f compose.usb.yaml stop journal-usb
```

## Vérifications de développement

```bash
python3 -m unittest discover -s serveur-local/tests -p 'test_journal_usb.py' -v
python3 -m unittest discover -s serveur-local/tests -p 'test_console_acces.py' -v
bash controleur-esp32/tests/usb/verifier.sh
```

Tests Python exécutés : journal, ACK après commit, doublons, conflits, données invalides,
trames fragmentées/trop longues, suivi USB et régression console/RFID (22 tests au total).
Tests C construits avec `-Wall -Wextra -Werror` : transport ACK et file RAM USB.
Leur exécution est bloquée par le contrôle d'application Windows de l'environnement
de préparation; les lancer sur Linux avec le script ci-dessus.
La compilation ESP-IDF complète, le flash et le parcours matériel restent à valider.

Référence d'API :
[pilote USB Serial/JTAG ESP-IDF 5.3](https://github.com/espressif/esp-idf/blob/v5.3.3/components/esp_driver_usb_serial_jtag/include/driver/usb_serial_jtag.h).

# Installation et premier test LCD ESP32

## Portée

Ce guide permet de compiler et de téléverser le test LCD situé dans `controleur-esp32/`.

Le programme affiche `LCD OK` et `ESP32-C6` sur fond bleu sombre, avec un rétroéclairage réglé à 50 %. Sans fichier de configuration Wi-Fi local, il n’initialise ni le Wi-Fi, ni la microSD, ni la LED RGB. Un [test Wi-Fi optionnel](test-wifi-esp32.md) est disponible; sa validation matérielle reste à effectuer. Les communications avec le Raspberry Pi restent à implémenter.

## Configuration de référence

- Carte : Waveshare ESP32-C6-LCD-1.47, non tactile.
- Puce identifiée sur l’exemplaire testé : ESP32-C6FH8, révision silicium v0.2.
- Mémoire flash détectée : 8 Mo.
- Révision du circuit imprimé : non relevée.
- Poste de compilation : HP EliteBook 840 G6, Ubuntu 26.04.1 LTS, x86-64.
- VS Code : 1.142.0, utilisé via Remote – SSH.
- Extension Espressif IDF distante : 2.3.0.
- Gestionnaire d’installation EIM : 0.20.1.
- ESP-IDF : 5.3.6.
- LVGL : 8.3.11, fourni dans les composants du projet.
- esptool : 4.12.0.

Cette configuration décrit le banc testé. D’autres postes sont possibles; leurs procédures doivent être validées séparément.

La fiche constructeur consultée décrit une variante de 4 Mo. L’exemplaire testé a été identifié par `esptool` comme un ESP32-C6FH8 de 8 Mo : vérifier la capacité réelle avant de réutiliser cette configuration.

## 1. Préparer Ubuntu

Installer Git, curl, unzip et les dépendances système :

```bash
sudo apt update
sudo apt install git curl unzip flex bison gperf ccache dfu-util libffi-dev libssl-dev
```

Installer VS Code et l’extension officielle **ESP-IDF**, publiée par **Espressif Systems**.

Pour travailler via Remote – SSH, installer l’extension ESP-IDF sur l’hôte Ubuntu distant. Brancher la carte sur cet hôte.

## 2. Vérifier l’USB et les permissions

Utiliser un câble USB de données, puis exécuter :

```bash
lsusb
ls -l /dev/serial/by-id/
```

L’exemplaire testé apparaît comme `303a:1001 Espressif USB JTAG/serial debug unit`, avec un port `/dev/ttyACM0`. Le numéro du port peut changer.

Donner à l’utilisateur l’accès série :

```bash
sudo usermod -a -G dialout "$USER"
```

Fermer puis rouvrir la session utilisateur. En SSH, se déconnecter puis établir une nouvelle connexion.

Vérifier les droits :

```bash
id -nG
test -r /dev/ttyACM0 && test -w /dev/ttyACM0 && echo "Accès série OK"
```

Le groupe `dialout` et le message `Accès série OK` doivent apparaître.

## 3. Installer ESP-IDF

Dans la palette de commandes VS Code, lancer :

```text
ESP-IDF: Open ESP-IDF Installation Manager
```

En SSH, l’assistant peut s’ouvrir dans le terminal.

Choisir :

- Cible : `esp32c6` uniquement.
- Version fixe : `v5.3.6`.
- Dépôt : GitHub officiel Espressif.
- Paquets Python : `https://pypi.org/simple`.
- Emplacement : `~/.espressif`.
- Fonctionnalités : cœur et prise en charge IDE.
- Outil supplémentaire : CMake.

Après installation, sélectionner v5.3.6 avec :

```text
ESP-IDF: Select Current ESP-IDF Version
```

Dans chaque nouveau terminal de compilation, activer l’environnement :

```bash
source "$HOME/.espressif/tools/activate_idf_v5.3.6.sh"
idf.py --version
```

Résultat attendu : `ESP-IDF v5.3.6`.

## 4. Identifier la mémoire flash

Fermer tout moniteur série, puis exécuter :

```bash
python -m esptool --chip esp32c6 --port /dev/ttyACM0 flash_id
```

La configuration du dépôt cible une mémoire de 8 Mo. Si la capacité détectée diffère, adapter **Serial flasher config → Flash size** avec `idf.py menuconfig` avant le téléversement.

## 5. Compiler

Depuis la racine du dépôt, sur la branche contenant le contrôleur :

```bash
git switch feature/controleur-esp32
cd controleur-esp32
idf.py build
```

La configuration initiale est fournie par `sdkconfig.defaults` : cible `esp32c6`, flash de 8 Mo.

Résultat attendu : `Project build complete`.

## 6. Téléverser et vérifier

Le téléversement remplace le programme présent sur la carte :

```bash
idf.py -p /dev/ttyACM0 flash monitor
```

Vérifier :

- La vérification d’intégrité du téléversement réussit.
- L’écran affiche `LCD OK` et `ESP32-C6`.
- Le terminal affiche `Test LCD actif, luminosite 50 %`.
- L’affichage reste stable au moins 30 secondes.

Le programme ne produit pas de messages périodiques. Le silence du terminal après l’initialisation est normal.

Quitter le moniteur avec **Ctrl + ]**, ou **Ctrl + T**, puis **X**.

Débrancher puis rebrancher la carte sans appuyer sur BOOT. L’affichage doit revenir et rester stable au moins 30 secondes.

## 7. Dépannage

- **`python` introuvable** : activer l’environnement ESP-IDF dans le terminal courant.
- **Permission refusée sur le port série** : vérifier `dialout` et renouveler la session.
- **`waiting for download`** : relâcher BOOT et appuyer brièvement sur RESET.
- **`host_id not initialized`** : vérifier que `LCD_Init()` initialise le bus SPI avant `esp_lcd_new_panel_io_spi()`.
- **Déconnexion du moniteur** : fermer les autres accès série, quitter le moniteur puis le relancer avec `idf.py -p /dev/ttyACM0 monitor`. Une déconnexion du moniteur ne prouve pas, à elle seule, un plantage du programme.

## Provenance du test

Le programme dérive de l’exemple Waveshare `ESP32-C6-LCD-1.47-Test`.

Adaptations : initialisation autonome du bus SPI, rétroéclairage limité à 50 %, interface textuelle minimale et retrait des sources applicatives Wi-Fi, SD et RGB de la compilation.

Archive constructeur : [ESP32-C6-LCD-1.47-Demo.zip](https://files.waveshare.com/wiki/ESP32-C6-LCD-1.47/ESP32-C6-LCD-1.47-Demo.zip).

Empreinte SHA-256 de l’archive utilisée :

```text
4b960e8ccd58e54e60494a2a6da62531695c9152c9950153cad34acc496c4ee4
```

Conserver les mentions de licence des sources et des composants tiers.

Références : [carte Waveshare](https://docs.waveshare.com/ESP32-C6-LCD-1.47) et [exemples ESP-IDF](https://docs.waveshare.com/ESP32-C6-LCD-1.47/ESP-IDF).
# Test Wi-Fi dedie Raspberry Pi / ESP32

**Statut : connexion Wi-Fi, ping et reconnexion automatique sans RESET valides sur le banc; nouvelle signalisation couleur a compiler et valider sur le materiel.**

Ce test ajoute uniquement la connexion Wi-Fi et son etat sur le LCD. Il n'implemente pas le service de decision, l'authentification applicative ou une commande de porte.

## Signalisation sur le LCD

- **Fond vert, texte blanc** : connexion Wi-Fi et configuration IP acquises.
- **Fond orange, texte sombre** : connexion en cours, Wi-Fi deconnecte ou configuration locale invalide. La boucle d'affichage reste active et les reconnexions se poursuivent lorsque la configuration est valide.
- **Fond bleu sombre** : test LCD seul, sans fichier de configuration Wi-Fi local.

Le texte precise l'etat en complement de la couleur. Le vert ne garantit pas que le service applicatif du Raspberry Pi est disponible; l'orange ne signifie pas qu'un controle d'acces autonome fonctionne. Aucun mode de decision hors ligne n'est implemente.

## Configuration

- Raspberry Pi 4 sous Debian 13 (trixie), avec NetworkManager actif.
- Ethernet pour l'administration et la synchronisation existantes.
- `wlan0` en point d'acces 2,4 GHz, SSID masque `ControleAcces-Labo`.
- WPA2-Personal, mot de passe choisi localement.
- Pi : `192.168.81.1/24`.
- ESP32 : `192.168.81.2/24`, ESP-IDF 5.3.6.
- Pas de DHCP dans ce profil; adresse fixe cote ESP32.

Verifier que ce sous-reseau ne chevauche pas les autres routes du banc. Le SSID masque ne constitue pas une protection contre la detection du reseau. Ce profil ne configure pas de partage Internet; il ne remplace pas une politique de filtrage sur un Pi qui utilise deja Docker ou du routage.

## Preparer le point d'acces sur le Pi

Verifier que NetworkManager est actif et que la radio prend en charge le mode AP :

```bash
systemctl is-active NetworkManager
ip -brief address
iw list
```

Creer le profil une seule fois :

```bash
sudo nmcli connection add \
  type wifi ifname wlan0 con-name controle-acces-ap \
  ssid ControleAcces-Labo \
  802-11-wireless.mode ap \
  802-11-wireless.band bg \
  802-11-wireless.hidden yes \
  802-11-wireless-security.key-mgmt wpa-psk \
  802-11-wireless-security.proto rsn \
  ipv4.method manual \
  ipv4.addresses 192.168.81.1/24 \
  ipv4.never-default yes \
  ipv6.method disabled \
  connection.autoconnect no
sudo nmcli --ask connection up controle-acces-ap
```

Saisir le mot de passe uniquement sur le Pi; ne pas le publier dans un journal ou une capture. Pour le banc, choisir 16 a 63 caracteres ASCII.

Verifier :

```bash
ip -brief address
nmcli -f GENERAL.STATE,GENERAL.CONNECTION device show wlan0
```

Attendre `wlan0 UP 192.168.81.1/24` et la connexion `controle-acces-ap` active. Ethernet doit rester actif. Le demarrage automatique reste desactive pendant les essais; apres redemarrage du Pi, reactiver le profil manuellement.

## Configurer l'ESP32 sur l'hote de compilation

Depuis `controleur-esp32/` :

```bash
cp -n main/configuration-wifi.exemple.h main/configuration-wifi.locale.h
chmod 600 main/configuration-wifi.locale.h
git check-ignore main/configuration-wifi.locale.h
```

Ouvrir le fichier local dans l'editeur et remplacer `REMPLACER_LOCALEMENT` par le mot de passe du point d'acces. Les valeurs sont des chaines C : echapper les guillemets et antislashs si necessaire. Ne pas transmettre ce fichier.

Le fichier local est exclu de Git. Les identifiants sont neanmoins inclus dans le binaire compile : ne pas publier les binaires de ce test. Le programme ne les affiche pas et utilise le stockage Wi-Fi en RAM plutot qu'une sauvegarde de configuration Wi-Fi en NVS.

Sans fichier local, le programme conserve le test LCD seul. Apres ajout, modification ou retrait du fichier local, reconfigurer explicitement avant de compiler :

```bash
source "$HOME/.espressif/tools/activate_idf_v5.3.6.sh"
idf.py reconfigure
idf.py build
```

Apres compilation reussie :

```bash
idf.py -p /dev/ttyACM0 flash monitor
```

## Validation a effectuer

1. Le LCD affiche `LCD OK`, `Wi-Fi connecte` et `192.168.81.2`, sur fond vert.
2. Le terminal indique `RESEAU: Wi-Fi connecte, IP=192.168.81.2`.
3. Depuis le Pi, verifier l'association et la liaison IP :

```bash
iw dev wlan0 station dump
ping -c 4 192.168.81.2
```

4. Debrancher et rebrancher l'ESP32; verifier la reconnexion et la stabilite du LCD.
5. Depuis la session SSH Ethernet du Pi, couper le point d'acces :

```bash
sudo nmcli connection down controle-acces-ap
```

Attendre la detection de la coupure sur le LCD, puis laisser le reseau arrete au moins une minute. Le LCD doit passer a l'orange et afficher `Wi-Fi deconnecte / Nouvel essai: 5 s` ou `Wi-Fi connexion...`. Le moniteur doit continuer d'annoncer de nouvelles tentatives, sans demande de RESET.

6. Reactiver le point d'acces sur le Pi :

```bash
sudo nmcli --ask connection up controle-acces-ap
```

Attendre la confirmation d'activation. Sans appuyer sur RESET ni debrancher l'ESP32, attendre le retour du fond vert et de `Wi-Fi connecte / 192.168.81.2`, puis lancer sur le Pi :

```bash
ping -c 4 192.168.81.2
vcgencmd get_throttled
```

Le ping doit repondre et le LCD doit rester stable. La session SSH Ethernet ne doit pas etre interrompue.

## Fonctionnement de la reconnexion

La premiere connexion est immediate. Chaque echec ou deconnexion detectee programme une nouvelle tentative apres cinq secondes, sans limite de nombre. Le temps de recherche et d'authentification Wi-Fi s'ajoute a ce delai; il ne s'agit pas d'une garantie de retablissement en cinq secondes.

La minuterie ne bloque pas la boucle d'affichage. Elle transmet un evenement a la boucle reseau, qui evite les connexions simultanees et annule les essais a l'association au point d'acces. L'etat `connecte` est affiche apres l'evenement IP. Une erreur immediate de l'API de connexion est egalement reessayee.

Les erreurs d'initialisation et une configuration locale invalide restent des erreurs a corriger; elles ne sont pas masquees par la reconnexion. Un mauvais mot de passe de format valide entrainera des tentatives repetees.

## Alimentation et diagnostic du Pi

Utiliser une alimentation adaptee au Pi 4 et verifier l'absence de sous-tension avant les essais prolonges :

```bash
vcgencmd get_throttled
sudo journalctl -k -b --no-pager | grep -Ei 'under.?voltage|voltage normal'
```

Le banc a retrouve `throttled=0x0` apres remplacement de son alimentation USB de routeur. Les alertes de sous-tension constatees auparavant ne suffisent pas a prouver la cause des redemarrages, faute de journaux persistants.

Le point d'acces ne demarre pas automatiquement apres un redemarrage du Pi dans cette configuration : verifier son activation avant de diagnostiquer l'ESP32.

Une adresse IP affichee ne prouve pas a elle seule que le Pi repond : valider aussi le ping. Aucun echange de decision d'acces n'est realise.

Pour arreter le point d'acces sans modifier Ethernet :

```bash
sudo nmcli connection down controle-acces-ap
```

References : [NetworkManager](https://networkmanager.pages.freedesktop.org/NetworkManager/NetworkManager/nm-settings-nmcli.html), [ESP-IDF ESP-NETIF](https://docs.espressif.com/projects/esp-idf/en/v5.3.6/esp32c6/api-reference/network/esp_netif.html).

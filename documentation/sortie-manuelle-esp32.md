# Simuler une demande de sortie interieure avec BOOT

**Statut : implementation preparee et logique testee avec entrees simulees; compilation ESP-IDF et bouton physique a valider sur la carte.**

## Fonctionnement

Un appui sur BOOT simule le bouton de deverrouillage manuel situe a l'interieur. Le LCD affiche `SORTIE AUTORISEE / DEVERROUILLAGE / SIMULE` pendant cinq secondes, puis revient a `PRET / BOOT: sortie`.

Il s'agit d'un etat logiciel et d'un affichage : aucun relais, aucune serrure ni sortie de puissance ne sont commandes. Aucun message applicatif n'est encore envoye au Raspberry Pi. Cette action interieure simulee est distincte d'une demande d'entree par badge, dont l'autorisation doit etre decidee par le Pi.

## Entree et temporisation

- BOOT est lu sur GPIO9, actif au niveau bas, avec resistance de rappel interne.
- Anti-rebond : 40 ms de niveau stable.
- Lecture non bloquante dans la boucle principale, environ toutes les 10 ms.
- Un appui maintenu ne declenche qu'une demande.
- Il faut relacher le bouton de facon stable avant un nouvel appui.
- Un nouvel appui distinct pendant la simulation prolonge la duree a cinq secondes depuis cet appui.
- Si le bouton est deja maintenu au lancement du programme, il faut le relacher avant de pouvoir declencher une demande.

Le bouton BOOT participe au mode de demarrage. Ne pas le maintenir pendant RESET ou une remise sous tension : cela peut placer la carte en mode televersement. RESET n'est pas une commande de sortie.

Reference : [schema Waveshare](https://files.waveshare.com/wiki/ESP32-C6-LCD-1.47/ESP32-C6-LCD-1.47_schemetics.pdf).

## Couleurs de l'interface

| Couleur | Sens |
| --- | --- |
| Bleu sombre | Repos ou premiere connexion en cours; aucune decision d'acces affichee |
| Vert | Sortie manuelle autorisee dans la simulation, pendant cinq secondes |
| Orange | Erreur, notamment perte Wi-Fi ou configuration locale invalide |
| Rouge | Reserve a un refus d'acces effectif; ce comportement n'est pas encore implemente |

L'etat Wi-Fi reste affiche en texte et ne suffit plus a rendre l'ecran vert. Une erreur reste prioritaire sur la couleur verte : le texte indique toujours si la simulation de sortie est active. La reconnexion n'efface pas la temporisation de sortie.

La simulation locale de sortie reste utilisable pendant une coupure reseau. Cela ne constitue pas un moteur d'autorisation hors ligne pour des badges.

## Compiler et televerser sur l'EliteBook

Depuis la racine du depot, sur `feature/controleur-esp32` :

```bash
git pull --ff-only origin feature/controleur-esp32
cd controleur-esp32
source "$HOME/.espressif/tools/activate_idf_v5.3.6.sh"
idf.py build
```

Apres compilation reussie :

```bash
idf.py -p /dev/ttyACM0 flash monitor
```

La configuration Wi-Fi locale existante est conservee et reste exclue de Git.

## Validation materielle

1. Avec le point d'acces actif, attendre `PRET` et `Wi-Fi connecte` sur fond neutre.
2. Appuyer brievement sur BOOT : verifier le fond vert et le message de sortie autorisee simulee.
3. Attendre cinq secondes : verifier le retour au repos sans redemarrage.
4. Maintenir BOOT plus de cinq secondes : la simulation doit expirer sans se declencher de nouveau. Relacher, puis appuyer pour produire une nouvelle demande.
5. Faire deux appuis distincts : la duree doit repartir du dernier appui valide.
6. Couper le point d'acces depuis la session Ethernet du Pi : verifier l'orange apres detection de la perte Wi-Fi. Appuyer sur BOOT : le texte doit indiquer la simulation, tout en conservant l'orange d'erreur.
7. Reactiver le point d'acces : verifier la reconnexion sans RESET et la mise a jour de l'affichage.

Le moniteur indique `SORTIE: Demande interieure: deverrouillage SIMULE pendant 5 secondes`, puis `SORTIE: Fin du deverrouillage SIMULE`. Un appui maintenu ne doit pas produire de demandes repetees.

Les essais avec entrees simulees couvrent les rebonds, l'appui maintenu, l'expiration, la prolongation et le bouton maintenu au lancement. Ils ne remplacent pas la validation du bouton physique.

## Journal réseau optionnel

Sur la branche `feature/journal-evenements-securise`, suivre le [guide du journal ESP32](journal-esp32.md) pour transmettre chaque nouvel appui par mTLS. Le programme conserve la simulation locale et ajoute une file RAM bornée; la fin des cinq secondes ne génère pas un nouvel événement. L'activation requiert les fichiers privés de configuration et de certificats. Sans activation, la simulation locale reste disponible.

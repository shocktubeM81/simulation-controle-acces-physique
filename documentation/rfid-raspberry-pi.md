# MFRC522 et NTAG215 sur Raspberry Pi 4

Branche : `feature/rfid-mfrc522-raspberry-pi`. Lecture seule, sans DEL ni actionneur.
Le mode UID ne demande aucune décision d'accès. Le mode porte utilise exclusivement
le cache synchronisé et refuse une erreur ou une réponse ambiguë du moteur.
Un UID seul est un identifiant copiable, pas une authentification cryptographique.

## Câblage de référence

Couper l'alimentation avant toute modification. Alimentation et logique en 3,3 V.

| RC522 | Broche physique Pi | Fonction |
|---|---|---|
| 3.3V | 1 | 3,3 V |
| GND | 6 | Masse |
| SDA/SS | 24 | GPIO8 / CE0 |
| SCK | 23 | GPIO11 |
| MOSI | 19 | GPIO10 |
| MISO | 21 | GPIO9 |
| RST | 22 | GPIO25 |
| IRQ | Non raccordée | |

## Préparation

Sur le Pi, depuis le dépôt, après avoir vérifié `git status` et conservé tout travail local :

```bash
git fetch origin
git switch feature/rfid-mfrc522-raspberry-pi
git pull --ff-only
sudo raspi-config nonint do_spi 0
# Redémarrer si SPI vient d'être activé.
ls -l /dev/spidev0.0
id
sudo apt install -y python3-venv python3-dev build-essential
python3 -m venv ~/rfid-test/.venv
~/rfid-test/.venv/bin/python -m pip install -r requirements-rfid.txt
```

L'utilisateur doit appartenir aux groupes `spi` et `gpio` (déjà confirmé sur le banc).
Ne pas lancer Python avec sudo. Les dépendances directes sont épinglées;
consigner aussi la version de Python, du noyau et `pip freeze` pour reproduire un essai.

## Essai de lecture

```bash
~/rfid-test/.venv/bin/python serveur-local/lecteur-rfid.py --une-lecture
```

Tester séparément le badge à quatre octets et le NTAG215 à sept octets.
Le format est hexadécimal majuscule séparé par `:`, sans BCC ni marqueur de cascade.
Le programme contrôle BCC, sélection et CRC du SAK à chaque niveau.
Un seul jeton doit être présenté. Les UID de dix octets et NDEF ne sont pas pris en charge.
Sans `--une-lecture`, retirer le jeton au moins deux secondes avant de le représenter.

## Décision locale

L'installation habituelle du Pi et une synchronisation valide doivent déjà fonctionner.
Construire l'image si nécessaire :

```bash
docker compose -f compose.local.yaml build cache-sqlite
~/rfid-test/.venv/bin/python serveur-local/lecteur-rfid.py --porte 'Laboratoire' --une-lecture
```

Cette commande utilise les droits Docker du compte courant, comme les outils existants.
Elle n'inscrit aucun badge, ne crée aucune autorisation, ne modifie pas le cache et
n'ajoute pas d'événement au journal. Un jeton inconnu doit produire `REFUSE`.
Pour un essai positif, faire enregistrer l'UID complet comme `identifiants.code`
dans les données locales du laboratoire côté central, avec une personne active et
une autorisation valide pour le nom exact de la porte; synchroniser ensuite le Pi.
Ne pas remplacer les identifiants fictifs du dépôt par les UID physiques.
Sans cet enregistrement, la lecture peut être confirmée tout en étant refusée.

## Validation

```bash
python3 -m unittest discover -s serveur-local/tests -p 'test_lecteur_rfid.py' -v
```

Tests simulés : cascade quatre/sept octets, BCC/CRC invalides, format canonique,
refus sur panne, délai et sortie ambiguë. Ils ne remplacent pas l'essai matériel.
Le badge quatre octets et SPI ont été validés avant cette intégration; la nouvelle
lecture en cascade et la décision avec un jeton physique restent à valider sur le Pi.
Ne publier ni secrets, ni UID physiques, ni captures les contenant.

Références : [MFRC522 NXP](https://www.nxp.com/docs/en/data-sheet/MFRC522.pdf),
[bibliothèque utilisée](https://github.com/pimylifeup/MFRC522-python).

# Console du banc d'essai

Depuis le dépôt sur le Pi, sur la branche RFID :

```bash
git pull --ff-only
sudo -v
~/rfid-test/.venv/bin/python serveur-local/console-acces.py --porte 'Laboratoire' --docker-sudo
```

Le programme démarre à la demande dans le terminal, sans installer de service.
Ne pas lancer simultanément un autre programme utilisant le RC522.
Les dépendances de `requirements-rfid.txt` doivent être installées.

Un état `En attente | RFID : prêt | Bouton : prêt` reste sur la dernière ligne.
Il n'y a ni animation ni nouvelle ligne pendant l'attente. Les événements restent
au-dessus avec l'heure locale : scan en cours, décision d'autorisation ou de refus,
et sortie manuelle simulée reçue de l'ESP32. Ctrl+C termine la console et libère le lecteur;
un appel Docker en cours peut retarder l'arrêt de quelques secondes.
Sans terminal interactif, seules les transitions et événements sont écrits.

La console réutilise la sélection RFID 4/7 octets et le moteur du cache synchronisé.
Un badge maintenu n'ajoute pas des scans en boucle; le retirer au moins 0,8 seconde
avant de le représenter. Un badge différent peut être présenté immédiatement.
RFID et journal sont suivis indépendamment : l'attente de la décision Docker
ne bloque pas l'affichage d'un événement BOOT reçu.

## Bouton BOOT de l'ESP32

Le suivi lit SQLite depuis le service `journal-https` déjà en fonctionnement,
avec `docker compose exec` et une connexion SQLite en lecture seule, environ
une fois par seconde. Aucune nouvelle route réseau, aucun accès aux clés privées.
Il faut que le service et le transport mTLS de l'ESP32 soient opérationnels.
La console ne les démarre ni ne les reconfigure.

Les anciens événements sont ignorés à la première connexion réussie. Ensuite,
le curseur suit les numéros dans l'ordre, par lots de 100, sans réafficher les doublons.
Après une panne du journal, les événements conservés depuis ce curseur sont affichés
à la reprise. Si la première connexion échoue, le suivi ne commence qu'à la première
connexion réussie. Une suppression/remise à zéro de la base nécessite une relance.
Seuls `SORTIE_MANUELLE_SIMULEE` d'origine `MTLS` sont affichés comme appuis BOOT;
les essais `TEST_LOCAL` ne sont pas présentés comme appuis physiques.
L'identifiant de porte du journal (ex. `PORTE_TEST`) est affiché tel quel;
il n'est pas assimilé au nom `Laboratoire` du cache.

Une réception confirme l'enregistrement dans le journal; elle ne prouve pas
l'ouverture physique d'une porte. Un événement retardé par la file de l'ESP32
apparaît à réception. Tous les contrôleurs/portes du journal sont suivis.

Si le journal devient indisponible, l'état Bouton passe en erreur, puis revient
à prêt à la reprise. Le lecteur RFID reste utilisable. Une erreur d'initialisation
du RFID est affichée et nécessite de corriger la cause puis relancer la console.
Si sudo réclame un mot de passe, arrêter et relancer après `sudo -v` dans le même
terminal. Aucun mot de passe n'est lu par Python; Python reste sans sudo.

## Essai sur le banc

1. Vérifier que les états deviennent prêts et que l'attente ne défile pas.
2. Présenter le NTAG215 autorisé : une décision `AUTORISE` est attendue.
3. Maintenir le jeton : pas de nouveau scan; retirer puis représenter.
4. Présenter un badge non enregistré : `REFUSE`.
5. Appuyer sur BOOT : une sortie manuelle simulée doit apparaître après réception.
6. Vérifier que l'historique reste visible et que Ctrl+C arrête le programme.

Les UID ne sont affichés que dans le terminal, sans nouveau stockage par la console.
Ne pas publier de capture contenant les UID physiques. Les événements RFID ne sont
pas ajoutés au journal SQLite, qui reste réservé aux sorties simulées.

Tests locaux sans matériel :

```bash
python3 -m unittest discover -s serveur-local/tests -p 'test_*rfid.py' -v
python3 -m unittest discover -s serveur-local/tests -p 'test_console_acces.py' -v
```

La console reste à valider sur le Pi et avec le bouton; les tests simulés ne
constituent pas une validation du transport ni du matériel.

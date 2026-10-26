#!/usr/bin/env python3
"""Console locale : lecteur RFID et événements BOOT reçus par le journal mTLS."""
import argparse
from datetime import datetime
import importlib.util
import json
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time

RACINE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('lecteur_rfid', Path(__file__).with_name('lecteur-rfid.py'))
rfid = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rfid)

# Exécuté dans le conteneur déjà actif, volume du journal accessible en lecture seule.
LECTURE_JOURNAL = '''
import json, sqlite3, sys
with sqlite3.connect('file:/donnees/journal-evenements.sqlite3?mode=ro', uri=True, timeout=2) as db:
    db.row_factory = sqlite3.Row
    if sys.argv[1] == 'initialiser':
        resultat = {'curseur': db.execute('SELECT COALESCE(MAX(numero), 0) FROM evenements').fetchone()[0], 'evenements': []}
    else:
        lignes = db.execute('SELECT numero, controleur, porte, type, origine, recu_a_utc FROM evenements WHERE numero > ? ORDER BY numero LIMIT 100', (int(sys.argv[1]),)).fetchall()
        resultat = {'curseur': lignes[-1]['numero'] if lignes else int(sys.argv[1]), 'evenements': [dict(ligne) for ligne in lignes]}
    print(json.dumps(resultat))
'''


def commande_docker(sudo):
    return (['sudo', '-n'] if sudo else []) + ['docker', 'compose', '-f', str(RACINE / 'compose.local.yaml')]


def lire_journal(curseur, sudo):
    commande = commande_docker(sudo) + ['exec', '-T', 'journal-https', 'python3', '-c',
                                       LECTURE_JOURNAL, 'initialiser' if curseur is None else str(curseur)]
    resultat = subprocess.run(commande, cwd=RACINE, capture_output=True, text=True, timeout=8)
    if resultat.returncode:
        raise RuntimeError('Journal indisponible : vérifier journal-https et les droits Docker/sudo')
    donnees = json.loads(resultat.stdout)
    return donnees['curseur'], donnees['evenements']


class Presence:
    """Une seule entrée par présentation; retrait d'au moins 0,8 seconde pour réarmer."""
    def __init__(self):
        self.uid = None
        self.dernier = 0

    def nouveau(self, uid, maintenant):
        if uid is None:
            return False
        nouveau = uid != self.uid or maintenant - self.dernier >= 0.8
        self.uid, self.dernier = uid, maintenant
        return nouveau


def suivre_rfid(args, messages, arret):
    lecteur = None
    try:
        import RPi.GPIO as GPIO
        from mfrc522 import MFRC522
        lecteur = MFRC522(bus=0, device=0, pin_mode=GPIO.BOARD, pin_rst=22)
        messages.put(('etat', 'RFID', 'prêt'))
        presence = Presence()
        erreur_precedente = None
        while not arret.is_set():
            try:
                uid = rfid.lire_uid(lecteur)
                if erreur_precedente:
                    messages.put(('etat', 'RFID', 'prêt'))
                erreur_precedente = None
            except ValueError as erreur:
                if str(erreur) != erreur_precedente:
                    messages.put(('etat', 'RFID', f'lecture rejetée : {erreur}'))
                erreur_precedente = str(erreur)
                uid = None
            if presence.nouveau(uid, time.monotonic()):
                messages.put(('evenement', f'CARTE | {uid} | vérification…'))
                decision = rfid.verifier_acces(uid, args.porte, RACINE, args.docker_sudo)
                messages.put(('evenement', f'CARTE | {uid} | {args.porte} | {decision}'))
                # Le délai Docker ne doit pas réarmer un badge resté sur le lecteur.
                presence.dernier = time.monotonic()
            arret.wait(0.1)
    except Exception as erreur:
        messages.put(('etat', 'RFID', f'indisponible ({type(erreur).__name__}) — relancer la console'))
    finally:
        if lecteur is not None:
            lecteur.spi.close()
            GPIO.cleanup(22)


def suivre_journal(args, messages, arret):
    curseur, etat = None, None
    while not arret.is_set():
        try:
            curseur, lignes = lire_journal(curseur, args.docker_sudo)
            nouveau = 'prêt'
            for ligne in lignes:
                if ligne['origine'] == 'MTLS' and ligne['type'] == 'SORTIE_MANUELLE_SIMULEE':
                    messages.put(('evenement', f"BOUTON | sortie manuelle simulée reçue | {ligne['porte']} | {ligne['controleur']} | réception {ligne['recu_a_utc']}"))
        except (OSError, subprocess.TimeoutExpired, RuntimeError, ValueError, KeyError, TypeError):
            nouveau = 'indisponible — vérifier journal-https / sudo'
        if nouveau != etat:
            messages.put(('etat', 'Bouton', nouveau))
            etat = nouveau
        arret.wait(1)


def nettoyer(texte):
    # Une valeur reçue ne peut pas injecter une séquence de contrôle du terminal.
    return ''.join(c if c.isprintable() else '?' for c in str(texte))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--porte', required=True, help='Nom exact dans le cache, ex. Laboratoire')
    parser.add_argument('--docker-sudo', action='store_true')
    args = parser.parse_args()
    arret, messages = threading.Event(), queue.Queue()
    etats = {'RFID': 'initialisation', 'Bouton': 'initialisation'}
    print('CONSOLE CONTRÔLE D’ACCÈS — Ctrl+C pour arrêter')
    print('Le bouton affiche les sorties simulées reçues par le journal mTLS.')
    travailleurs = []
    for cible in (suivre_rfid, suivre_journal):
        travailleur = threading.Thread(target=cible, args=(args, messages, arret), daemon=True)
        travailleur.start()
        travailleurs.append(travailleur)
    interactif = sys.stdout.isatty()
    try:
        while True:
            if interactif:
                print('\r\033[2K' + 'En attente | ' + ' | '.join(f'{k} : {v}' for k, v in etats.items()), end='', flush=True)
            message = messages.get()
            if interactif:
                print('\r\033[2K', end='')
            if message[0] == 'etat':
                etats[message[1]] = nettoyer(message[2])
                texte = f'{message[1]} : {message[2]}'
            else:
                texte = message[1]
            print(f'[{datetime.now().astimezone():%H:%M:%S}] {nettoyer(texte)}', flush=True)
    except KeyboardInterrupt:
        arret.set()
        if interactif:
            print('\r\033[2K', end='')
        print('Arrêt en cours…', flush=True)
        for travailleur in travailleurs:
            travailleur.join(timeout=35)
        print('Console arrêtée.')


if __name__ == '__main__':
    main()

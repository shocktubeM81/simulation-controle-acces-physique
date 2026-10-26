#!/usr/bin/env python3
"""Récepteur USB local du banc, sans réseau ni authentification mTLS."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid

DECISIONS = {'AUTORISE', 'REFUSE', 'ERREUR'}


def programmer_affichage(base, decision):
    if decision not in DECISIONS:
        raise ValueError('Décision d’affichage invalide')
    destination = Path(base).with_name('affichage-usb.json')
    temporaire = destination.with_name(f'.affichage-{uuid.uuid4()}.tmp')
    try:
        with temporaire.open('x', encoding='utf-8') as fichier:
            json.dump({'id': str(uuid.uuid4()), 'decision': decision, 'instant': time.time()}, fichier)
        temporaire.replace(destination)
    finally:
        temporaire.unlink(missing_ok=True)


def prochain_affichage(base, precedent):
    try:
        donnees = json.loads(Path(base).with_name('affichage-usb.json').read_text(encoding='utf-8'))
        if (donnees['id'] == precedent or donnees['decision'] not in DECISIONS
                or not 0 <= time.time() - donnees['instant'] <= 5):
            return precedent, None
        return donnees['id'], ('AFF ' + donnees['decision'] + '\n').encode('ascii')
    except (OSError, ValueError, KeyError, TypeError):
        return precedent, None

spec = importlib.util.spec_from_file_location('validation_journal', Path(__file__).with_name('journal-evenements.py'))
validation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validation)


def ouvrir(base):
    db = sqlite3.connect(base, timeout=3)
    db.execute('PRAGMA synchronous=FULL')
    return db


def initialiser(base):
    db = ouvrir(base)
    try:
        version = db.execute('PRAGMA user_version').fetchone()[0]
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        if version == 0 and not tables:
            with db:
                db.execute('''CREATE TABLE evenements (
                    numero INTEGER PRIMARY KEY, controleur TEXT NOT NULL,
                    id_evenement TEXT NOT NULL UNIQUE, version INTEGER NOT NULL CHECK(version=1),
                    porte TEXT NOT NULL, type TEXT NOT NULL CHECK(type='SORTIE_MANUELLE_SIMULEE'),
                    origine TEXT NOT NULL CHECK(origine='USB'), recu_a_utc TEXT NOT NULL
                ) STRICT''')
                db.execute('CREATE TABLE etat (id INTEGER PRIMARY KEY CHECK(id=1), connecte INTEGER NOT NULL, instant REAL NOT NULL) STRICT')
                db.execute('PRAGMA user_version=1')
        elif version != 1 or tables != {'evenements', 'etat'}:
            raise ValueError('Base USB incompatible')
    finally:
        db.close()


def etat_port(base, connecte):
    db = ouvrir(base)
    try:
        with db:
            db.execute('INSERT INTO etat VALUES (1, ?, ?) ON CONFLICT(id) DO UPDATE SET connecte=excluded.connecte, instant=excluded.instant', (int(connecte), time.time()))
    finally:
        db.close()


def enregistrer(base, contenu, porte):
    evenement = validation.valider(contenu)
    if evenement['porte'] != porte:
        raise ValueError('Porte USB non configurée')
    db = ouvrir(base)
    try:
        with db:
            # Sérialiser recherche et insertion; ACK seulement après sortie du bloc COMMIT.
            db.execute('BEGIN IMMEDIATE')
            precedent = db.execute('SELECT version, porte, type FROM evenements WHERE id_evenement=?', (evenement['id_evenement'],)).fetchone()
            if precedent is not None:
                if precedent != (evenement['version'], evenement['porte'], evenement['type']):
                    raise ValueError('UUID déjà utilisé pour un autre contenu')
            else:
                instant = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
                db.execute('INSERT INTO evenements (controleur,id_evenement,version,porte,type,origine,recu_a_utc) VALUES (?,?,?,?,?,?,?)',
                           ('ESP32-USB', evenement['id_evenement'], 1, porte, evenement['type'], 'USB', instant))
        return ('ACK ' + evenement['id_evenement'] + '\n').encode('ascii')
    finally:
        db.close()


class Trames:
    def __init__(self):
        self.tampon = bytearray()
        self.debordement = False

    def recevoir(self, morceau):
        for octet in morceau:
            if octet == 10:
                if not self.debordement and self.tampon.startswith(b'EVT '):
                    yield bytes(self.tampon[4:])
                self.tampon.clear()
                self.debordement = False
            elif not self.debordement:
                if len(self.tampon) >= 1028:
                    self.tampon.clear()
                    self.debordement = True
                else:
                    self.tampon.append(octet)


def main():
    import serial
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', default='/dev/esp32')
    parser.add_argument('--base', default='/donnees/journal-usb.sqlite3')
    parser.add_argument('--porte', default='PORTE-01')
    parser.add_argument('--afficher', choices=sorted(DECISIONS),
                        help='Demander un affichage temporaire au récepteur USB actif')
    args = parser.parse_args()
    os.umask(0o077)
    if args.afficher:
        programmer_affichage(args.base, args.afficher)
        return
    if validation.IDENTIFIANT.fullmatch(args.porte) is None:
        parser.error('Identifiant de porte invalide')
    os.umask(0o077)
    initialiser(args.base)
    etat_port(args.base, False)
    try:
        while True:
            try:
                connexion = serial.Serial(port=None, baudrate=115200, timeout=0.2,
                                          write_timeout=2, exclusive=True)
                # Éviter la séquence DTR/RTS utilisée pour entrer dans le chargeur.
                connexion.dtr = False
                connexion.rts = False
                connexion.port = args.port
                connexion.open()
                with connexion as port:
                    print('USB : port ouvert', flush=True)
                    trames, dernier_etat, dernier_affichage = Trames(), 0, None
                    while True:
                        for contenu in trames.recevoir(port.read(128)):
                            try:
                                ack = enregistrer(args.base, contenu, args.porte)
                            except (ValueError, sqlite3.Error, OSError):
                                print('USB : événement rejeté ou stockage indisponible', flush=True)
                                continue
                            if port.write(ack) != len(ack):
                                raise serial.SerialException('ACK incomplet')
                            port.flush()
                        identifiant, affichage = prochain_affichage(args.base, dernier_affichage)
                        if affichage is not None:
                            if port.write(affichage) != len(affichage):
                                raise serial.SerialException('Affichage incomplet')
                            port.flush()
                            dernier_affichage = identifiant
                        if time.monotonic() - dernier_etat >= 1:
                            etat_port(args.base, True)
                            dernier_etat = time.monotonic()
            except (serial.SerialException, OSError):
                etat_port(args.base, False)
                print('USB : port indisponible, nouvel essai dans 2 secondes', flush=True)
                time.sleep(2)
    except KeyboardInterrupt:
        etat_port(args.base, False)


if __name__ == '__main__':
    main()

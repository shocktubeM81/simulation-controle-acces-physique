import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import uuid

spec = importlib.util.spec_from_file_location('journal_usb', Path(__file__).parents[1] / 'journal-usb.py')
usb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(usb)


def evenement(identifiant=None, porte='PORTE-01'):
    return json.dumps({'version': 1, 'id_evenement': identifiant or str(uuid.uuid4()),
                       'porte': porte, 'type': 'SORTIE_MANUELLE_SIMULEE'}).encode()


class TestsUSB(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.base = Path(self.dossier.name) / 'usb.sqlite3'
        usb.initialiser(self.base)

    def tearDown(self):
        self.dossier.cleanup()

    def test_ack_apres_commit_et_doublon(self):
        contenu = evenement()
        ack = usb.enregistrer(self.base, contenu, 'PORTE-01')
        self.assertEqual(ack, ('ACK ' + json.loads(contenu)['id_evenement'] + '\n').encode())
        self.assertEqual(usb.enregistrer(self.base, contenu, 'PORTE-01'), ack)
        db = sqlite3.connect(self.base)
        try:
            self.assertEqual(db.execute('SELECT origine,COUNT(*) FROM evenements').fetchone(), ('USB', 1))
        finally:
            db.close()

    def test_uuid_conflit(self):
        identifiant = str(uuid.uuid4())
        usb.enregistrer(self.base, evenement(identifiant), 'PORTE-01')
        with self.assertRaises(ValueError):
            usb.enregistrer(self.base, evenement(identifiant, 'PORTE-02'), 'PORTE-02')

    def test_aucun_ack_sur_stockage_en_panne(self):
        with patch.object(usb, 'ouvrir', side_effect=sqlite3.OperationalError()):
            with self.assertRaises(sqlite3.Error):
                usb.enregistrer(self.base, evenement(), 'PORTE-01')

    def test_porte_inconnue_et_json_invalide(self):
        for contenu in (evenement(porte='PORTE-02'), b'{}', b'{bad', b'x' * 1025):
            with self.assertRaises(ValueError):
                usb.enregistrer(self.base, contenu, 'PORTE-01')

    def test_trames_fragmentees_et_bruit(self):
        trames = usb.Trames()
        self.assertEqual(list(trames.recevoir(b'log\nEV')), [])
        self.assertEqual(list(trames.recevoir(b'T {}\nEVT {')), [b'{}'])
        self.assertEqual(list(trames.recevoir(b'}\n')), [b'{}'])

    def test_debordement_et_resynchronisation(self):
        trames = usb.Trames()
        self.assertEqual(list(trames.recevoir(b'EVT ' + b'x' * 2000)), [])
        self.assertLessEqual(len(trames.tampon), 1028)
        self.assertEqual(list(trames.recevoir(b'\nEVT {}\n')), [b'{}'])

    def test_schema_etranger_refuse(self):
        db = sqlite3.connect(self.base)
        db.execute('PRAGMA user_version=99')
        db.close()
        with self.assertRaises(ValueError):
            usb.initialiser(self.base)


if __name__ == '__main__':
    unittest.main()

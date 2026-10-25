import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('rfid', Path(__file__).parents[1] / 'lecteur-rfid.py')
rfid = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rfid)


def bloc(valeurs):
    a, b, c, d = valeurs
    return valeurs + [a ^ b ^ c ^ d]


class Lecteur:
    MI_OK = 0
    PICC_REQALL = 0x52
    PCD_TRANSCEIVE = 0x0C
    BitFramingReg = 13

    def __init__(self, reponses):
        self.reponses = iter(reponses)
        self.commandes = []

    def MFRC522_Request(self, mode):
        return 0, 16

    def Write_MFRC522(self, registre, valeur):
        pass

    def MFRC522_ToCard(self, mode, commande):
        self.commandes.append(commande)
        if commande[0] == 0x50:
            return 1, [], 0
        return next(self.reponses)


def sak(valeur):
    return 0, [valeur] + rfid.crc_a([valeur]), 24


class TestsRFID(unittest.TestCase):
    def test_crc_vecteur_requete_select(self):
        self.assertEqual(rfid.crc_a([0x93, 0x20]), [0x97, 0x0C])

    def test_quatre_octets(self):
        lecteur = Lecteur([(0, bloc([1, 2, 3, 4]), 40), sak(8)])
        self.assertEqual(rfid.lire_uid(lecteur), '01:02:03:04')

    def test_sept_octets_cascade(self):
        lecteur = Lecteur([(0, bloc([0x88, 4, 1, 2]), 40), sak(4),
                          (0, bloc([3, 4, 5, 6]), 40), sak(0)])
        self.assertEqual(rfid.lire_uid(lecteur), '04:01:02:03:04:05:06')
        self.assertEqual(lecteur.commandes[2], [0x95, 0x20])

    def test_bcc_invalide(self):
        with self.assertRaises(ValueError):
            rfid.lire_uid(Lecteur([(0, [1, 2, 3, 4, 0], 40)]))

    def test_sak_crc_invalide(self):
        with self.assertRaises(ValueError):
            rfid.lire_uid(Lecteur([(0, bloc([1, 2, 3, 4]), 40), (0, [8, 0, 0], 24)]))

    def test_cascade_sans_marqueur(self):
        with self.assertRaises(ValueError):
            rfid.lire_uid(Lecteur([(0, bloc([1, 2, 3, 4]), 40), sak(4)]))

    @patch.object(rfid.subprocess, 'run')
    def test_decision_stricte(self, appel):
        for code, sortie, attendu in [(0, 'AUTORISE\n', 'AUTORISE'),
                                      (0, 'REFUSE\n', 'REFUSE'),
                                      (1, 'AUTORISE', 'REFUSE'),
                                      (0, 'INFO AUTORISE', 'REFUSE'),
                                      (0, '', 'REFUSE')]:
            appel.return_value = subprocess.CompletedProcess([], code, sortie, '')
            self.assertEqual(rfid.verifier_acces('01:02:03:04', 'Laboratoire', Path('.')), attendu)
        self.assertIn('verifier-sync', appel.call_args.args[0])

    @patch.object(rfid.subprocess, 'run', side_effect=subprocess.TimeoutExpired('docker', 30))
    def test_delai(self, appel):
        self.assertTrue(rfid.verifier_acces('01:02:03:04', 'Laboratoire', Path('.')).startswith('REFUSE'))


if __name__ == '__main__':
    unittest.main()

import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('console', Path(__file__).parents[1] / 'console-acces.py')
console = importlib.util.module_from_spec(spec)
spec.loader.exec_module(console)


class TestsConsole(unittest.TestCase):
    @patch.object(console.subprocess, 'run')
    def test_retour_ecran_refus_par_defaut(self, appel):
        appel.return_value = subprocess.CompletedProcess([], 0, '', '')
        for decision, attendu in [('AUTORISE', 'AUTORISE'), ('REFUSE', 'REFUSE'),
                                  ('REFUSE (moteur indisponible)', 'ERREUR')]:
            self.assertTrue(console.transmettre_affichage(decision, True))
            self.assertEqual(appel.call_args.args[0][-2:], ['--afficher', attendu])
            self.assertEqual(appel.call_args.args[0][:3], ['sudo', '-n', 'docker'])
        appel.return_value = subprocess.CompletedProcess([], 1, '', '')
        self.assertFalse(console.transmettre_affichage('AUTORISE', True))

    def test_suivi_usb_connexion_et_curseur(self):
        vrai_run = subprocess.run
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as dossier:
            base = Path(dossier) / 'usb.sqlite3'
            db = sqlite3.connect(base)
            db.execute('CREATE TABLE evenements (numero INTEGER PRIMARY KEY, controleur TEXT, porte TEXT, type TEXT, origine TEXT, recu_a_utc TEXT)')
            db.execute('CREATE TABLE etat (id INTEGER PRIMARY KEY, connecte INTEGER, instant REAL)')
            db.execute('INSERT INTO etat VALUES (1, 0, 0)')
            db.commit()
            db.close()

            def executer(commande, **options):
                self.assertIn('journal-usb', commande)
                self.assertTrue(any(str(c).endswith('compose.usb.yaml') for c in commande))
                script = commande[-2].replace('file:/donnees/journal-usb.sqlite3?mode=ro', base.as_uri() + '?mode=ro')
                return vrai_run([sys.executable, '-c', script, commande[-1]], capture_output=True, text=True, check=True)

            with patch.object(console.subprocess, 'run', side_effect=executer):
                self.assertEqual(console.lire_journal(None, True, 'usb'), (0, [], False))

    def test_badge_maintenu_et_retrait(self):
        presence = console.Presence()
        self.assertTrue(presence.nouveau('A', 0))
        for instant in (0.1, 0.5, 0.9, 1.3):
            self.assertFalse(presence.nouveau('A', instant))
        self.assertFalse(presence.nouveau(None, 2))
        self.assertTrue(presence.nouveau('A', 2.2))

    def test_badge_different(self):
        presence = console.Presence()
        presence.nouveau('A', 0)
        self.assertTrue(presence.nouveau('B', 0.1))

    def test_controles_terminal(self):
        self.assertEqual(console.nettoyer('ABC\033[2J\n'), 'ABC?[2J?')

    def test_journal_initialisation_et_rattrapage_sans_perte(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as dossier:
            base = Path(dossier) / 'journal.sqlite3'
            with sqlite3.connect(base) as db:
                db.execute('CREATE TABLE evenements (numero INTEGER PRIMARY KEY, controleur TEXT, porte TEXT, type TEXT, origine TEXT, recu_a_utc TEXT)')
                db.execute("INSERT INTO evenements VALUES (1, 'ESP', 'PORTE_TEST', 'SORTIE_MANUELLE_SIMULEE', 'MTLS', '2026-01-01T00:00:00Z')")
            db.close()
            script = console.LECTURE_JOURNAL.replace('file:/donnees/journal-evenements.sqlite3?mode=ro', base.as_uri() + '?mode=ro')

            def lire(curseur):
                resultat = subprocess.run([sys.executable, '-c', script, str(curseur)], capture_output=True, text=True, check=True)
                return json.loads(resultat.stdout)

            debut = lire('initialiser')
            self.assertEqual(debut, {'curseur': 1, 'evenements': []})
            with sqlite3.connect(base) as db:
                db.executemany("INSERT INTO evenements VALUES (?, 'ESP', 'PORTE_TEST', 'SORTIE_MANUELLE_SIMULEE', 'MTLS', '2026-01-01T00:00:00Z')", [(i,) for i in range(2, 107)])
            db.close()
            lot1 = lire(1)
            self.assertEqual(len(lot1['evenements']), 100)
            lot2 = lire(lot1['curseur'])
            self.assertEqual([e['numero'] for e in lot2['evenements']], list(range(102, 107)))
            self.assertEqual(lire(lot2['curseur']), {'curseur': 106, 'evenements': []})


if __name__ == '__main__':
    unittest.main()

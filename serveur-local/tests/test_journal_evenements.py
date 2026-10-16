#!/usr/bin/env python3
"""Tests du journal sur bases temporaires, sans reseau ni donnees d'exploitation."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid

SOURCE = Path(__file__).resolve().parents[1] / "journal-evenements.py"
if not SOURCE.is_file():
    SOURCE = Path("/usr/local/bin/journal-evenements.py")
specification = importlib.util.spec_from_file_location("journal", SOURCE)
journal = importlib.util.module_from_spec(specification)
specification.loader.exec_module(journal)


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()
        self.addCleanup(self.dossier.cleanup)
        self.base = Path(self.dossier.name) / "journal.sqlite3"
        self.evenement = {
            "version": 1,
            "id_evenement": str(uuid.uuid4()),
            "porte": "PORTE-01",
            "type": "SORTIE_MANUELLE_SIMULEE",
        }

    def ajouter(self, evenement=None, controleur="SECTEUR-01"):
        return journal.enregistrer(
            self.base, controleur,
            json.dumps(evenement or self.evenement).encode(),
        )

    def test_persistance_horodatage_et_origine_locale(self):
        instant = datetime(2026, 10, 16, 20, 0, tzinfo=timezone.utc)
        with patch.object(journal, "datetime") as horloge:
            horloge.now.return_value = instant
            resultat = self.ajouter()
        self.assertEqual(resultat["statut"], "ENREGISTRE")
        # La lecture ouvre une autre connexion au meme fichier.
        lignes = journal.lire(self.base)
        self.assertEqual(len(lignes), 1)
        self.assertEqual(lignes[0]["recu_a_utc"], "2026-10-16T20:00:00.000Z")
        self.assertEqual(lignes[0]["origine"], "TEST_LOCAL")
        self.assertEqual(lignes[0]["controleur"], "SECTEUR-01")
        self.assertNotIn("identite", lignes[0])

    def test_doublon_ne_modifie_ni_ligne_ni_date(self):
        premier = self.ajouter()
        with patch.object(journal, "datetime") as horloge:
            second = self.ajouter()
            horloge.now.assert_not_called()
        self.assertEqual(second["statut"], "DEJA_PRESENT")
        self.assertEqual(second["recu_a_utc"], premier["recu_a_utc"])
        self.assertEqual(len(journal.lire(self.base)), 1)

    def test_meme_identifiant_autre_contenu_refuse(self):
        self.ajouter()
        modifie = dict(self.evenement, porte="PORTE-02")
        with self.assertRaises(journal.ConflitEvenement):
            self.ajouter(modifie)
        self.assertEqual(journal.lire(self.base)[0]["porte"], "PORTE-01")

    def test_identite_controleur_et_date_non_acceptes_du_message(self):
        for cle in ("nom", "identite", "controleur", "recu_a_utc", "mot_de_passe"):
            with self.subTest(cle=cle):
                with self.assertRaises(journal.EvenementInvalide):
                    self.ajouter(dict(self.evenement, **{cle: "FICTIF"}))
        self.assertFalse(self.base.exists())

    def test_types_identifiants_et_evenements_invalides(self):
        changements = [
            {"version": True}, {"version": 1.0}, {"version": 2},
            {"id_evenement": str(uuid.uuid1())},
            {"id_evenement": self.evenement["id_evenement"].upper()},
            {"id_evenement": "invalide"},
            {"porte": "x'); DROP TABLE evenements;--"},
            {"porte": "A"*33}, {"porte": []},
            {"type": "PASSAGE_CONFIRME"}, {"type": "ACCES_AUTORISE"},
        ]
        for changement in changements:
            with self.subTest(changement=changement):
                with self.assertRaises(journal.EvenementInvalide):
                    self.ajouter(dict(self.evenement, **changement))
        self.assertFalse(self.base.exists())

    def test_json_utf8_doublons_et_taille_invalides(self):
        invalides = [
            b'{"version":1,"version":1}', b"[]", b"null",
            b"\\xff", b"{", b" "*1025, b"["*500 + b"]"*500,
        ]
        for contenu in invalides:
            with self.subTest(contenu=contenu[:40]):
                with self.assertRaises(journal.EvenementInvalide):
                    journal.enregistrer(self.base, "SECTEUR-01", contenu)
        self.assertFalse(self.base.exists())

    def test_identifiant_controleur_valide_obligatoire(self):
        for controleur in ("", "A"*33, "ctrl\n", "x'; --", None):
            with self.subTest(controleur=controleur):
                with self.assertRaises(journal.EvenementInvalide):
                    self.ajouter(controleur=controleur)
        self.assertFalse(self.base.exists())

    def test_idempotence_limitee_au_controleur(self):
        self.ajouter(controleur="SECTEUR-01")
        self.ajouter(controleur="SECTEUR-02")
        self.assertEqual(len(journal.lire(self.base)), 2)

    def test_doublons_concurrents_une_seule_ligne(self):
        with ThreadPoolExecutor(max_workers=6) as pool:
            resultats = list(pool.map(lambda _: self.ajouter(), range(18)))
        self.assertEqual(
            sum(r["statut"] == "ENREGISTRE" for r in resultats), 1
        )
        self.assertEqual(len(journal.lire(self.base)), 1)

    def test_evenements_concurrents_distincts(self):
        evenements = [
            dict(self.evenement, id_evenement=str(uuid.uuid4()))
            for _ in range(12)
        ]
        with ThreadPoolExecutor(max_workers=6) as pool:
            resultats = list(pool.map(self.ajouter, evenements))
        self.assertTrue(all(r["statut"] == "ENREGISTRE" for r in resultats))
        self.assertEqual(len(journal.lire(self.base)), 12)

    def test_base_autorisations_existante_non_modifiee(self):
        with closing(sqlite3.connect(self.base)) as connexion, connexion:
            connexion.execute("CREATE TABLE autorisations (code TEXT)")
            connexion.execute("INSERT INTO autorisations VALUES ('FICTIF')")
        with self.assertRaises(journal.BaseIncompatible):
            self.ajouter()
        with closing(sqlite3.connect(self.base)) as connexion, connexion:
            self.assertEqual(
                connexion.execute("SELECT * FROM autorisations").fetchall(),
                [("FICTIF",)],
            )
            self.assertIsNone(connexion.execute(
                "SELECT name FROM sqlite_master WHERE name='evenements'"
            ).fetchone())

    def test_lecture_absente_ne_cree_pas_de_base(self):
        with self.assertRaises(sqlite3.Error):
            journal.lire(self.base)
        self.assertFalse(self.base.exists())

    def test_lecture_bornee(self):
        journal.initialiser(self.base)
        for limite in (0, 101, True):
            with self.subTest(limite=limite):
                with self.assertRaises(journal.EvenementInvalide):
                    journal.lire(self.base, limite)

    def test_cli_refus_sans_echo_du_contenu(self):
        entree = dict(self.evenement, nom="FICTIF_NE_PAS_AFFICHER")
        resultat = subprocess.run(
            [sys.executable, str(SOURCE), "--base", str(self.base),
             "enregistrer", "--controleur", "SECTEUR-01"],
            input=json.dumps(entree), capture_output=True, text=True,
        )
        self.assertEqual(resultat.returncode, 2)
        self.assertEqual(resultat.stdout, "")
        self.assertEqual(
            json.loads(resultat.stderr), {"erreur": "EVENEMENT_INVALIDE"}
        )
        self.assertNotIn("FICTIF_NE_PAS_AFFICHER", resultat.stderr)
        self.assertFalse(self.base.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""Certificats de test ephemeres; aucune cle d'exploitation utilisee."""
from contextlib import redirect_stdout, redirect_stderr
import importlib.util
import io
import json
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[2] / "scripts/preparer-certificats-journal.py"
specification = importlib.util.spec_from_file_location("certificats", SOURCE)
certificats = importlib.util.module_from_spec(specification)
specification.loader.exec_module(certificats)


class CertificatsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.racine = Path(cls.temp.name)
        cls.dossier = cls.racine / "pki"
        cls.phrase = secrets.token_urlsafe(32).encode("ascii")
        with patch.object(certificats.subprocess, "run", wraps=subprocess.run) as appels:
            sortie, erreur = io.StringIO(), io.StringIO()
            with redirect_stdout(sortie), redirect_stderr(erreur):
                cls.resultat = certificats.preparer(cls.dossier, cls.phrase)
            cls.appels = list(appels.call_args_list)
            cls.affichage = sortie.getvalue() + erreur.getvalue()
        cls.autre = cls.racine / "autre"
        certificats.preparer(cls.autre, secrets.token_urlsafe(32).encode("ascii"))

    def test_verification_identites_et_portes(self):
        resultat = certificats.verifier(self.dossier)
        self.assertEqual(resultat["statut"], "CERTIFICATS_VALIDES")
        self.assertEqual(resultat["adresse_pi"], "192.168.81.1")
        self.assertEqual(resultat["controleur"], "SECTEUR-01")
        self.assertEqual(resultat["portes"], ["PORTE-01"])
        self.assertEqual(len(resultat["empreinte_controleur_sha256"]), 64)

    def test_autorite_chiffree_et_separee(self):
        cle = (self.dossier / "autorite/ca.cle.pem").read_bytes()
        self.assertIn(b"BEGIN ENCRYPTED PRIVATE KEY", cle)
        for emplacement in ("pi", "esp32"):
            self.assertFalse((self.dossier / emplacement / "ca.cle.pem").exists())
        self.assertFalse((self.dossier / "pi/controleur.cle.pem").exists())
        self.assertFalse((self.dossier / "esp32/serveur.cle.pem").exists())

    def test_phrase_absente_arguments_et_affichage(self):
        phrase = self.phrase.decode("ascii")
        for appel in self.appels:
            arguments = " ".join(map(str, appel.args[0]))
            self.assertFalse(phrase in arguments)
        self.assertFalse(phrase in self.affichage)
        self.assertNotIn("PRIVATE KEY", self.affichage)

    def test_refus_mauvaise_adresse_serveur(self):
        with self.assertRaises(certificats.ErreurCertificats):
            certificats.executer([
                "verify", "-CAfile", self.dossier / "autorite/ca.cert.pem",
                "-purpose", "sslserver", "-verify_ip", "192.168.81.99",
                self.dossier / "pi/serveur.cert.pem",
            ])

    def test_refus_inversion_roles(self):
        for but, fichier in (
            ("sslserver", "esp32/controleur.cert.pem"),
            ("sslclient", "pi/serveur.cert.pem"),
        ):
            with self.subTest(but=but):
                with self.assertRaises(certificats.ErreurCertificats):
                    certificats.executer([
                        "verify", "-CAfile", self.dossier / "autorite/ca.cert.pem",
                        "-purpose", but, self.dossier / fichier,
                    ])

    def test_refus_autre_autorite(self):
        with self.assertRaises(certificats.ErreurCertificats):
            certificats.executer([
                "verify", "-CAfile", self.autre / "autorite/ca.cert.pem",
                "-purpose", "sslclient", self.dossier / "esp32/controleur.cert.pem",
            ])

    def test_cles_existantes_non_remplacees(self):
        avant = (self.dossier / "autorite/ca.cle.pem").read_bytes()
        with self.assertRaises(certificats.ErreurCertificats):
            certificats.preparer(self.dossier, self.phrase)
        self.assertTrue(avant == (self.dossier / "autorite/ca.cle.pem").read_bytes())

    def test_refus_configuration_invalide(self):
        for options in (
            {"adresse_pi": "127.0.0.1; echo FICTIF"},
            {"controleur": "SECTEUR/../../FICTIF"},
            {"porte": "PORTE\nFICTIVE"},
        ):
            with self.subTest(options=options):
                destination = self.racine / "invalide"
                with self.assertRaises(certificats.ErreurCertificats):
                    certificats.preparer(destination, self.phrase, **options)
                self.assertFalse(destination.exists())
        for phrase in (b"court", b"A"*16 + b"\n", b"A"*16 + b"\x00"):
            with self.assertRaises(certificats.ErreurCertificats):
                certificats.preparer(self.racine / "invalide", phrase)

    def test_refus_empreinte_client_modifiee(self):
        copie = self.racine / "empreinte-modifiee"
        shutil.copytree(self.dossier, copie)
        fichier = copie / "pi/controleurs.json"
        contenu = json.loads(fichier.read_text())
        contenu["controleurs"][0]["empreinte_sha256"] = "0"*64
        fichier.write_text(json.dumps(contenu))
        with self.assertRaises(certificats.ErreurCertificats):
            certificats.verifier(copie)

    def test_refus_cle_serveur_non_correspondante(self):
        copie = self.racine / "cle-modifiee"
        shutil.copytree(self.dossier, copie)
        shutil.copyfile(
            self.autre / "pi/serveur.cle.pem", copie / "pi/serveur.cle.pem"
        )
        with self.assertRaises(certificats.ErreurCertificats):
            certificats.verifier(copie)


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""Tests HTTPS reels sur boucle locale, certificats et bases ephemeres."""
import asyncio
from contextlib import closing
import importlib.util
import json
from pathlib import Path
import secrets
import sqlite3
import ssl
import tempfile
import unittest
from unittest.mock import patch
import uuid
from aiohttp import ClientError, ClientSession, ClientTimeout, web


def charger(nom, source):
    spec = importlib.util.spec_from_file_location(nom, source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RACINE = Path(__file__).resolve().parents[2]
serveur = charger("serveur", RACINE / "serveur-local/journal-https.py")
certificats = charger("certificats", RACINE / "scripts/preparer-certificats-journal.py")


class HttpsTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.pki = Path(cls.temp.name) / "pki"
        certificats.preparer(cls.pki, secrets.token_urlsafe(32).encode(), adresse_pi="127.0.0.1")
        cls.autre = Path(cls.temp.name) / "autre"
        certificats.preparer(cls.autre, secrets.token_urlsafe(32).encode(), adresse_pi="127.0.0.1")

    async def asyncSetUp(self):
        self.temp_base = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_base.cleanup)
        self.base = Path(self.temp_base.name) / "journal.sqlite3"
        self.droits = serveur.charger_droits(self.pki / "pi/controleurs.json")
        self.app = serveur.creer_application(self.base, self.droits, delai=0.2)
        self.runner = web.AppRunner(self.app, access_log=None)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, "127.0.0.1", 0,
                               ssl_context=serveur.contexte_tls(self.pki / "pi"))
        await self.site.start()
        self.addAsyncCleanup(self.runner.cleanup)
        port = self.site._server.sockets[0].getsockname()[1]
        self.port = port
        self.url = f"https://127.0.0.1:{port}/v1/evenements"
        self.session = ClientSession(timeout=ClientTimeout(total=3))
        self.addAsyncCleanup(self.session.close)
        self.evenement = dict(version=1, id_evenement=str(uuid.uuid4()),
                              porte="PORTE-01", type="SORTIE_MANUELLE_SIMULEE")

    def contexte_client(self, certificat=True, autre=False, role_serveur=False):
        contexte = ssl.create_default_context(cafile=str(self.pki / "esp32/ca.cert.pem"))
        contexte.verify_flags |= ssl.VERIFY_X509_STRICT
        if certificat:
            racine = self.autre if autre else self.pki
            dossier = racine / ("pi" if role_serveur else "esp32")
            nom = "serveur" if role_serveur else "controleur"
            contexte.load_cert_chain(str(dossier / f"{nom}.cert.pem"), str(dossier / f"{nom}.cle.pem"))
        return contexte

    async def poster(self, evenement=None, **kwargs):
        async with self.session.post(self.url, json=evenement or self.evenement,
                                     ssl=self.contexte_client(), **kwargs) as resultat:
            return resultat.status, await resultat.json()

    async def test_enregistrement_apres_commit_et_doublon(self):
        statut, premier = await self.poster()
        self.assertEqual(statut, 201)
        lignes = serveur.journal.lire(self.base)
        self.assertEqual(lignes[0]["origine"], "MTLS")
        self.assertEqual(lignes[0]["controleur"], "SECTEUR-01")
        statut, second = await self.poster()
        self.assertEqual(statut, 200)
        self.assertEqual(second["statut"], "DEJA_PRESENT")
        self.assertEqual(second["recu_a_utc"], premier["recu_a_utc"])
        self.assertEqual(len(serveur.journal.lire(self.base)), 1)

    async def test_refus_sans_certificat(self):
        with self.assertRaises((OSError, asyncio.TimeoutError, ClientError)):
            async with self.session.post(self.url, json=self.evenement,
                                         ssl=self.contexte_client(False)) as reponse:
                await reponse.read()
        self.assertFalse(self.base.exists())

    async def test_refus_autre_autorite(self):
        with self.assertRaises((OSError, asyncio.TimeoutError, ClientError)):
            async with self.session.post(self.url, json=self.evenement,
                                         ssl=self.contexte_client(autre=True)) as reponse:
                await reponse.read()
        self.assertFalse(self.base.exists())

    async def test_refus_role_serveur_comme_client(self):
        with self.assertRaises((OSError, asyncio.TimeoutError, ClientError)):
            async with self.session.post(self.url, json=self.evenement,
                                         ssl=self.contexte_client(role_serveur=True)) as reponse:
                await reponse.read()
        self.assertFalse(self.base.exists())

    async def test_refus_empreinte_non_autorisee(self):
        self.droits.clear()
        statut, resultat = await self.poster()
        self.assertEqual((statut, resultat), (403, {"erreur": "CONTROLEUR_NON_AUTORISE"}))
        self.assertFalse(self.base.exists())

    async def test_refus_porte_non_autorisee(self):
        statut, _ = await self.poster(dict(self.evenement, porte="PORTE-02"))
        self.assertEqual(statut, 403)
        self.assertFalse(self.base.exists())

    async def test_identite_non_acceptee_du_message_ni_entetes(self):
        statut, resultat = await self.poster(dict(self.evenement, controleur="USURPE"))
        self.assertEqual(statut, 400)
        self.assertNotIn("USURPE", json.dumps(resultat))
        statut, _ = await self.poster(headers={"X-Controleur": "USURPE"})
        self.assertEqual(statut, 201)
        self.assertEqual(serveur.journal.lire(self.base)[0]["controleur"], "SECTEUR-01")

    async def test_conflit_origine_locale(self):
        serveur.journal.enregistrer(self.base, "SECTEUR-01", json.dumps(self.evenement).encode())
        statut, _ = await self.poster()
        self.assertEqual(statut, 409)
        self.assertEqual(serveur.journal.lire(self.base)[0]["origine"], "TEST_LOCAL")

    async def test_stockage_indisponible_sans_accuse(self):
        with patch.object(serveur.journal, "enregistrer", side_effect=sqlite3.OperationalError("secret")):
            statut, resultat = await self.poster()
        self.assertEqual((statut, resultat), (503, {"erreur": "STOCKAGE_INDISPONIBLE"}))

    async def test_corps_surdimensionne_json_duplique_et_compression(self):
        for corps, entetes, attendu in [
            (b"x"*1025, {"Content-Type": "application/json"}, 413),
            (b'{"version":1,"version":1}', {"Content-Type": "application/json"}, 400),
            (b"faux", {"Content-Type": "application/json", "Content-Encoding": "gzip"}, 400),
        ]:
            async with self.session.post(self.url, data=corps, headers=entetes,
                                         ssl=self.contexte_client()) as resultat:
                self.assertEqual(resultat.status, attendu)
        self.assertFalse(self.base.exists())

    async def test_flux_surdimensionne(self):
        async def morceaux():
            yield b" "*600
            yield b" "*600
        async with self.session.post(self.url, data=morceaux(),
                                     headers={"Content-Type": "application/json"},
                                     ssl=self.contexte_client()) as resultat:
            self.assertEqual(resultat.status, 413)
        self.assertFalse(self.base.exists())

    async def test_lecture_distante_absente(self):
        async with self.session.get(self.url, ssl=self.contexte_client()) as resultat:
            self.assertEqual(resultat.status, 405)
        self.assertFalse(self.base.exists())

    async def test_delai_corps_incomplet(self):
        lecteur, ecrivain = await asyncio.open_connection(
            "127.0.0.1", self.port, ssl=self.contexte_client())
        try:
            ecrivain.write(b"POST /v1/evenements HTTP/1.1\r\nHost: localhost\r\n"
                           b"Content-Type: application/json\r\nContent-Length: 100\r\n\r\n{")
            await ecrivain.drain()
            resultat = await asyncio.wait_for(lecteur.read(4096), 2)
            self.assertIn(b"408", resultat.split(b"\r\n")[0])
        finally:
            ecrivain.close()
            await ecrivain.wait_closed()
        self.assertFalse(self.base.exists())

    async def test_migration_v1_conserve_lignes(self):
        # Reconstruit le schema v1 sans dependre d'un fichier de production ancien.
        with closing(sqlite3.connect(self.base)) as connexion, connexion:
            connexion.execute("""
                CREATE TABLE evenements (
                    numero INTEGER PRIMARY KEY,
                    controleur TEXT NOT NULL CHECK(length(controleur) BETWEEN 1 AND 32),
                    id_evenement TEXT NOT NULL CHECK(length(id_evenement) = 36),
                    version INTEGER NOT NULL CHECK(version = 1),
                    porte TEXT NOT NULL CHECK(length(porte) BETWEEN 1 AND 32),
                    type TEXT NOT NULL CHECK(type = 'SORTIE_MANUELLE_SIMULEE'),
                    origine TEXT NOT NULL CHECK(origine = 'TEST_LOCAL'),
                    recu_a_utc TEXT NOT NULL,
                    UNIQUE(controleur, id_evenement)
                ) STRICT
            """)
            connexion.execute("PRAGMA user_version=1")
            connexion.execute("INSERT INTO evenements VALUES (1, ?, ?, 1, ?, ?, 'TEST_LOCAL', ?)",
                              ("SECTEUR-01", str(uuid.uuid4()), "PORTE-01",
                               "SORTIE_MANUELLE_SIMULEE", "2026-10-16T20:00:00.000Z"))
        avant = serveur.journal.lire(self.base)
        statut, _ = await self.poster()
        self.assertEqual(statut, 201)
        apres = serveur.journal.lire(self.base)
        self.assertEqual(apres[-1], avant[0])
        with closing(sqlite3.connect(self.base)) as connexion:
            self.assertEqual(connexion.execute("PRAGMA user_version").fetchone()[0], 2)

    async def test_configuration_droits_invalide(self):
        chemin = Path(self.temp_base.name) / "droits.json"
        for contenu in [
            '{"version":1,"version":1,"controleurs":[]}',
            '{"version":true,"controleurs":[]}',
            json.dumps({"version": 1, "controleurs": [
                {"id": "A", "empreinte_sha256": "a"*64, "portes": ["P"]},
                {"id": "B", "empreinte_sha256": "a"*64, "portes": ["P"]}]}),
        ]:
            chemin.write_text(contenu)
            with self.assertRaises(ValueError):
                serveur.charger_droits(chemin)


if __name__ == "__main__":
    unittest.main(verbosity=2)


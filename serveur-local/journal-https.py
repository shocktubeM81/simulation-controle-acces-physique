#!/usr/bin/env python3
"""Reception HTTPS mTLS du journal de simulation; aucune route de lecture."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.util
import json
import logging
import os
from pathlib import Path
import re
import sqlite3
import ssl
import sys
from aiohttp import web

SOURCE = Path(__file__).with_name("journal-evenements.py")
spec = importlib.util.spec_from_file_location("journal_stockage", SOURCE)
journal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(journal)


def charger_droits(chemin):
    donnees = Path(chemin).read_bytes()
    if len(donnees) > 65536:
        raise ValueError("Configuration trop grande")
    configuration = json.loads(donnees, object_pairs_hook=journal._objet_sans_doublon)
    if (not isinstance(configuration, dict)
            or set(configuration) != {"version", "controleurs"}
            or type(configuration["version"]) is not int
            or configuration["version"] != 1
            or not isinstance(configuration["controleurs"], list)
            or not 1 <= len(configuration["controleurs"]) <= 100):
        raise ValueError("Configuration invalide")
    droits, identifiants = {}, set()
    for entree in configuration["controleurs"]:
        if not isinstance(entree, dict) or set(entree) != {"id", "empreinte_sha256", "portes"}:
            raise ValueError("Controleur invalide")
        identifiant, empreinte, portes = entree["id"], entree["empreinte_sha256"], entree["portes"]
        if (not isinstance(identifiant, str)
                or journal.IDENTIFIANT.fullmatch(identifiant) is None
                or identifiant in identifiants
                or not isinstance(empreinte, str)
                or re.fullmatch(r"[0-9a-f]{64}", empreinte) is None
                or empreinte in droits
                or not isinstance(portes, list) or not 1 <= len(portes) <= 100):
            raise ValueError("Identite invalide")
        if any(not isinstance(p, str) or journal.IDENTIFIANT.fullmatch(p) is None for p in portes):
            raise ValueError("Porte invalide")
        if len(set(portes)) != len(portes):
            raise ValueError("Porte repetee")
        droits[empreinte] = (identifiant, frozenset(portes))
        identifiants.add(identifiant)
    return droits


def contexte_tls(dossier):
    dossier = Path(dossier)
    contexte = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    contexte.minimum_version = ssl.TLSVersion.TLSv1_2
    contexte.verify_mode = ssl.CERT_REQUIRED
    contexte.verify_flags |= ssl.VERIFY_X509_STRICT
    contexte.options |= ssl.OP_NO_TICKET
    contexte.load_verify_locations(cafile=str(dossier / "ca.cert.pem"))
    contexte.load_cert_chain(str(dossier / "serveur.cert.pem"), str(dossier / "serveur.cle.pem"))
    return contexte


def reponse(statut, contenu):
    resultat = web.json_response(contenu, status=statut, headers={"Cache-Control": "no-store"})
    resultat.force_close()
    return resultat


def creer_application(base, droits, *, delai=5):
    # Deux requetes en cours au maximum, y compris la lecture du corps.
    en_cours = 0

    async def recevoir(request):
        nonlocal en_cours
        transport = request.transport
        tls = transport.get_extra_info("ssl_object") if transport else None
        certificat = tls.getpeercert(binary_form=True) if tls else None
        identite = droits.get(hashlib.sha256(certificat).hexdigest()) if certificat else None
        if identite is None:
            return reponse(403, {"erreur": "CONTROLEUR_NON_AUTORISE"})
        if en_cours >= 2:
            return reponse(503, {"erreur": "SERVICE_OCCUPE"})
        en_cours += 1
        try:
            if (request.query_string
                    or request.content_type != "application/json"
                    or request.headers.get("Content-Encoding", "identity") != "identity"):
                return reponse(400, {"erreur": "REQUETE_INVALIDE"})
            if request.content_length is not None and request.content_length > journal.TAILLE_MAX:
                return reponse(413, {"erreur": "EVENEMENT_TROP_GRAND"})
            contenu = bytearray()
            try:
                async with asyncio.timeout(delai):
                    async for morceau in request.content.iter_chunked(1024):
                        contenu.extend(morceau)
                        if len(contenu) > journal.TAILLE_MAX:
                            return reponse(413, {"erreur": "EVENEMENT_TROP_GRAND"})
            except TimeoutError:
                return reponse(408, {"erreur": "DELAI_DEPASSE"})
            try:
                evenement = journal.valider(bytes(contenu))
                controleur, portes = identite
                if evenement["porte"] not in portes:
                    return reponse(403, {"erreur": "PORTE_NON_AUTORISEE"})
                resultat = await asyncio.to_thread(
                    journal.enregistrer, base, controleur, bytes(contenu), origine="MTLS"
                )
            except journal.EvenementInvalide:
                return reponse(400, {"erreur": "EVENEMENT_INVALIDE"})
            except journal.ConflitEvenement:
                return reponse(409, {"erreur": "CONFLIT_EVENEMENT"})
            except (journal.BaseIncompatible, sqlite3.Error, OSError):
                return reponse(503, {"erreur": "STOCKAGE_INDISPONIBLE"})
            return reponse(201 if resultat["statut"] == "ENREGISTRE" else 200, resultat)
        finally:
            en_cours -= 1

    app = web.Application(
        client_max_size=journal.TAILLE_MAX,
        handler_args={"auto_decompress": False, "max_line_size": 2048, "max_field_size": 2048},
    )
    app.router.add_post("/v1/evenements", recevoir)
    return app


def main():
    os.umask(0o077)
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--pki", default="/run/journal-pki")
    analyseur.add_argument("--base", default="/donnees/journal-evenements.sqlite3")
    arguments = analyseur.parse_args()
    try:
        droits = charger_droits(Path(arguments.pki) / "controleurs.json")
        contexte = contexte_tls(arguments.pki)
        journal.initialiser(arguments.base)
    except (ValueError, OSError, sqlite3.Error, journal.BaseIncompatible):
        print('{"erreur":"INITIALISATION_REFUSEE"}', file=sys.stderr)
        return 1
    # Aucun contenu de requete, certificat ou identifiant personnel dans les logs.
    logging.getLogger("aiohttp.server").disabled = True
    print('{"statut":"CONFIGURATION_HTTPS_VALIDEE","port":8443}', flush=True)
    web.run_app(
        creer_application(arguments.base, droits), host="0.0.0.0", port=8443,
        ssl_context=contexte, access_log=None, print=None,
        keepalive_timeout=5, shutdown_timeout=10,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


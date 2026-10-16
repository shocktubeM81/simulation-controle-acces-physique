#!/usr/bin/env python3
"""Prepare les certificats du journal, sans ouvrir de service reseau."""
from __future__ import annotations

import argparse
import getpass
import hashlib
import hmac
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys

IDENTIFIANT = re.compile(r"[A-Z0-9][A-Z0-9_-]{0,31}", re.ASCII)


class ErreurCertificats(ValueError):
    pass


def executer(arguments, *, entree=None):
    try:
        resultat = subprocess.run(
            ["openssl", *map(str, arguments)],
            input=entree, capture_output=True, check=False, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as erreur:
        raise ErreurCertificats("OpenSSL indisponible ou delai depasse.") from erreur
    if resultat.returncode:
        # Les sorties brutes des outils ne sont jamais reproduites.
        raise ErreurCertificats("Operation OpenSSL echouee: " + arguments[0])
    return resultat.stdout


def verifier_openssl():
    version = executer(["version"]).decode("ascii", errors="replace").strip()
    if not version.startswith("OpenSSL 3."):
        raise ErreurCertificats("OpenSSL 3.x requis.")
    return version


def _serie():
    return "0x" + format(secrets.randbits(159) | (1 << 158), "x")


def _empreinte(certificat):
    der = executer(["x509", "-in", certificat, "-outform", "DER"])
    return hashlib.sha256(der).hexdigest()


def _verifier_cle(certificat, cle):
    public_certificat = executer(["x509", "-in", certificat, "-pubkey", "-noout"])
    public_certificat = executer(
        ["pkey", "-pubin", "-outform", "DER"], entree=public_certificat
    )
    public_cle = executer(["pkey", "-in", cle, "-pubout", "-outform", "DER"])
    if not hmac.compare_digest(public_certificat, public_cle):
        raise ErreurCertificats("Certificat et cle non correspondants.")


def verifier(dossier):
    dossier = Path(dossier)
    version = verifier_openssl()
    try:
        parametres = json.loads((dossier / "parametres.json").read_text())
        adresse = str(ipaddress.IPv4Address(parametres["adresse_pi"]))
        controleur = parametres["controleur"]
        if not isinstance(controleur, str) or IDENTIFIANT.fullmatch(controleur) is None:
            raise ValueError("controleur")
        autorisations = json.loads((dossier / "pi/controleurs.json").read_text())
        if autorisations["version"] != 1 or len(autorisations["controleurs"]) != 1:
            raise ValueError("autorisations")
        autorisation = autorisations["controleurs"][0]
        empreinte_autorisee = autorisation["empreinte_sha256"]
        if not isinstance(empreinte_autorisee, str) or re.fullmatch(
                r"[0-9a-f]{64}", empreinte_autorisee) is None:
            raise ValueError("empreinte")
        if autorisation["id"] != controleur:
            raise ValueError("identite")
        portes = autorisation["portes"]
        if not isinstance(portes, list) or len(portes) != 1:
            raise ValueError("portes")
        if not isinstance(portes[0], str) or IDENTIFIANT.fullmatch(portes[0]) is None:
            raise ValueError("porte")
        cle_autorite = (dossier / "autorite/ca.cle.pem").read_bytes()
    except (OSError, ValueError, TypeError, KeyError) as erreur:
        raise ErreurCertificats("Arborescence ou parametres de certificats invalides.") from erreur

    if b"BEGIN ENCRYPTED PRIVATE KEY" not in cle_autorite:
        raise ErreurCertificats("La cle d'autorite doit etre chiffree.")
    ca = dossier / "autorite/ca.cert.pem"
    serveur = dossier / "pi/serveur.cert.pem"
    client = dossier / "esp32/controleur.cert.pem"
    executer(["verify", "-x509_strict", "-CAfile", ca, ca])
    executer(["verify", "-x509_strict", "-CAfile", ca, "-purpose",
              "sslserver", "-verify_ip", adresse, serveur])
    executer(["verify", "-x509_strict", "-CAfile", ca, "-purpose",
              "sslclient", client])
    _verifier_cle(serveur, dossier / "pi/serveur.cle.pem")
    _verifier_cle(client, dossier / "esp32/controleur.cle.pem")
    for copie in (dossier / "pi/ca.cert.pem", dossier / "esp32/ca.cert.pem"):
        if copie.read_bytes() != ca.read_bytes():
            raise ErreurCertificats("Copie du certificat d'autorite incoherente.")
    empreinte_client = _empreinte(client)
    if not hmac.compare_digest(autorisation["empreinte_sha256"], empreinte_client):
        raise ErreurCertificats("Empreinte du controleur incoherente.")
    return {
        "statut": "CERTIFICATS_VALIDES",
        "openssl": version,
        "adresse_pi": adresse,
        "controleur": controleur,
        "portes": portes,
        "empreinte_controleur_sha256": empreinte_client,
    }


def preparer(dossier, phrase: bytes, *, adresse_pi="192.168.81.1",
             controleur="SECTEUR-01", porte="PORTE-01"):
    if not isinstance(phrase, bytes) or not 16 <= len(phrase) <= 1024:
        raise ErreurCertificats("Phrase de protection: 16 a 1024 octets UTF-8.")
    if any(caractere in phrase for caractere in (b"\n", b"\r", b"\0")):
        raise ErreurCertificats("Phrase de protection invalide.")
    try:
        adresse = str(ipaddress.IPv4Address(adresse_pi))
    except ipaddress.AddressValueError as erreur:
        raise ErreurCertificats("Adresse IPv4 du Pi invalide.") from erreur
    if any(not isinstance(x, str) or IDENTIFIANT.fullmatch(x) is None
           for x in (controleur, porte)):
        raise ErreurCertificats("Identifiant de controleur ou porte invalide.")
    verifier_openssl()
    dossier = Path(dossier).absolute()
    try:
        # Ne jamais ecraser ni reutiliser silencieusement une PKI existante.
        dossier.mkdir(mode=0o700, parents=True, exist_ok=False)
    except FileExistsError as erreur:
        raise ErreurCertificats("Dossier deja present: aucune cle remplacee.") from erreur
    for nom in ("autorite", "pi", "esp32", "travail"):
        (dossier / nom).mkdir(mode=0o700)

    configuration = dossier / "travail/extensions.cnf"
    configuration.write_text(
        "[req]\nprompt=no\ndistinguished_name=dn\n"
        "[dn]\nCN=ControleAcces-Labo-CA\n"
        "[autorite]\nbasicConstraints=critical,CA:TRUE,pathlen:0\n"
        "keyUsage=critical,keyCertSign,cRLSign\nsubjectKeyIdentifier=hash\n"
        "authorityKeyIdentifier=keyid:always\n"
        "[serveur]\nbasicConstraints=critical,CA:FALSE\n"
        "keyUsage=critical,digitalSignature\nextendedKeyUsage=serverAuth\n"
        "subjectKeyIdentifier=hash\nauthorityKeyIdentifier=keyid,issuer\n"
        f"subjectAltName=IP:{adresse}\n"
        "[client]\nbasicConstraints=critical,CA:FALSE\n"
        "keyUsage=critical,digitalSignature\nextendedKeyUsage=clientAuth\n"
        "subjectKeyIdentifier=hash\nauthorityKeyIdentifier=keyid,issuer\n"
        f"subjectAltName=URI:urn:controle-acces:controleur:{controleur}\n",
        encoding="ascii",
    )
    ca_cle = dossier / "autorite/ca.cle.pem"
    ca_cert = dossier / "autorite/ca.cert.pem"
    entree_protegee = phrase + b"\n"
    executer(["genpkey", "-algorithm", "EC", "-pkeyopt",
              "ec_paramgen_curve:P-256", "-aes-256-cbc", "-pass",
              "stdin", "-out", ca_cle], entree=entree_protegee)
    executer(["req", "-new", "-x509", "-key", ca_cle, "-passin", "stdin",
              "-config", configuration, "-extensions", "autorite",
              "-days", "365", "-sha256", "-set_serial", _serie(),
              "-out", ca_cert], entree=entree_protegee)

    for role, sous_dossier, nom, sujet in (
        ("serveur", "pi", "serveur", "journal-pi"),
        ("client", "esp32", "controleur", controleur),
    ):
        cle = dossier / sous_dossier / (nom + ".cle.pem")
        certificat = dossier / sous_dossier / (nom + ".cert.pem")
        requete = dossier / "travail" / (nom + ".csr.pem")
        executer(["genpkey", "-algorithm", "EC", "-pkeyopt",
                  "ec_paramgen_curve:P-256", "-out", cle])
        executer(["req", "-new", "-key", cle, "-config", configuration,
                  "-subj", "/CN=" + sujet, "-out", requete])
        executer(["x509", "-req", "-in", requete, "-CA", ca_cert,
                  "-CAkey", ca_cle, "-passin", "stdin", "-set_serial", _serie(),
                  "-days", "90", "-sha256", "-extfile", configuration,
                  "-extensions", role, "-out", certificat],
                 entree=entree_protegee)
        shutil.copyfile(ca_cert, dossier / sous_dossier / "ca.cert.pem")

    (dossier / "parametres.json").write_text(
        json.dumps({"version": 1, "adresse_pi": adresse, "controleur": controleur},
                   indent=2) + "\n", encoding="ascii"
    )
    (dossier / "pi/controleurs.json").write_text(
        json.dumps({"version": 1, "controleurs": [{
            "id": controleur,
            "empreinte_sha256": _empreinte(dossier / "esp32/controleur.cert.pem"),
            "portes": [porte],
        }]}, indent=2) + "\n", encoding="ascii"
    )
    for fichier in dossier.rglob("*"):
        if fichier.is_file():
            fichier.chmod(0o600)
    return verifier(dossier)


def main():
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--verifier", action="store_true")
    arguments = analyseur.parse_args()
    racine = Path(__file__).resolve().parents[1]
    dossier = racine / "secrets/journal-pki"
    try:
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            raise ErreurCertificats("Executer avec le compte utilisateur, sans sudo.")
        if arguments.verifier:
            resultat = verifier(dossier)
        else:
            if dossier.exists():
                raise ErreurCertificats("Dossier deja present: utiliser --verifier.")
            git = subprocess.run(
                ["git", "-C", str(racine), "check-ignore", "--quiet", "--",
                 "secrets/journal-pki/autorite/ca.cle.pem"],
                capture_output=True, check=False,
            )
            if git.returncode != 0:
                raise ErreurCertificats("Le dossier des secrets doit etre exclu de Git.")
            if not sys.stdin.isatty():
                raise ErreurCertificats("Terminal interactif requis pour proteger la phrase.")
            phrase = getpass.getpass("Phrase de protection de l'autorite (16 caracteres minimum): ")
            confirmation = getpass.getpass("Confirmer la phrase: ")
            if phrase != confirmation:
                raise ErreurCertificats("Les phrases ne correspondent pas.")
            os.umask(0o077)
            resultat = preparer(dossier, phrase.encode("utf-8"))
        print(json.dumps(resultat, ensure_ascii=True))
        return 0
    except (ErreurCertificats, OSError) as erreur:
        print("Erreur: " + str(erreur), file=sys.stderr)
        return 2
    except (EOFError, KeyboardInterrupt):
        print("Operation interrompue; verifier le dossier local avant de recommencer.",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

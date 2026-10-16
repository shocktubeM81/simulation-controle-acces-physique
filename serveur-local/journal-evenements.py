#!/usr/bin/env python3
"""Journal local de simulation. Aucune ecoute reseau ni identification de personne."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import uuid

TAILLE_MAX = 1024
CHAMPS = {"version", "id_evenement", "porte", "type"}
TYPE_EVENEMENT = "SORTIE_MANUELLE_SIMULEE"
IDENTIFIANT = re.compile(r"[A-Z0-9][A-Z0-9_-]{0,31}", re.ASCII)
COLONNES = (
    "numero", "controleur", "id_evenement", "version", "porte",
    "type", "origine", "recu_a_utc",
)


class EvenementInvalide(ValueError):
    pass


class ConflitEvenement(ValueError):
    pass


class BaseIncompatible(ValueError):
    pass


def _objet_sans_doublon(paires):
    resultat = {}
    for cle, valeur in paires:
        if cle in resultat:
            raise EvenementInvalide("Cle JSON repetee.")
        resultat[cle] = valeur
    return resultat


def valider(contenu: bytes) -> dict:
    if not isinstance(contenu, bytes) or len(contenu) > TAILLE_MAX:
        raise EvenementInvalide("Taille maximale: 1024 octets.")
    try:
        evenement = json.loads(
            contenu.decode("utf-8"), object_pairs_hook=_objet_sans_doublon
        )
    except (UnicodeError, ValueError, RecursionError) as erreur:
        raise EvenementInvalide("JSON invalide.") from erreur
    if not isinstance(evenement, dict) or set(evenement) != CHAMPS:
        raise EvenementInvalide("Champs absents ou non autorises.")
    if type(evenement["version"]) is not int or evenement["version"] != 1:
        raise EvenementInvalide("Version non prise en charge.")
    identifiant = evenement["id_evenement"]
    if not isinstance(identifiant, str):
        raise EvenementInvalide("Identifiant d'evenement invalide.")
    try:
        identifiant_uuid = uuid.UUID(identifiant)
    except (ValueError, AttributeError) as erreur:
        raise EvenementInvalide("Identifiant d'evenement invalide.") from erreur
    if (
        str(identifiant_uuid) != identifiant
        or identifiant_uuid.version != 4
        or identifiant_uuid.variant != uuid.RFC_4122
    ):
        raise EvenementInvalide("UUID v4 canonique requis.")
    if (
        not isinstance(evenement["porte"], str)
        or IDENTIFIANT.fullmatch(evenement["porte"]) is None
    ):
        raise EvenementInvalide("Identifiant de porte invalide.")
    if evenement["type"] != TYPE_EVENEMENT:
        raise EvenementInvalide("Type d'evenement non pris en charge.")
    return evenement


def _verifier_schema(connexion: sqlite3.Connection, creation: bool) -> None:
    version = connexion.execute("PRAGMA user_version").fetchone()[0]
    tables = {
        ligne[0]
        for ligne in connexion.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%'"
        )
    }
    if version == 0 and not tables and creation:
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
        connexion.execute("PRAGMA user_version = 1")
        return
    if version != 1 or tables != {"evenements"}:
        raise BaseIncompatible("Base absente, incompatible ou non reservee au journal.")
    colonnes = tuple(
        ligne[1] for ligne in connexion.execute("PRAGMA table_info(evenements)")
    )
    if colonnes != COLONNES:
        raise BaseIncompatible("Schema du journal incompatible.")


@contextmanager
def _connexion(base, *, ecriture: bool):
    chemin = Path(base).absolute()
    if chemin.is_symlink():
        raise BaseIncompatible("Le fichier de journal ne doit pas etre un lien.")
    if ecriture:
        # La creation exclusive applique les droits avant la premiere ecriture SQLite.
        try:
            descripteur = os.open(
                chemin, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600
            )
        except FileExistsError:
            pass
        else:
            os.close(descripteur)
        connexion = sqlite3.connect(chemin, timeout=5, isolation_level=None)
    else:
        connexion = sqlite3.connect(
            chemin.as_uri() + "?mode=ro", uri=True, timeout=5, isolation_level=None
        )
    try:
        connexion.row_factory = sqlite3.Row
        connexion.execute("PRAGMA trusted_schema = OFF")
        connexion.execute("PRAGMA foreign_keys = ON")
        if ecriture:
            connexion.execute("PRAGMA synchronous = FULL")
            connexion.execute("BEGIN IMMEDIATE")
        _verifier_schema(connexion, creation=ecriture)
        yield connexion
        if ecriture:
            connexion.commit()
    except BaseException:
        if ecriture:
            connexion.rollback()
        raise
    finally:
        connexion.close()


def initialiser(base) -> None:
    with _connexion(base, ecriture=True):
        pass


def enregistrer(base, controleur: str, contenu: bytes) -> dict:
    # Ce contexte est fourni par l'operateur local, jamais extrait du message.
    # Un futur transport devra le fournir APRES authentification du controleur.
    if not isinstance(controleur, str) or IDENTIFIANT.fullmatch(controleur) is None:
        raise EvenementInvalide("Identifiant de controleur invalide.")
    evenement = valider(contenu)
    with _connexion(base, ecriture=True) as connexion:
        precedent = connexion.execute(
            "SELECT version, porte, type, recu_a_utc FROM evenements "
            "WHERE controleur = ? AND id_evenement = ?",
            (controleur, evenement["id_evenement"]),
        ).fetchone()
        if precedent is not None:
            if tuple(precedent)[:3] != (
                evenement["version"], evenement["porte"], evenement["type"]
            ):
                raise ConflitEvenement("Identifiant deja utilise pour un autre contenu.")
            statut = "DEJA_PRESENT"
            recu_a = precedent["recu_a_utc"]
        else:
            recu_a = (
                datetime.now(timezone.utc).isoformat(timespec="milliseconds")
                .replace("+00:00", "Z")
            )
            connexion.execute(
                "INSERT INTO evenements "
                "(controleur, id_evenement, version, porte, type, origine, recu_a_utc) "
                "VALUES (?, ?, ?, ?, ?, 'TEST_LOCAL', ?)",
                (
                    controleur, evenement["id_evenement"], evenement["version"],
                    evenement["porte"], evenement["type"], recu_a,
                ),
            )
            statut = "ENREGISTRE"
    # L'accuse de reception n'est produit qu'apres le commit.
    return {
        "statut": statut,
        "id_evenement": evenement["id_evenement"],
        "recu_a_utc": recu_a,
    }


def lire(base, limite: int = 20) -> list[dict]:
    if type(limite) is not int or not 1 <= limite <= 100:
        raise EvenementInvalide("Limite de lecture: 1 a 100.")
    with _connexion(base, ecriture=False) as connexion:
        return [
            dict(ligne) for ligne in connexion.execute(
                "SELECT numero, controleur, id_evenement, version, porte, type, "
                "origine, recu_a_utc FROM evenements ORDER BY numero DESC LIMIT ?",
                (limite,),
            )
        ]


def main() -> int:
    os.umask(0o077)
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument(
        "--base", default="/donnees/journal-evenements.sqlite3",
        help="Base dediee au journal, distincte des caches d'autorisations.",
    )
    commandes = analyseur.add_subparsers(dest="commande", required=True)
    commandes.add_parser("initialiser")
    ajout = commandes.add_parser("enregistrer")
    ajout.add_argument("--controleur", required=True)
    lecture = commandes.add_parser("lire")
    lecture.add_argument("--limite", type=int, default=20)
    arguments = analyseur.parse_args()
    try:
        if arguments.commande == "initialiser":
            initialiser(arguments.base)
            resultat = {"statut": "JOURNAL_PRET"}
        elif arguments.commande == "enregistrer":
            resultat = enregistrer(
                arguments.base, arguments.controleur,
                sys.stdin.buffer.read(TAILLE_MAX + 1),
            )
        else:
            resultat = lire(arguments.base, arguments.limite)
    except EvenementInvalide:
        print('{"erreur":"EVENEMENT_INVALIDE"}', file=sys.stderr)
        return 2
    except ConflitEvenement:
        print('{"erreur":"CONFLIT_EVENEMENT"}', file=sys.stderr)
        return 3
    except (BaseIncompatible, sqlite3.Error, OSError):
        print('{"erreur":"STOCKAGE_INDISPONIBLE"}', file=sys.stderr)
        return 4
    print(json.dumps(resultat, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

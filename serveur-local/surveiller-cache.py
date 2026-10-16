#!/usr/bin/env python3
"""Surveillance du cache synchronisé; sortie simple pour systemd/journald."""
import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path

BASE = Path("/donnees/autorisations-synchronisees.sqlite3")
POLITIQUE = Path("/etc/controle-acces/politique-synchronisation.json")


def etat(age, alerte, limite):
    if age is None or age < 0:
        return "EXPIRE"
    if age >= limite:
        return "EXPIRE"
    if age >= alerte:
        return "RETARD"
    return "NORMAL"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--simuler-age-s", type=int,
                        help="Test sans modifier le fichier SQLite")
    args = parser.parse_args()
    politique = json.loads(POLITIQUE.read_text(encoding="utf-8"))
    alerte = politique["alerte_retard_s"]
    limite = politique["validite_cache_standard_s"]
    if not (isinstance(alerte, int) and isinstance(limite, int)
            and 0 < alerte < limite):
        raise ValueError("Seuils de surveillance incohérents")
    age = args.simuler_age_s
    if age is None:
        if BASE.exists():
            with sqlite3.connect(f"file:{BASE}?mode=ro", uri=True) as base:
                ligne = base.execute(
                    "SELECT instant_local FROM synchronisation WHERE id = 1"
                ).fetchone()
            age = int(time.time()) - int(ligne[0]) if ligne else None
        else:
            age = None
    statut = etat(age, alerte, limite)
    texte_age = "inconnu" if age is None else str(age)
    print(f"CACHE_{statut} age_s={texte_age} alerte_s={alerte} limite_s={limite}", flush=True)
    # Les retards/expirations ne sont pas des erreurs de programme :
    # journald reçoit un message clair sans faire échouer le timer.
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, sqlite3.Error) as erreur:
        print(f"SURVEILLANCE_ERREUR {erreur}", file=sys.stderr)
        sys.exit(1)

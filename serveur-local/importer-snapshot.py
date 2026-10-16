#!/usr/bin/env python3
"""Importation atomique d'un instantané fictif reçu sur stdin par SSH."""
import datetime as dt
import json
import sqlite3
import sys
import time

DB = "/donnees/autorisations-synchronisees.sqlite3"
MAX_BYTES = 2_000_000
CLOCK_SKEW_S = 60


def necessaire(condition, message):
    if not condition:
        raise ValueError(message)


def analyser_lignes(lignes, champs):
    necessaire(isinstance(lignes, list) and len(lignes) <= 10000, "tableau invalide")
    for ligne in lignes:
        necessaire(isinstance(ligne, dict) and set(ligne) == set(champs), "champs invalides")
    return lignes


def main():
    raw = sys.stdin.buffer.read(MAX_BYTES + 1)
    necessaire(0 < len(raw) <= MAX_BYTES, "instantané vide ou trop volumineux")
    paquet = json.loads(raw)
    necessaire(isinstance(paquet, dict) and paquet.get("schema_version") == 1,
               "version de schéma inconnue")
    instant = dt.datetime.fromisoformat(paquet["captured_at"].replace("Z", "+00:00"))
    necessaire(instant.tzinfo is not None, "horodatage sans fuseau")
    now = time.time()
    necessaire(abs(now - instant.timestamp()) <= CLOCK_SKEW_S,
               "écart d'horloge trop important")
    personnes = analyser_lignes(paquet["personnes"], ("id_personne", "actif"))
    identifiants = analyser_lignes(paquet["identifiants"], ("code", "id_personne", "actif"))
    portes = analyser_lignes(paquet["portes"], ("nom", "actif"))
    autorisations = analyser_lignes(
        paquet["autorisations"],
        ("id_personne", "nom_porte", "date_debut", "date_fin"),
    )

    # Validation complète avant de modifier quoi que ce soit.
    for ligne in personnes:
        necessaire(type(ligne["id_personne"]) is int and ligne["id_personne"] > 0
                   and type(ligne["actif"]) is bool, "personne invalide")
    for ligne in identifiants:
        necessaire(isinstance(ligne["code"], str) and 0 < len(ligne["code"]) <= 64
                   and type(ligne["id_personne"]) is int
                   and type(ligne["actif"]) is bool, "identifiant invalide")
    for ligne in portes:
        necessaire(isinstance(ligne["nom"], str) and 0 < len(ligne["nom"]) <= 100
                   and type(ligne["actif"]) is bool, "porte invalide")
    for ligne in autorisations:
        necessaire(type(ligne["id_personne"]) is int
                   and isinstance(ligne["nom_porte"], str), "autorisation invalide")
        for cle in ("date_debut", "date_fin"):
            valeur = ligne[cle]
            necessaire(valeur is None or isinstance(valeur, str), "date invalide")
            if valeur is not None:
                dat = dt.datetime.fromisoformat(valeur.replace("Z", "+00:00"))
                necessaire(dat.tzinfo is not None, "date sans fuseau")

    db = sqlite3.connect(DB, timeout=5)
    try:
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("BEGIN IMMEDIATE")
        db.executescript("""
            CREATE TABLE IF NOT EXISTS personnes
              (id_personne INTEGER PRIMARY KEY, actif INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS identifiants
              (code TEXT PRIMARY KEY, id_personne INTEGER NOT NULL, actif INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS portes
              (nom TEXT PRIMARY KEY, actif INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS autorisations
              (id_personne INTEGER NOT NULL, nom_porte TEXT NOT NULL,
               PRIMARY KEY (id_personne, nom_porte));
            CREATE TABLE IF NOT EXISTS synchronisation
              (id INTEGER PRIMARY KEY CHECK (id = 1),
               instant_central TEXT NOT NULL, instant_local INTEGER NOT NULL);
        """)
        # executescript() peut terminer une transaction implicite; en démarrer
        # une nouvelle avant la moindre suppression du contenu existant.
        cols = {row[1] for row in db.execute("PRAGMA table_info(autorisations)")}
        if "date_debut" not in cols:
            db.execute("ALTER TABLE autorisations ADD COLUMN date_debut TEXT")
        if "date_fin" not in cols:
            db.execute("ALTER TABLE autorisations ADD COLUMN date_fin TEXT")
        db.commit()
        db.execute("BEGIN IMMEDIATE")
        ancien = db.execute(
            "SELECT instant_central FROM synchronisation WHERE id=1"
        ).fetchone()
        if ancien is not None:
            necessaire(instant > dt.datetime.fromisoformat(
                ancien[0].replace("Z", "+00:00")), "instantané non plus récent")

        for table in ("autorisations", "identifiants", "portes", "personnes"):
            db.execute("DELETE FROM " + table)
        db.executemany("INSERT INTO personnes VALUES (?, ?)",
                       [(x["id_personne"], int(x["actif"])) for x in personnes])
        db.executemany("INSERT INTO identifiants VALUES (?, ?, ?)",
                       [(x["code"], x["id_personne"], int(x["actif"]))
                        for x in identifiants])
        db.executemany("INSERT INTO portes VALUES (?, ?)",
                       [(x["nom"], int(x["actif"])) for x in portes])
        db.executemany(
            "INSERT INTO autorisations "
            "(id_personne, nom_porte, date_debut, date_fin) VALUES (?, ?, ?, ?)",
            [(x["id_personne"], x["nom_porte"], x["date_debut"], x["date_fin"])
             for x in autorisations],
        )
        db.execute(
            "INSERT OR REPLACE INTO synchronisation VALUES (1, ?, ?)",
            (paquet["captured_at"], int(time.time())),
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    print("Synchronisation SQLite validée et enregistrée.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, TypeError, sqlite3.Error) as exc:
        print("Refus de synchronisation : " + str(exc), file=sys.stderr)
        sys.exit(1)

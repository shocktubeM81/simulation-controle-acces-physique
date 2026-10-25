#!/usr/bin/env python3
"""Lecture seule ISO14443-A, un seul jeton à la fois, UID 4 ou 7 octets."""
import argparse
from pathlib import Path
import subprocess
import time


def crc_a(octets):
    crc = 0x6363
    for octet in octets:
        crc ^= octet
        for _ in range(8):
            crc = (crc >> 1) ^ (0x8408 if crc & 1 else 0)
    return [crc & 255, crc >> 8]


def lire_uid(lecteur):
    # WUPA réveille aussi une carte mise en HALT lors du passage précédent.
    statut, _ = lecteur.MFRC522_Request(lecteur.PICC_REQALL)
    if statut != lecteur.MI_OK:
        return None
    lecteur.Write_MFRC522(lecteur.BitFramingReg, 0)
    uid = []
    for niveau in (0x93, 0x95):
        statut, bloc, bits = lecteur.MFRC522_ToCard(lecteur.PCD_TRANSCEIVE, [niveau, 0x20])
        if statut != lecteur.MI_OK or bits != 40 or len(bloc) != 5:
            raise ValueError("Anticollision invalide : présenter un seul jeton")
        if bloc[0] ^ bloc[1] ^ bloc[2] ^ bloc[3] != bloc[4]:
            raise ValueError("Contrôle BCC invalide")
        selection = [niveau, 0x70] + bloc
        statut, sak, bits = lecteur.MFRC522_ToCard(
            lecteur.PCD_TRANSCEIVE, selection + crc_a(selection))
        if (statut != lecteur.MI_OK or bits != 24 or len(sak) != 3
                or crc_a(sak[:1]) != sak[1:]):
            raise ValueError("Réponse de sélection invalide")
        suite = bool(sak[0] & 4)
        if suite:
            if niveau != 0x93 or bloc[0] != 0x88:
                raise ValueError("UID non pris en charge (4 ou 7 octets requis)")
            uid.extend(bloc[1:4])
        else:
            uid.extend(bloc[:4])
            # HALT ne renvoie normalement aucune réponse.
            halt = [0x50, 0]
            lecteur.MFRC522_ToCard(lecteur.PCD_TRANSCEIVE, halt + crc_a(halt))
            return ":".join(f"{octet:02X}" for octet in uid)
    raise ValueError("UID incomplet")


def verifier_acces(uid, porte, racine):
    commande = ["docker", "compose", "-f", str(racine / "compose.local.yaml"),
                "run", "--rm", "-T", "--no-deps", "cache-sqlite", "verifier-sync", uid, porte]
    try:
        resultat = subprocess.run(commande, cwd=racine, capture_output=True,
                                  text=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return "REFUSE (moteur indisponible)"
    # Le CLI existant renvoie aussi 0 lors d'un refus : exiger le texte exact.
    if resultat.returncode == 0 and resultat.stdout.strip() == "AUTORISE":
        return "AUTORISE"
    return "REFUSE"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--porte", help="Active la décision avec le cache synchronisé")
    parser.add_argument("--une-lecture", action="store_true")
    args = parser.parse_args()
    import RPi.GPIO as GPIO
    from mfrc522 import MFRC522
    lecteur = None
    try:
        lecteur = MFRC522(bus=0, device=0, pin_mode=GPIO.BOARD, pin_rst=22)
        print("Présente un seul badge ou jeton. Ctrl+C pour arrêter.", flush=True)
        precedent, dernier = None, 0
        while True:
            try:
                uid = lire_uid(lecteur)
            except ValueError as erreur:
                print(f"Lecture rejetée : {erreur}", flush=True)
                uid = None
            maintenant = time.monotonic()
            if uid:
                if uid != precedent or maintenant - dernier >= 2:
                    print(f"UID ({len(uid.split(':'))} octets) : {uid}", flush=True)
                    if args.porte:
                        racine = Path(__file__).resolve().parents[1]
                        print(verifier_acces(uid, args.porte, racine), flush=True)
                    else:
                        print("LECTURE CONFIRMEE (autorisation non vérifiée)", flush=True)
                    if args.une_lecture:
                        return
                precedent, dernier = uid, maintenant
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nTest terminé.")
    finally:
        if lecteur is not None:
            lecteur.spi.close()
        GPIO.cleanup(22)


if __name__ == "__main__":
    main()

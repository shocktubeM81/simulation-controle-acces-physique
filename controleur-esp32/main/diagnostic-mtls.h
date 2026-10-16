/* SPDX-License-Identifier: MIT */
#pragma once
#include <stdbool.h>

/* Diagnostic sans evenement: POST {} doit etre refuse avec HTTP 400.
 * Initialiser une fois depuis app_main. Aucun appel reseau dans actualiser.
 * Le resultat du test est journalise sur USB; ce n'est pas un etat de sante permanent. */
void diagnostic_mtls_initialiser(void);
void diagnostic_mtls_actualiser(bool reseau_et_heure_disponibles);

/* Uniquement depuis la tache du journal; confirme UUID et accuse du Pi. */
bool mtls_enregistrer(const char *identifiant, const char *message);

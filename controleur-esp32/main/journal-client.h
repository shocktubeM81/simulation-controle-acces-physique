/* SPDX-License-Identifier: MIT */
#pragma once
#include <stdbool.h>
/* API app_main seulement. File RAM bornee, perdue a toute coupure/reset. */
void journal_client_initialiser(void);
bool journal_client_ajouter_sortie(void);
bool journal_client_actualiser(bool reseau_et_heure_disponibles);
const char *journal_client_texte(void);
bool journal_client_erreur(void);

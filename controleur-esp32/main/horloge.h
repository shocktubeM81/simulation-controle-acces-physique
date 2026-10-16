/* SPDX-License-Identifier: MIT */
#pragma once
#include <stdbool.h>

/* Appeler depuis app_main seulement, apres reseau_initialiser().
 * Aucun delai d'attente reseau. Une date SNTP n'est pas une heure authentifiee.
 * Reinitialisation apres reconnexion; aucun etat de confiance TLS expose. */
bool horloge_actualiser(bool reseau_connecte);
const char *horloge_texte(void);
bool horloge_erreur(void);


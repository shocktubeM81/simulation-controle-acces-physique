/* SPDX-License-Identifier: MIT */
#pragma once

#include <stdbool.h>

/* BOOT/GPIO9 simule une demande interieure; aucune sortie physique n'est pilotee. */
void sortie_manuelle_initialiser(void);
/* Appeler regulierement depuis app_main. Retourne true si l'affichage doit changer. */
bool sortie_manuelle_actualiser(void);
bool sortie_manuelle_active(void);

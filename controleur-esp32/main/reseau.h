/* SPDX-License-Identifier: MIT */
#pragma once

#include <stdbool.h>

typedef struct {
    /* Association et configuration IP acquises; pas un etat du service du Pi. */
    bool connecte;
    char texte[80];
} EtatReseau;

/* Initialiser une seule fois. Sans fichier local, le test reste en mode LCD. */
void reseau_initialiser(void);
/* Lire le dernier etat sans bloquer; seul app_main met a jour LVGL. */
bool reseau_lire_etat(EtatReseau *etat);

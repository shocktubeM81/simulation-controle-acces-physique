/* SPDX-License-Identifier: MIT */
#pragma once
#include <stdbool.h>
typedef enum { USB_AUCUNE, USB_AUTORISE, USB_REFUSE, USB_ERREUR } DecisionUSB;
bool usb_initialiser(void);
bool usb_enregistrer(const char *id, const char *message);
/* Appelé par app_main, seul lecteur du port. */
DecisionUSB usb_actualiser(void);

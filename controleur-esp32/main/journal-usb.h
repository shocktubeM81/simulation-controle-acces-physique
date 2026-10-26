/* SPDX-License-Identifier: MIT */
#pragma once
#include <stdbool.h>
bool usb_initialiser(void);
bool usb_enregistrer(const char *id, const char *message);

/* SPDX-License-Identifier: MIT */
#if JOURNAL_USB_PRESENT
#include "journal-usb.h"
#include <stdio.h>
#include <string.h>
#include "driver/usb_serial_jtag.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

bool usb_initialiser(void)
{
    usb_serial_jtag_driver_config_t configuration = USB_SERIAL_JTAG_DRIVER_CONFIG_DEFAULT();
    configuration.tx_buffer_size = 512;
    configuration.rx_buffer_size = 256;
    return usb_serial_jtag_driver_install(&configuration) == ESP_OK;
}

/* Un seul appelant: la tache d'envoi de la file RAM. */
bool usb_enregistrer(const char *id, const char *message)
{
    char trame[256], attendu[48], ligne[80];
    size_t longueur = 0;
    bool trop_longue = false;
    int taille = snprintf(trame, sizeof(trame), "EVT %s\n", message);
    if (taille < 0 || (size_t)taille >= sizeof(trame)) return false;
    snprintf(attendu, sizeof(attendu), "ACK %s", id);
    /* Une nouvelle ligne permet de resynchroniser un recepteur apres un envoi coupe. */
    if (usb_serial_jtag_write_bytes("\n", 1, pdMS_TO_TICKS(100)) != 1 ||
        usb_serial_jtag_write_bytes(trame, taille, pdMS_TO_TICKS(1000)) != taille) return false;
    TickType_t debut = xTaskGetTickCount();
    while ((TickType_t)(xTaskGetTickCount() - debut) < pdMS_TO_TICKS(5000)) {
        char octet;
        if (usb_serial_jtag_read_bytes(&octet, 1, pdMS_TO_TICKS(100)) != 1) continue;
        if (octet == '\n') {
            ligne[longueur] = '\0';
            if (!trop_longue && strcmp(ligne, attendu) == 0) return true;
            longueur = 0;
            trop_longue = false;
        } else if (octet == '\0') {
            trop_longue = true;
        } else if (longueur < sizeof(ligne) - 1 && !trop_longue) {
            ligne[longueur++] = octet;
        } else {
            trop_longue = true;
        }
    }
    return false;
}
#endif

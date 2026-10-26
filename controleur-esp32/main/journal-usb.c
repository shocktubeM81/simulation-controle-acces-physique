/* SPDX-License-Identifier: MIT */
#if JOURNAL_USB_PRESENT
#include "journal-usb.h"
#include <stdio.h>
#include <string.h>
#include "driver/usb_serial_jtag.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"

static QueueHandle_t confirmations;

bool usb_initialiser(void)
{
    usb_serial_jtag_driver_config_t configuration = USB_SERIAL_JTAG_DRIVER_CONFIG_DEFAULT();
    configuration.tx_buffer_size = 512;
    configuration.rx_buffer_size = 256;
    confirmations = xQueueCreate(1, 37);
    if (confirmations == NULL) return false;
    if (usb_serial_jtag_driver_install(&configuration) == ESP_OK) return true;
    vQueueDelete(confirmations);
    confirmations = NULL;
    return false;
}

/* Seul app_main lit le port : ACK et affichage partagent le même décodeur. */
DecisionUSB usb_actualiser(void)
{
    static char ligne[80];
    static size_t longueur;
    static bool trop_longue;
    DecisionUSB decision = USB_AUCUNE;
    for (unsigned n = 0; n < 256; ++n) {
        char octet;
        if (usb_serial_jtag_read_bytes(&octet, 1, 0) != 1) break;
        if (octet == '\n') {
            ligne[longueur] = '\0';
            if (!trop_longue) {
                if (strlen(ligne) == 40 && strncmp(ligne, "ACK ", 4) == 0) {
                    if (confirmations != NULL) xQueueOverwrite(confirmations, ligne + 4);
                } else if (strcmp(ligne, "AFF AUTORISE") == 0) decision = USB_AUTORISE;
                else if (strcmp(ligne, "AFF REFUSE") == 0) decision = USB_REFUSE;
                else if (strcmp(ligne, "AFF ERREUR") == 0) decision = USB_ERREUR;
            }
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
    return decision;
}

/* La tâche de journal est le seul émetteur; app_main reçoit les ACK. */
bool usb_enregistrer(const char *id, const char *message)
{
    char trame[256], recu[37];
    if (confirmations == NULL) return false;
    while (xQueueReceive(confirmations, recu, 0) == pdTRUE) { }
    int taille = snprintf(trame, sizeof(trame), "EVT %s\n", message);
    if (taille < 0 || (size_t)taille >= sizeof(trame)) return false;
    if (usb_serial_jtag_write_bytes("\n", 1, pdMS_TO_TICKS(100)) != 1 ||
        usb_serial_jtag_write_bytes(trame, taille, pdMS_TO_TICKS(1000)) != taille) return false;
    TickType_t debut = xTaskGetTickCount();
    const TickType_t delai = pdMS_TO_TICKS(5000);
    for (;;) {
        TickType_t ecoule = (TickType_t)(xTaskGetTickCount() - debut);
        if (ecoule >= delai) return false;
        if (xQueueReceive(confirmations, recu, delai - ecoule) != pdTRUE) return false;
        if (strcmp(recu, id) == 0) return true;
    }
}
#endif

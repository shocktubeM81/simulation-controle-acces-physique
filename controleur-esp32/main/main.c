/*
 * SPDX-FileCopyrightText: 2021-2022 Espressif Systems (Shanghai) CO LTD
 *
 * SPDX-License-Identifier: CC0-1.0
 */

#include "ST7789.h"
#include "LVGL_Driver.h"
#include "reseau.h"
#include "horloge.h"
#include "journal-client.h"
#include "sortie-manuelle.h"

void app_main(void)
{
    LCD_Init();
    LVGL_Init();

    lv_obj_t *screen = lv_scr_act();
    lv_obj_set_style_bg_color(screen, lv_color_hex(0x102030), 0);
    lv_obj_set_style_bg_opa(screen, LV_OPA_COVER, 0);

    lv_obj_t *label = lv_label_create(screen);
    /* Garder 8 pixels de marge de chaque cote de l'ecran de 172 pixels. */
    lv_obj_set_width(label, EXAMPLE_LCD_H_RES - 16);
    lv_label_set_long_mode(label, LV_LABEL_LONG_WRAP);
    lv_label_set_text(label, "PRET\nBOOT: sortie\n\nESP32-C6");
    lv_obj_set_style_text_color(label, lv_color_hex(0xFFFFFF), 0);
    lv_obj_set_style_text_align(label, LV_TEXT_ALIGN_CENTER, 0);
    lv_obj_center(label);

    ESP_LOGI("LCD_TEST", "Test LCD actif, luminosite 50 %%");

    sortie_manuelle_initialiser();
#if !JOURNAL_USB_PRESENT
    reseau_initialiser();
#endif
    journal_client_initialiser();
#if JOURNAL_USB_PRESENT
    EtatReseau etat_courant = {.texte = "USB vers Raspberry Pi"};
#else
    EtatReseau etat_courant = {.texte = "ESP32-C6"};
#endif
    bool premier_affichage = true;

    while (1) {
        bool changement_sortie = sortie_manuelle_actualiser();
        bool rafraichir = changement_sortie || premier_affichage;
        premier_affichage = false;
        if (changement_sortie && sortie_manuelle_active()) {
            journal_client_ajouter_sortie();
        }
#if !JOURNAL_USB_PRESENT
        EtatReseau nouvel_etat;
        if (reseau_lire_etat(&nouvel_etat)) {
            etat_courant = nouvel_etat;
            rafraichir = true;
        }
        rafraichir = horloge_actualiser(etat_courant.connecte) || rafraichir;
#endif
        rafraichir = journal_client_actualiser(
#if JOURNAL_USB_PRESENT
            true) || rafraichir;
#else
            etat_courant.connecte && horloge_disponible()) || rafraichir;
#endif
        if (rafraichir) {
            const bool en_erreur = etat_courant.erreur ||
#if !JOURNAL_USB_PRESENT
                                   horloge_erreur() ||
#endif
                                   journal_client_erreur();
            const bool sortie_active = sortie_manuelle_active();
            /* L'erreur prime sur l'autorisation simulee; le repos reste neutre. */
            const uint32_t fond = en_erreur ? 0xF4A300
                : (sortie_active ? 0x006B32 : 0x102030);
            lv_obj_set_style_bg_color(screen, lv_color_hex(fond), 0);
            lv_obj_set_style_text_color(
                label, lv_color_hex(en_erreur ? 0x101010 : 0xFFFFFF), 0);
            const char *sortie = sortie_active
                ? "SORTIE AUTORISEE\nDEVERROUILLAGE\nSIMULE"
                : "PRET\nBOOT: sortie";
            lv_label_set_text_fmt(label, "%s\n\n%s\n\n%s\n\n%s",
                                  sortie, etat_courant.texte,
#if JOURNAL_USB_PRESENT
                                  "Sans Wi-Fi",
#else
                                  horloge_texte(),
#endif
                                  journal_client_texte());
            lv_obj_center(label);
        }
        lv_timer_handler();
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}



/*
 * SPDX-FileCopyrightText: 2021-2022 Espressif Systems (Shanghai) CO LTD
 *
 * SPDX-License-Identifier: CC0-1.0
 */

#include "ST7789.h"
#include "LVGL_Driver.h"
#include "reseau.h"

void app_main(void)
{
    LCD_Init();
    LVGL_Init();

    lv_obj_t *screen = lv_scr_act();
    lv_obj_set_style_bg_color(screen, lv_color_hex(0x102030), 0);
    lv_obj_set_style_bg_opa(screen, LV_OPA_COVER, 0);

    lv_obj_t *label = lv_label_create(screen);
    lv_label_set_text(label, "LCD OK\nESP32-C6");
    lv_obj_set_style_text_color(label, lv_color_hex(0xFFFFFF), 0);
    lv_obj_set_style_text_align(label, LV_TEXT_ALIGN_CENTER, 0);
    lv_obj_center(label);

    ESP_LOGI("LCD_TEST", "Test LCD actif, luminosite 50 %%");

    reseau_initialiser();

    while (1) {
        EtatReseau etat;
        if (reseau_lire_etat(&etat)) {
            lv_label_set_text_fmt(label, "LCD OK\n%s", etat.texte);
            lv_obj_center(label);
        }
        lv_timer_handler();
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

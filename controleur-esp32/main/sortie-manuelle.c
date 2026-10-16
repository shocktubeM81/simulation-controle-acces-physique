/* SPDX-License-Identifier: MIT */
#include "sortie-manuelle.h"

#include <stdint.h>
#include "driver/gpio.h"
#include "esp_err.h"
#include "esp_log.h"
#include "esp_timer.h"

#define BOUTON_SORTIE GPIO_NUM_9

static const char *TAG = "SORTIE";
static const int64_t anti_rebond_us = 40000;
static const int64_t duree_deverrouillage_us = 5000000;
static int niveau_brut;
static int niveau_stable;
static int64_t dernier_changement_us;
static int64_t fin_deverrouillage_us;
static bool bouton_arme;
static bool deverrouillage_actif;

void sortie_manuelle_initialiser(void)
{
    const gpio_config_t configuration = {
        .pin_bit_mask = 1ULL << BOUTON_SORTIE,
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    ESP_ERROR_CHECK(gpio_config(&configuration));
    niveau_brut = gpio_get_level(BOUTON_SORTIE);
    niveau_stable = niveau_brut;
    dernier_changement_us = esp_timer_get_time();
    fin_deverrouillage_us = 0;
    deverrouillage_actif = false;
    /* Un bouton deja maintenu au lancement doit etre relache avant tout appui. */
    bouton_arme = niveau_stable != 0;
    ESP_LOGI(TAG, "BOOT: demande de sortie simulee, duree 5 secondes");
}

bool sortie_manuelle_actualiser(void)
{
    const int64_t maintenant = esp_timer_get_time();
    const int niveau = gpio_get_level(BOUTON_SORTIE);
    bool changement = false;

    if (niveau != niveau_brut) {
        niveau_brut = niveau;
        dernier_changement_us = maintenant;
    }
    if (niveau_brut != niveau_stable &&
        maintenant - dernier_changement_us >= anti_rebond_us) {
        niveau_stable = niveau_brut;
        if (niveau_stable != 0) {
            bouton_arme = true;
        } else if (bouton_arme) {
            bouton_arme = false;
            deverrouillage_actif = true;
            /* Un nouvel appui distinct prolonge la simulation de cinq secondes. */
            fin_deverrouillage_us = maintenant + duree_deverrouillage_us;
            changement = true;
            ESP_LOGI(TAG, "Demande interieure: deverrouillage SIMULE pendant 5 secondes");
        }
    }
    if (deverrouillage_actif && maintenant >= fin_deverrouillage_us) {
        deverrouillage_actif = false;
        changement = true;
        ESP_LOGI(TAG, "Fin du deverrouillage SIMULE");
    }
    return changement;
}

bool sortie_manuelle_active(void)
{
    return deverrouillage_actif;
}

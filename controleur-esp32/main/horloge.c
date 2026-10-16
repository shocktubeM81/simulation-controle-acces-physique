/* SPDX-License-Identifier: MIT */
#include "horloge.h"

#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include "esp_log.h"
#include "esp_netif_sntp.h"
#include "esp_timer.h"

static const char *TAG = "HORLOGE";
static bool initialise;
static bool demarre;
static bool reseau_precedent;
static bool recue;
static bool erreur;
static int64_t attente_depuis;
static int64_t reception_depuis;
static char texte[64] = "Heure: attente Wi-Fi";

static bool afficher(const char *nouveau, bool en_erreur)
{
    bool change = erreur != en_erreur || strcmp(texte, nouveau) != 0;
    erreur = en_erreur;
    snprintf(texte, sizeof(texte), "%s", nouveau);
    return change;
}

const char *horloge_texte(void) { return texte; }
bool horloge_erreur(void) { return erreur; }

bool horloge_actualiser(bool reseau_connecte)
{
    if (!reseau_connecte) {
        reseau_precedent = false;
        recue = false;
        return afficher("Heure: attente Wi-Fi", false);
    }

    int64_t maintenant = esp_timer_get_time();
    if (!reseau_precedent) {
        esp_err_t resultat;
        if (!initialise) {
            esp_sntp_config_t configuration =
                ESP_NETIF_SNTP_DEFAULT_CONFIG("192.168.81.1");
            configuration.start = false;
            resultat = esp_netif_sntp_init(&configuration);
            if (resultat != ESP_OK) {
                /* Retenter au plus toutes les cinq secondes, sans bloquer BOOT. */
                reseau_precedent = true;
                attente_depuis = maintenant;
                ESP_LOGW(TAG, "Initialisation SNTP impossible: %s",
                         esp_err_to_name(resultat));
                return afficher("Heure: erreur SNTP", true);
            }
            initialise = true;
        }
        /* Une notification anterieure a la reconnexion ne valide pas ce test. */
        while (esp_netif_sntp_sync_wait(0) == ESP_OK) {}
        resultat = esp_netif_sntp_start();
        demarre = resultat == ESP_OK;
        reseau_precedent = true;
        attente_depuis = maintenant;
        recue = false;
        if (resultat != ESP_OK) {
            ESP_LOGW(TAG, "Demarrage SNTP impossible: %s",
                     esp_err_to_name(resultat));
            return afficher("Heure: erreur SNTP", true);
        }
        ESP_LOGI(TAG, "Attente SNTP depuis 192.168.81.1; heure non authentifiee");
        return afficher("Heure: synchronisation", false);
    }

    if (!initialise || !demarre) {
        if (maintenant - attente_depuis >= 5000000) {
            reseau_precedent = false;
        }
        return false;
    }

    esp_err_t resultat = esp_netif_sntp_sync_wait(0);
    if (resultat == ESP_OK) {
        time_t secondes = time(NULL);
        struct tm utc;
        /* Filtre de coherence uniquement; ceci n'authentifie pas l'heure. */
        if ((int64_t)secondes < 1704067200LL ||
            (int64_t)secondes >= 4102444800LL ||
            gmtime_r(&secondes, &utc) == NULL) {
            recue = false;
            return afficher("Heure: date incoherente", true);
        }
        char date[32];
        strftime(date, sizeof(date), "%Y-%m-%dT%H:%M:%SZ", &utc);
        ESP_LOGI(TAG, "Heure recue du Pi (SNTP): %s", date);
        recue = true;
        reception_depuis = maintenant;
        return afficher("Heure recue du Pi\nSNTP non authentifie", false);
    }
    if (resultat != ESP_ERR_TIMEOUT) {
        return afficher("Heure: erreur SNTP", true);
    }
    if ((!recue && maintenant - attente_depuis >= 30000000) ||
        (recue && maintenant - reception_depuis >= 21600000000LL)) {
        return afficher("Heure indisponible\nNouvel essai automatique", true);
    }
    return false;
}


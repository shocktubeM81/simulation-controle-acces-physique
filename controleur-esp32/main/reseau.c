/* SPDX-License-Identifier: MIT */
#include "reseau.h"

#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "esp_log.h"

#if WIFI_LOCAL_PRESENT
#include "configuration-wifi.locale.h"
#endif

static const char *TAG = "RESEAU";
static QueueHandle_t file_etats;

#if WIFI_LOCAL_PRESENT
static void publier_etat(const char *texte)
{
    EtatReseau etat = {0};
    snprintf(etat.texte, sizeof(etat.texte), "%s", texte);
    xQueueOverwrite(file_etats, &etat);
}
#endif

bool reseau_lire_etat(EtatReseau *etat)
{
    return file_etats != NULL &&
           xQueueReceive(file_etats, etat, 0) == pdTRUE;
}

#if WIFI_LOCAL_PRESENT
#include <string.h>
#include "esp_event.h"
#include "esp_netif.h"
#include "esp_wifi.h"
#include "esp_timer.h"
#include "nvs_flash.h"

/* Les etats ci-dessous sont modifies uniquement par la boucle d'evenements. */
ESP_EVENT_DEFINE_BASE(RESEAU_EVENEMENTS);
enum { RESEAU_RECONNECTER };
static esp_timer_handle_t minuterie_reconnexion;
static const uint64_t delai_reconnexion_us = 5000000;
static bool wifi_demarre;
static bool associe;
static bool connexion_en_cours;

static void annuler_reconnexion(void)
{
    esp_err_t resultat = esp_timer_stop(minuterie_reconnexion);
    if (resultat != ESP_ERR_INVALID_STATE) {
        ESP_ERROR_CHECK(resultat);
    }
}

static void planifier_reconnexion(void)
{
    annuler_reconnexion();
    publier_etat("Wi-Fi deconnecte\nNouvel essai: 5 s");
    ESP_LOGI(TAG, "Nouvelle tentative Wi-Fi dans 5 secondes");
    ESP_ERROR_CHECK(esp_timer_start_periodic(
        minuterie_reconnexion, delai_reconnexion_us));
}

static void reveiller_reconnexion(void *contexte)
{
    (void)contexte;
    /* Ne pas bloquer la tache esp_timer ni y manipuler l'etat du Wi-Fi. */
    esp_err_t resultat = esp_event_post(
        RESEAU_EVENEMENTS, RESEAU_RECONNECTER, NULL, 0, 0);
    if (resultat != ESP_OK) {
        ESP_LOGW(TAG, "Evenement de reconnexion differe: %s",
                 esp_err_to_name(resultat));
        /* La minuterie periodique reessaiera au prochain passage. */
    }
}

static void connecter(void)
{
    if (!wifi_demarre || associe || connexion_en_cours) {
        return;
    }
    publier_etat("Wi-Fi connexion...");
    esp_err_t resultat = esp_wifi_connect();
    if (resultat == ESP_OK) {
        connexion_en_cours = true;
    } else {
        ESP_LOGW(TAG, "Connexion impossible: %s", esp_err_to_name(resultat));
        planifier_reconnexion();
    }
}

static void evenement_reseau(void *contexte, esp_event_base_t base,
                             int32_t evenement, void *donnees)
{
    (void)contexte;
    if (base == RESEAU_EVENEMENTS && evenement == RESEAU_RECONNECTER) {
        connecter();
    } else if (base == WIFI_EVENT && evenement == WIFI_EVENT_STA_START) {
        wifi_demarre = true;
        connecter();
    } else if (base == WIFI_EVENT && evenement == WIFI_EVENT_STA_STOP) {
        wifi_demarre = false;
        associe = false;
        connexion_en_cours = false;
        annuler_reconnexion();
        publier_etat("Wi-Fi arrete");
    } else if (base == WIFI_EVENT && evenement == WIFI_EVENT_STA_CONNECTED) {
        associe = true;
        connexion_en_cours = false;
        annuler_reconnexion();
    } else if (base == WIFI_EVENT && evenement == WIFI_EVENT_STA_DISCONNECTED) {
        const wifi_event_sta_disconnected_t *rupture = donnees;
        associe = false;
        connexion_en_cours = false;
        ESP_LOGW(TAG, "Deconnexion Wi-Fi, raison=%u", (unsigned)rupture->reason);
        if (wifi_demarre) {
            planifier_reconnexion();
        }
    } else if (base == IP_EVENT && evenement == IP_EVENT_STA_GOT_IP) {
        const ip_event_got_ip_t *adresse = donnees;
        EtatReseau etat = {.connecte = true};
        snprintf(etat.texte, sizeof(etat.texte),
                 "Wi-Fi connecte\n" IPSTR, IP2STR(&adresse->ip_info.ip));
        xQueueOverwrite(file_etats, &etat);
        ESP_LOGI(TAG, "Wi-Fi connecte, IP=" IPSTR,
                 IP2STR(&adresse->ip_info.ip));
    }
}
#endif

void reseau_initialiser(void)
{
    file_etats = xQueueCreate(1, sizeof(EtatReseau));
    configASSERT(file_etats != NULL);

#if WIFI_LOCAL_PRESENT
    const char *ssid = CONTROLE_WIFI_SSID;
    const char *mot_de_passe = CONTROLE_WIFI_MOT_DE_PASSE;
    const size_t longueur_ssid = strlen(ssid);
    const size_t longueur_secret = strlen(mot_de_passe);
    if (longueur_ssid == 0 || longueur_ssid > 32 ||
        longueur_secret < 8 || longueur_secret > 63 ||
        strcmp(mot_de_passe, "REMPLACER_LOCALEMENT") == 0) {
        publier_etat("Wi-Fi non configure");
        ESP_LOGE(TAG, "Verifier la configuration locale, sans publier le secret");
        return;
    }

    /* Ne pas effacer automatiquement la NVS si son initialisation echoue. */
    ESP_ERROR_CHECK(nvs_flash_init());
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_t *interface = esp_netif_create_default_wifi_sta();
    configASSERT(interface != NULL);

    /* Le point d'acces du Pi ne fournit pas de DHCP. */
    esp_err_t resultat = esp_netif_dhcpc_stop(interface);
    if (resultat != ESP_ERR_ESP_NETIF_DHCP_ALREADY_STOPPED) {
        ESP_ERROR_CHECK(resultat);
    }
    esp_netif_ip_info_t adresse = {0};
    ESP_ERROR_CHECK(esp_netif_str_to_ip4("192.168.81.2", &adresse.ip));
    ESP_ERROR_CHECK(esp_netif_str_to_ip4("255.255.255.0", &adresse.netmask));
    ESP_ERROR_CHECK(esp_netif_str_to_ip4("192.168.81.1", &adresse.gw));
    ESP_ERROR_CHECK(esp_netif_set_ip_info(interface, &adresse));

    wifi_init_config_t initialisation = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&initialisation));
    ESP_ERROR_CHECK(esp_wifi_set_storage(WIFI_STORAGE_RAM));

    const esp_timer_create_args_t minuterie = {
        .callback = reveiller_reconnexion,
        .name = "reconnexion_wifi",
    };
    ESP_ERROR_CHECK(esp_timer_create(&minuterie, &minuterie_reconnexion));
    ESP_ERROR_CHECK(esp_event_handler_register(
        RESEAU_EVENEMENTS, RESEAU_RECONNECTER, evenement_reseau, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(
        WIFI_EVENT, ESP_EVENT_ANY_ID, evenement_reseau, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(
        IP_EVENT, IP_EVENT_STA_GOT_IP, evenement_reseau, NULL));

    wifi_config_t configuration = {0};
    memcpy(configuration.sta.ssid, ssid, longueur_ssid);
    memcpy(configuration.sta.password, mot_de_passe, longueur_secret);
    configuration.sta.scan_method = WIFI_ALL_CHANNEL_SCAN;
    configuration.sta.threshold.authmode = WIFI_AUTH_WPA2_PSK;
    configuration.sta.pmf_cfg.capable = true;
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &configuration));
    publier_etat("Wi-Fi connexion...");
    ESP_ERROR_CHECK(esp_wifi_start());
#else
    ESP_LOGI(TAG, "Mode LCD: fichier configuration-wifi.locale.h absent");
#endif
}

/* SPDX-License-Identifier: MIT */
#include "diagnostic-mtls.h"
#include "esp_log.h"

#if JOURNAL_MTLS_PRESENT
#include <stdint.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"
#include "freertos/task.h"
#include "esp_http_client.h"
#include "cJSON.h"

#if !CONFIG_MBEDTLS_HAVE_TIME_DATE
#error "La verification des dates des certificats doit rester active."
#endif
#if CONFIG_ESP_TLS_INSECURE || CONFIG_ESP_TLS_SKIP_SERVER_CERT_VERIFY
#error "Les options de contournement TLS doivent etre desactivees."
#endif

extern const char ca[] asm("_binary_journal_ca_start");
extern const char certificat[] asm("_binary_journal_client_start");
extern const char cle[] asm("_binary_journal_cle_start");

static EventGroupHandle_t conditions;
static const EventBits_t PRET = (1U << 0);
static bool etat_precedent;

typedef struct {
    char texte[256];
    size_t taille;
    bool depassement;
} ReponseDiagnostic;

static esp_err_t recevoir(esp_http_client_event_t *evenement)
{
    ReponseDiagnostic *reponse = evenement->user_data;
    if (evenement->event_id != HTTP_EVENT_ON_DATA) {
        return ESP_OK;
    }
    if (evenement->data_len < 0 || reponse->depassement ||
        (size_t)evenement->data_len >= sizeof(reponse->texte) - reponse->taille) {
        reponse->depassement = true;
        return ESP_FAIL;
    }
    memcpy(reponse->texte + reponse->taille, evenement->data, evenement->data_len);
    reponse->taille += evenement->data_len;
    reponse->texte[reponse->taille] = '\0';
    return ESP_OK;
}

static bool refus_attendu(int statut, const ReponseDiagnostic *reponse)
{
    if (statut != 400 || reponse->depassement || reponse->taille == 0 ||
        memchr(reponse->texte, '\0', reponse->taille) != NULL) {
        return false;
    }
    cJSON *objet = cJSON_ParseWithLengthOpts(
        reponse->texte, reponse->taille + 1, NULL, true);
    if (objet == NULL) {
        return false;
    }
    cJSON *erreur = cJSON_GetObjectItemCaseSensitive(objet, "erreur");
    const bool correct = cJSON_IsObject(objet) &&
        cJSON_GetArraySize(objet) == 1 && cJSON_IsString(erreur) &&
        strcmp(erreur->valuestring, "EVENEMENT_INVALIDE") == 0;
    cJSON_Delete(objet);
    return correct;
}

static bool accuse_attendu(int statut, const ReponseDiagnostic *reponse,
                           const char *identifiant)
{
    if ((statut != 200 && statut != 201) || reponse->depassement ||
        reponse->taille == 0 ||
        memchr(reponse->texte, '\0', reponse->taille) != NULL) {
        return false;
    }
    cJSON *objet = cJSON_ParseWithLengthOpts(
        reponse->texte, reponse->taille + 1, NULL, true);
    if (objet == NULL) return false;
    cJSON *etat = cJSON_GetObjectItemCaseSensitive(objet, "statut");
    cJSON *id = cJSON_GetObjectItemCaseSensitive(objet, "id_evenement");
    cJSON *date = cJSON_GetObjectItemCaseSensitive(objet, "recu_a_utc");
    bool correct = cJSON_IsObject(objet) && cJSON_GetArraySize(objet) == 3 &&
        cJSON_IsString(etat) && cJSON_IsString(id) && cJSON_IsString(date) &&
        strcmp(id->valuestring, identifiant) == 0 &&
        strcmp(etat->valuestring, statut == 201 ? "ENREGISTRE" : "DEJA_PRESENT") == 0 &&
        strlen(date->valuestring) == 24;
    if (correct) {
        const char *d = date->valuestring;
        for (int i = 0; i < 24; ++i) {
            char separateur = i == 4 || i == 7 ? '-' : i == 10 ? 'T' :
                i == 13 || i == 16 ? ':' : i == 19 ? '.' : i == 23 ? 'Z' : 0;
            if ((separateur && d[i] != separateur) ||
                (!separateur && (d[i] < '0' || d[i] > '9'))) correct = false;
        }
    }
    cJSON_Delete(objet);
    return correct;
}

static bool requete(const char *message, const char *identifiant)
{
    ReponseDiagnostic reponse = {0};
    const esp_http_client_config_t configuration = {
        .url = "https://192.168.81.1:8443/v1/evenements",
        .method = HTTP_METHOD_POST,
        .cert_pem = ca,
        .client_cert_pem = certificat,
        .client_key_pem = cle,
        .common_name = "192.168.81.1",
        .skip_cert_common_name_check = false,
        .disable_auto_redirect = true,
        .tls_version = ESP_HTTP_CLIENT_TLS_VER_TLS_1_2,
        .timeout_ms = 5000,
        .event_handler = recevoir,
        .user_data = &reponse,
    };
    esp_http_client_handle_t client = esp_http_client_init(&configuration);
    if (client == NULL) {
        ESP_LOGW("MTLS_TEST", "Client indisponible; aucun evenement envoye");
        return false;
    }
    esp_err_t resultat = esp_http_client_set_header(
        client, "Content-Type", "application/json");
    if (resultat == ESP_OK) {
        resultat = esp_http_client_set_post_field(client, message, strlen(message));
    }
    if (resultat == ESP_OK) {
        resultat = esp_http_client_perform(client);
    }
    int statut = esp_http_client_get_status_code(client);
    bool termine = esp_http_client_is_complete_data_received(client);
    bool correct = resultat == ESP_OK && termine &&
                   (identifiant == NULL ? refus_attendu(statut, &reponse)
                                       : accuse_attendu(statut, &reponse, identifiant));
    esp_http_client_cleanup(client);
    if (correct && identifiant == NULL) {
        ESP_LOGI("MTLS_TEST", "Diagnostic mTLS OK: HTTP 400 EVENEMENT_INVALIDE; aucun evenement cree");
    } else if (!correct) {
        /* Ne jamais reproduire le corps brut, les certificats ou la cle. */
        ESP_LOGW("MTLS_TEST", "Requete non confirmee: transport=%s, HTTP=%d",
                 esp_err_to_name(resultat), statut);
    }
    return correct;
}

static bool essayer(void) { return requete("{}", NULL); }

bool mtls_enregistrer(const char *identifiant, const char *message)
{
    return requete(message, identifiant);
}

static void tache_diagnostic(void *contexte)
{
    (void)contexte;
    for (;;) {
        xEventGroupWaitBits(conditions, PRET, pdFALSE, pdTRUE, portMAX_DELAY);
        if (essayer()) {
            vTaskDelete(NULL);
            return;
        }
        ESP_LOGW("MTLS_TEST", "Nouvel essai dans 10 secondes; BOOT reste local");
        vTaskDelay(pdMS_TO_TICKS(10000));
    }
}

void diagnostic_mtls_initialiser(void)
{
    conditions = xEventGroupCreate();
    if (conditions == NULL) {
        ESP_LOGE("MTLS_TEST", "Diagnostic desactive: memoire insuffisante");
        return;
    }
    if (xTaskCreate(tache_diagnostic, "test_mtls", 12288, NULL, 3, NULL) != pdPASS) {
        vEventGroupDelete(conditions);
        conditions = NULL;
        ESP_LOGE("MTLS_TEST", "Diagnostic desactive: tache indisponible");
    }
}

void diagnostic_mtls_actualiser(bool disponible)
{
    if (conditions != NULL && disponible != etat_precedent) {
        if (disponible) {
            xEventGroupSetBits(conditions, PRET);
        } else {
            xEventGroupClearBits(conditions, PRET);
        }
        etat_precedent = disponible;
    }
}
#else
bool mtls_enregistrer(const char *identifiant, const char *message)
{ (void)identifiant; (void)message; return false; }
void diagnostic_mtls_initialiser(void)
{
    ESP_LOGI("MTLS_TEST", "Diagnostic desactive: configuration locale absente");
}
void diagnostic_mtls_actualiser(bool disponible) { (void)disponible; }
#endif

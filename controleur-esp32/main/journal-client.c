/* SPDX-License-Identifier: MIT */
#include "journal-client.h"
#include <stdio.h>
#include <string.h>
#include "esp_log.h"

static bool perte;
static bool en_erreur;
static char texte[48] = "Journal: desactive";
const char *journal_client_texte(void) { return texte; }
bool journal_client_erreur(void) { return perte || en_erreur; }

#if JOURNAL_MTLS_PRESENT
#include "diagnostic-mtls.h"
#include "esp_random.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/event_groups.h"
#include "freertos/task.h"

#define CAPACITE 8
typedef struct { char id[37]; } Evenement;
typedef enum { ATTENTE, CONFIRME, ECHEC } EtatEnvoi;
static QueueHandle_t file;
static QueueHandle_t etats;
static EventGroupHandle_t conditions;
static bool pret_precedent;
static EtatEnvoi etat_courant = ATTENTE;
static const EventBits_t PRET = (1U << 0);

static void publier(EtatEnvoi etat) { xQueueOverwrite(etats, &etat); }

static void uuid_v4(char id[37])
{
    unsigned char b[16];
    esp_fill_random(b, sizeof(b));
    b[6] = (b[6] & 0x0f) | 0x40;
    b[8] = (b[8] & 0x3f) | 0x80;
    snprintf(id, 37,
        "%02x%02x%02x%02x-%02x%02x-%02x%02x-%02x%02x-%02x%02x%02x%02x%02x%02x",
        b[0], b[1], b[2], b[3], b[4], b[5], b[6], b[7],
        b[8], b[9], b[10], b[11], b[12], b[13], b[14], b[15]);
}

/* La tete reste dans la file pendant tous les essais et jusqu'a l'accuse valide. */
static bool traiter(const Evenement *evenement)
{
    char message[192];
    snprintf(message, sizeof(message),
        "{\"version\":1,\"id_evenement\":\"%s\",\"porte\":\"PORTE-01\","
        "\"type\":\"SORTIE_MANUELLE_SIMULEE\"}", evenement->id);
    if (!mtls_enregistrer(evenement->id, message)) {
        publier(ECHEC);
        ESP_LOGW("JOURNAL", "En attente de confirmation: %s; nouvel essai dans 10 s",
                 evenement->id);
        return false;
    }
    Evenement retire;
    if (xQueueReceive(file, &retire, 0) != pdTRUE ||
        strcmp(retire.id, evenement->id) != 0) {
        publier(ECHEC);
        ESP_LOGE("JOURNAL", "Erreur interne de file RAM");
        return false;
    }
    ESP_LOGI("JOURNAL", "Enregistrement confirme par le Pi: %s", evenement->id);
    publier(CONFIRME);
    return true;
}

static void envoyer(void *contexte)
{
    (void)contexte;
    for (;;) {
        Evenement evenement;
        if (xQueuePeek(file, &evenement, portMAX_DELAY) != pdTRUE) continue;
        xEventGroupWaitBits(conditions, PRET, pdFALSE, pdTRUE, portMAX_DELAY);
        if (!traiter(&evenement)) vTaskDelay(pdMS_TO_TICKS(10000));
    }
}

void journal_client_initialiser(void)
{
    file = xQueueCreate(CAPACITE, sizeof(Evenement));
    etats = xQueueCreate(1, sizeof(EtatEnvoi));
    conditions = xEventGroupCreate();
    if (file == NULL || etats == NULL || conditions == NULL ||
        xTaskCreate(envoyer, "journal_mtls", 12288, NULL, 1, NULL) != pdPASS) {
        if (file != NULL) vQueueDelete(file);
        if (etats != NULL) vQueueDelete(etats);
        if (conditions != NULL) vEventGroupDelete(conditions);
        file = NULL; etats = NULL; conditions = NULL;
        en_erreur = true;
        snprintf(texte, sizeof(texte), "Journal: erreur RAM");
        ESP_LOGE("JOURNAL", "Initialisation impossible; BOOT reste une simulation locale");
        return;
    }
    snprintf(texte, sizeof(texte), "Journal: pret");
}

bool journal_client_ajouter_sortie(void)
{
    if (file == NULL) {
        perte = true;
        ESP_LOGE("JOURNAL", "Evenement perdu: journal indisponible");
        return false;
    }
    Evenement evenement;
    uuid_v4(evenement.id);
    if (xQueueSend(file, &evenement, 0) != pdTRUE) {
        /* Conserver tous les anciens; refuser le nouveau sans bloquer BOOT. */
        perte = true;
        ESP_LOGE("JOURNAL", "Evenement perdu: file RAM pleine (8)");
        return false;
    }
    ESP_LOGI("JOURNAL", "Sortie simulee en file RAM: %s", evenement.id);
    return true;
}

bool journal_client_actualiser(bool pret)
{
    char precedent[sizeof(texte)];
    memcpy(precedent, texte, sizeof(texte));
    bool ancienne_erreur = journal_client_erreur();
    if (conditions != NULL && pret != pret_precedent) {
        if (pret) xEventGroupSetBits(conditions, PRET);
        else xEventGroupClearBits(conditions, PRET);
        pret_precedent = pret;
    }
    if (file != NULL) {
        EtatEnvoi nouveau;
        if (xQueueReceive(etats, &nouveau, 0) == pdTRUE) etat_courant = nouveau;
        unsigned attente = (unsigned)uxQueueMessagesWaiting(file);
        en_erreur = etat_courant == ECHEC && attente > 0;
        if (perte) snprintf(texte, sizeof(texte), "Journal: PERTE RAM");
        else if (en_erreur) snprintf(texte, sizeof(texte), "Journal: erreur\n%u en attente", attente);
        else if (attente) snprintf(texte, sizeof(texte), "Journal: %u attente", attente);
        else snprintf(texte, sizeof(texte), "%s",
            etat_courant == CONFIRME ? "Journal: confirme" : "Journal: pret");
    } else if (perte) {
        snprintf(texte, sizeof(texte), "Journal: PERTE RAM");
    }
    return ancienne_erreur != journal_client_erreur() || strcmp(precedent, texte) != 0;
}
#else
void journal_client_initialiser(void) { }
bool journal_client_ajouter_sortie(void) { return false; }
bool journal_client_actualiser(bool pret) { (void)pret; return false; }
#endif

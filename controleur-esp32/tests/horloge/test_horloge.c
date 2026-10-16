#include <assert.h>
#include <stdarg.h>
#include <string.h>
#include <time.h>
#define time test_time
time_t test_time(time_t *);
struct tm *gmtime_r(const time_t *, struct tm *);
#include "../../main/horloge.c"

static int init_resultat, start_resultat, init_appels, start_appels, notifications;
static int64_t mono;
static time_t date = 1792185600;
void test_log(const char *a,const char *b,...) {(void)a;(void)b;}
const char *esp_err_to_name(int code) {(void)code;return "TEST";}
int64_t esp_timer_get_time(void) {return mono;}
time_t test_time(time_t *t) {if(t)*t=date;return date;}
struct tm *gmtime_r(const time_t *t,struct tm *out) {
    (void)t; memset(out,0,sizeof(*out));out->tm_year=126;out->tm_mon=9;out->tm_mday=16;return out;
}
esp_err_t esp_netif_sntp_init(const esp_sntp_config_t *c) {
    assert(!c->start && c->wait_for_sync);
    assert(strcmp(c->server,"192.168.81.1")==0);++init_appels;return init_resultat;
}
esp_err_t esp_netif_sntp_start(void) {++start_appels;return start_resultat;}
esp_err_t esp_netif_sntp_sync_wait(int attente) {
    assert(attente==0);if(notifications){--notifications;return ESP_OK;}return ESP_ERR_TIMEOUT;
}
static void reset(void) {
    initialise=demarre=reseau_precedent=recue=erreur=false;
    attente_depuis=reception_depuis=mono=0;
    init_resultat=start_resultat=init_appels=start_appels=notifications=0;
    strcpy(texte,"Heure: attente Wi-Fi");date=1792185600;
}
int main(void) {
    reset();
    assert(!horloge_actualiser(false)); assert(init_appels==0);
    assert(horloge_actualiser(true)); assert(init_appels==1 && start_appels==1);
    for(int i=0;i<10000;i++) assert(!horloge_actualiser(true));
    assert(!horloge_erreur());
    mono=30000000; assert(horloge_actualiser(true));assert(horloge_erreur());
    notifications=1; assert(horloge_actualiser(true));assert(recue && !horloge_erreur());
    mono+=21600000000LL; assert(horloge_actualiser(true));assert(horloge_erreur());
    notifications=1; assert(horloge_actualiser(true));assert(!horloge_erreur());
    assert(horloge_actualiser(false)); assert(!recue);
    notifications=1;assert(horloge_actualiser(true));assert(!recue && notifications==0);
    assert(init_appels==1 && start_appels==2);
    notifications=1;assert(horloge_actualiser(true));assert(recue);
    date=0; notifications=1;assert(horloge_actualiser(true));assert(!recue && horloge_erreur());
    reset();init_resultat=ESP_FAIL;assert(horloge_actualiser(true));assert(horloge_erreur());
    for(int i=0;i<10000;i++)horloge_actualiser(true);
    assert(init_appels==1);
    mono=5000000;horloge_actualiser(true);init_resultat=ESP_OK;horloge_actualiser(true);
    assert(init_appels==2 && start_appels==1);
    reset();start_resultat=ESP_FAIL;horloge_actualiser(true);assert(horloge_erreur());
    mono=5000000;horloge_actualiser(true);start_resultat=ESP_OK;horloge_actualiser(true);
    assert(init_appels==1 && start_appels==2);
    puts("OK: attente, notification, delai, reprise, reconnexion, date incoherente, erreurs API");
    return 0;
}


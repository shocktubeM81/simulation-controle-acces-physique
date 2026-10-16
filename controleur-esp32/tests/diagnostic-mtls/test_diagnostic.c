#include <assert.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include "../../main/diagnostic-mtls.c"

const char ca[]="CA_TEST";
const char certificat[]="CERT_TEST";
const char cle[]="CLE_TEST";
static const esp_http_client_config_t *conf;
static const char *body="{\"erreur\":\"EVENEMENT_INVALIDE\"}";
static int http=400, transport, cleanups, calls;
static bool complete=true;
static unsigned bits;
void test_log(const char*a,const char*b,...) {(void)a;(void)b;}
const char *esp_err_to_name(int c){(void)c;return "TEST";}
void *xEventGroupCreate(void){return &bits;}
void vEventGroupDelete(void*a){(void)a;}
unsigned xEventGroupSetBits(void*a,unsigned b){(void)a;return bits|=b;}
unsigned xEventGroupClearBits(void*a,unsigned b){(void)a;return bits&=~b;}
unsigned xEventGroupWaitBits(void*a,unsigned b,int c,int d,unsigned e){
(void)a;(void)b;(void)c;(void)d;(void)e;return bits;
}
int xTaskCreate(void(*f)(void*),const char*n,unsigned s,void*a,unsigned p,void*h){
(void)f;(void)n;(void)s;(void)a;(void)p;(void)h;return 1;
}
void vTaskDelete(void*a){(void)a;}
void vTaskDelay(unsigned n){(void)n;}
void *esp_http_client_init(const esp_http_client_config_t *c){
 assert(strcmp(c->url,"https://192.168.81.1:8443/v1/evenements")==0);
 assert(strcmp(c->common_name,"192.168.81.1")==0);
 assert(!c->skip_cert_common_name_check && c->disable_auto_redirect);
 assert(c->cert_pem==ca && c->client_cert_pem==certificat && c->client_key_pem==cle);
 assert(c->tls_version==ESP_HTTP_CLIENT_TLS_VER_TLS_1_2 && c->timeout_ms==5000);
 conf=c;return &bits;
}
int esp_http_client_set_header(void*h,const char*k,const char*v){
(void)h;assert(!strcmp(k,"Content-Type")&&!strcmp(v,"application/json"));return ESP_OK;
}
int esp_http_client_set_post_field(void*h,const char*d,int n){
(void)h;assert(n==(int)strlen(d));return ESP_OK;
}
int esp_http_client_perform(void*h){
(void)h;++calls;
size_t n=strlen(body), demi=n/2;
esp_http_client_event_t e={.event_id=HTTP_EVENT_ON_DATA,.user_data=conf->user_data,
.data=(void*)body,.data_len=(int)demi};
conf->event_handler(&e);e.data=(void*)(body+demi);e.data_len=(int)(n-demi);
conf->event_handler(&e);return transport;
}
int esp_http_client_get_status_code(void*h){(void)h;return http;}
bool esp_http_client_is_complete_data_received(void*h){(void)h;return complete;}
int esp_http_client_cleanup(void*h){(void)h;++cleanups;return ESP_OK;}
int main(void){
 diagnostic_mtls_initialiser();
 assert(calls==0 && bits==0);
 diagnostic_mtls_actualiser(false);assert(bits==0 && calls==0);
 diagnostic_mtls_actualiser(true);assert(bits==PRET && calls==0);
 diagnostic_mtls_actualiser(false);assert(bits==0 && calls==0);
 assert(essayer());
 http=403;assert(!essayer());http=201;assert(!essayer());http=302;assert(!essayer());
 http=400;transport=ESP_FAIL;assert(!essayer());transport=ESP_OK;
 complete=false;assert(!essayer());complete=true;
 const char *incorrects[]={
 "{\"erreur\":\"AUTRE\"}","{\"erreur\":true}","[]","{}","invalide",
 "{\"erreur\":\"EVENEMENT_INVALIDE\",\"erreur\":\"EVENEMENT_INVALIDE\"}",
 "{\"erreur\":\"EVENEMENT_INVALIDE\"}reste"};
 for(unsigned i=0;i<sizeof(incorrects)/sizeof(*incorrects);++i){body=incorrects[i];assert(!essayer());}
 char grand[300];memset(grand,'x',sizeof(grand)-1);grand[299]=0;body=grand;assert(!essayer());
 ReponseDiagnostic r={.texte="{\"erreur\":\"EVENEMENT_INVALIDE\"}\0reste",.taille=40};
 assert(!refus_attendu(400,&r));
 const char *id="a4c71422-e011-4ca7-b140-14310bec83f5";
 body="{\"statut\":\"ENREGISTRE\",\"id_evenement\":\"a4c71422-e011-4ca7-b140-14310bec83f5\",\"recu_a_utc\":\"2026-10-16T21:13:50.241Z\"}";
 http=201; assert(mtls_enregistrer(id,"{}"));
 http=200; assert(!mtls_enregistrer(id,"{}"));
 body="{\"statut\":\"DEJA_PRESENT\",\"id_evenement\":\"a4c71422-e011-4ca7-b140-14310bec83f5\",\"recu_a_utc\":\"2026-10-16T21:13:50.241Z\"}";
 assert(mtls_enregistrer(id,"{}"));
 assert(!mtls_enregistrer("autre-id","{}"));
 body="{\"statut\":\"DEJA_PRESENT\",\"id_evenement\":\"a4c71422-e011-4ca7-b140-14310bec83f5\",\"recu_a_utc\":\"invalide\"}";
 assert(!mtls_enregistrer(id,"{}"));
 body="{\"statut\":\"DEJA_PRESENT\",\"id_evenement\":\"a4c71422-e011-4ca7-b140-14310bec83f5\",\"recu_a_utc\":\"2026-10-16T21:13:50.241Z\",\"extra\":1}";
 assert(!mtls_enregistrer(id,"{}"));
 http=403;assert(!mtls_enregistrer(id,"{}"));
 http=409;assert(!mtls_enregistrer(id,"{}"));
 assert(cleanups==calls);
 puts("OK: TLS configure, requete vide, reponse fragmentee, refus HTTP, JSON, taille, nettoyage, depart differe");
 return 0;
}


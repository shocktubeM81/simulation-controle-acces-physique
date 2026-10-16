#include <assert.h>
#include <stdarg.h>
#include <stdlib.h>
#include "../../main/journal-client.c"
typedef struct {unsigned taille,capacite,n;unsigned char donnees[8][64];} Queue;
static unsigned bits, essais, prochain;
static bool accuse;
static char premier_message[192];
void test_log(const char*a,const char*b,...) {(void)a;(void)b;}
void *xQueueCreate(unsigned n,unsigned taille){
 Queue*q=calloc(1,sizeof(*q));q->capacite=n;q->taille=taille;return q;
}
void vQueueDelete(void*p){free(p);}
int xQueueSend(void*p,const void*d,unsigned t){
 (void)t;Queue*q=p;if(q->n==q->capacite)return 0;
 memcpy(q->donnees[q->n++],d,q->taille);return 1;
}
int xQueuePeek(void*p,void*d,unsigned t){
 (void)t;Queue*q=p;if(!q->n)return 0;memcpy(d,q->donnees[0],q->taille);return 1;
}
int xQueueReceive(void*p,void*d,unsigned t){
 Queue*q=p;if(!xQueuePeek(p,d,t))return 0;
 --q->n;memmove(q->donnees,q->donnees+1,q->n*sizeof(q->donnees[0]));return 1;
}
int xQueueOverwrite(void*p,const void*d){
 Queue*q=p;q->n=1;memcpy(q->donnees[0],d,q->taille);return 1;
}
unsigned uxQueueMessagesWaiting(void*p){return ((Queue*)p)->n;}
void *xEventGroupCreate(void){return &bits;}
void vEventGroupDelete(void*p){(void)p;}
unsigned xEventGroupSetBits(void*p,unsigned b){(void)p;return bits|=b;}
unsigned xEventGroupClearBits(void*p,unsigned b){(void)p;return bits&=~b;}
unsigned xEventGroupWaitBits(void*p,unsigned b,int c,int d,unsigned t){
(void)p;(void)b;(void)c;(void)d;(void)t;return bits;
}
int xTaskCreate(void(*f)(void*),const char*n,unsigned s,void*a,unsigned p,void*h){
(void)f;(void)n;(void)s;(void)a;(void)p;(void)h;return 1;
}
void vTaskDelete(void*p){(void)p;}
void vTaskDelay(unsigned t){(void)t;}
void esp_fill_random(void*p,size_t n){
 unsigned char*b=p;for(size_t i=0;i<n;i++)b[i]=(unsigned char)(prochain+i);prochain++;
}
bool mtls_enregistrer(const char*id,const char*message){
 assert(strstr(message,id)!=NULL && strstr(message,"SORTIE_MANUELLE_SIMULEE")!=NULL);
 if(!essais)strcpy(premier_message,message);
 else if(essais<3)assert(strcmp(premier_message,message)==0);
 essais++;return accuse;
}
int main(void){
 journal_client_initialiser();assert(uxQueueMessagesWaiting(file)==0);
 char ids[8][37];
 for(unsigned i=0;i<8;i++){
  assert(journal_client_ajouter_sortie());
  Queue*q=file;Evenement e;memcpy(&e,q->donnees[i],sizeof(e));
  assert(strlen(e.id)==36 && e.id[14]=='4' && strchr("89ab",e.id[19]));
  strcpy(ids[i],e.id);if(i)assert(strcmp(ids[i-1],ids[i])!=0);
 }
 assert(!journal_client_ajouter_sortie());assert(uxQueueMessagesWaiting(file)==8);
 journal_client_actualiser(false);assert(journal_client_erreur());
 assert(strstr(journal_client_texte(),"PERTE"));
 assert(essais==0 && bits==0);
 journal_client_actualiser(true);assert(bits==PRET && essais==0);
 journal_client_actualiser(false);assert(bits==0);
 Evenement e;assert(xQueuePeek(file,&e,0));
 assert(!traiter(&e));assert(uxQueueMessagesWaiting(file)==8);
 assert(!traiter(&e));assert(uxQueueMessagesWaiting(file)==8);
 accuse=true;assert(traiter(&e));assert(uxQueueMessagesWaiting(file)==7);
 for(unsigned i=1;i<8;i++){
  assert(xQueuePeek(file,&e,0));assert(strcmp(e.id,ids[i])==0);assert(traiter(&e));
 }
 assert(uxQueueMessagesWaiting(file)==0);
 journal_client_actualiser(true);assert(journal_client_erreur());
 assert(strstr(journal_client_texte(),"PERTE"));
 vQueueDelete(file);vQueueDelete(etats);
 puts("OK: FIFO huit places, refus debordement, UUID, retransmission identique, retrait apres accuse, perte visible");
 return 0;
}


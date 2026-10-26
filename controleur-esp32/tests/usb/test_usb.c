#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "journal-usb.h"
#include "driver/usb_serial_jtag.h"
static const char *reponse;
static TickType_t instant;
static int echec_ecriture;
static char sortie[1024];
static size_t longueur;
TickType_t xTaskGetTickCount(void) { return instant; }
int usb_serial_jtag_driver_install(usb_serial_jtag_driver_config_t *c) {
    assert(c->rx_buffer_size >= 80 && c->tx_buffer_size >= 256);
    return ESP_OK;
}
int usb_serial_jtag_write_bytes(const void *s, size_t n, TickType_t delai) {
    (void)delai;
    if (echec_ecriture) return 0;
    assert(longueur + n < sizeof(sortie));
    memcpy(sortie + longueur, s, n);
    longueur += n; sortie[longueur] = 0;
    return (int)n;
}
int usb_serial_jtag_read_bytes(void *s, uint32_t n, TickType_t delai) {
    assert(n == 1);
    if (*reponse) { *(char*)s = *reponse++; instant++; return 1; }
    instant += delai;
    return 0;
}
static bool essayer(const char *recu) {
    reponse = recu; instant = 0; longueur = 0;
    return usb_enregistrer("12345678-1234-4234-8234-123456789abc", "{\"version\":1}");
}
int main(void) {
    assert(usb_initialiser());
    assert(essayer("ACK 12345678-1234-4234-8234-123456789abc\n"));
    assert(strcmp(sortie, "\nEVT {\"version\":1}\n") == 0);
    assert(!essayer("ACK 12345678-1234-4234-8234-123456789abd\n"));
    assert(!essayer("ACK 12345678-1234-4234-8234-123456789abc"));
    assert(!essayer(""));
    assert(essayer("bruit\nACK 12345678-1234-4234-8234-123456789abc\n"));
    assert(!essayer("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXACK 12345678-1234-4234-8234-123456789abc\n"));
    assert(essayer("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX\nACK 12345678-1234-4234-8234-123456789abc\n"));
    echec_ecriture = 1;
    assert(!essayer("ACK 12345678-1234-4234-8234-123456789abc\n"));
    puts("OK : ACK exact, erreurs, fragmentation, delai et resynchronisation");
    return 0;
}

#pragma once
#include <stdbool.h>
typedef int esp_err_t;
#define ESP_OK 0
#define ESP_ERR_TIMEOUT 1
#define ESP_FAIL 2
typedef struct {bool start; bool wait_for_sync; const char *server;} esp_sntp_config_t;
#define ESP_NETIF_SNTP_DEFAULT_CONFIG(s) {.start=true,.wait_for_sync=true,.server=s}
esp_err_t esp_netif_sntp_init(const esp_sntp_config_t *);
esp_err_t esp_netif_sntp_start(void);
esp_err_t esp_netif_sntp_sync_wait(int);
const char *esp_err_to_name(int);


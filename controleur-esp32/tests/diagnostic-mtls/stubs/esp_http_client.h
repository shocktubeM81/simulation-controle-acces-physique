#pragma once
#include <stdbool.h>
typedef int esp_err_t;
#define ESP_OK 0
#define ESP_FAIL -1
#define HTTP_EVENT_ON_DATA 1
#define HTTP_METHOD_POST 1
#define ESP_HTTP_CLIENT_TLS_VER_TLS_1_2 1
typedef struct {int event_id; void *user_data; void *data; int data_len;} esp_http_client_event_t;
typedef struct {
 const char *url,*cert_pem,*client_cert_pem,*client_key_pem,*common_name;
 int method,tls_version,timeout_ms;
 bool skip_cert_common_name_check,disable_auto_redirect;
 esp_err_t (*event_handler)(esp_http_client_event_t *);
 void *user_data;
} esp_http_client_config_t;
typedef void *esp_http_client_handle_t;
esp_http_client_handle_t esp_http_client_init(const esp_http_client_config_t *);
esp_err_t esp_http_client_set_header(void*,const char*,const char*);
esp_err_t esp_http_client_set_post_field(void*,const char*,int);
esp_err_t esp_http_client_perform(void*);
int esp_http_client_get_status_code(void*);
bool esp_http_client_is_complete_data_received(void*);
esp_err_t esp_http_client_cleanup(void*);
const char *esp_err_to_name(int);


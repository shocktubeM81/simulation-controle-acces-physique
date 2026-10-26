#pragma once
#include <stddef.h>
#include "freertos/FreeRTOS.h"
typedef struct { uint32_t tx_buffer_size; uint32_t rx_buffer_size; } usb_serial_jtag_driver_config_t;
#define USB_SERIAL_JTAG_DRIVER_CONFIG_DEFAULT() ((usb_serial_jtag_driver_config_t){256,256})
#define ESP_OK 0
int usb_serial_jtag_driver_install(usb_serial_jtag_driver_config_t*);
int usb_serial_jtag_write_bytes(const void*, size_t, TickType_t);
int usb_serial_jtag_read_bytes(void*, uint32_t, TickType_t);

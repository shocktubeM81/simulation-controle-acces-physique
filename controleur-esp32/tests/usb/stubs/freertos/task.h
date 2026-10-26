#pragma once
#include "FreeRTOS.h"
TickType_t xTaskGetTickCount(void);
int xTaskCreate(void (*)(void*), const char*, unsigned, void*, unsigned, void*);
void vTaskDelay(unsigned);

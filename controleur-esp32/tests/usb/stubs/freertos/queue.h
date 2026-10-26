#pragma once
#include <stddef.h>
typedef void *QueueHandle_t;
QueueHandle_t xQueueCreate(unsigned, unsigned);
void vQueueDelete(QueueHandle_t);
int xQueueSend(QueueHandle_t,const void*,unsigned);
int xQueueReceive(QueueHandle_t,void*,unsigned);
int xQueuePeek(QueueHandle_t,void*,unsigned);
int xQueueOverwrite(QueueHandle_t,const void*);
unsigned uxQueueMessagesWaiting(QueueHandle_t);


idf_component_register(
    SRCS
        "main.c"
        "reseau.c"
        "LCD_Driver/Vernon_ST7789T/Vernon_ST7789T.c"
        "LCD_Driver/ST7789.c"
        "LVGL_Driver/LVGL_Driver.c"
    INCLUDE_DIRS
        "."
        "LCD_Driver"
        "LCD_Driver/Vernon_ST7789T"
        "LVGL_Driver"
)

# Le mode LCD reste compilable sans identifiants. Reconfigurer apres ajout/retrait.
if(EXISTS "${CMAKE_CURRENT_LIST_DIR}/configuration-wifi.locale.h")
    target_compile_definitions(${COMPONENT_LIB} PRIVATE WIFI_LOCAL_PRESENT=1)
else()
    target_compile_definitions(${COMPONENT_LIB} PRIVATE WIFI_LOCAL_PRESENT=0)
endif()

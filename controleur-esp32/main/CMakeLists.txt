idf_component_register(
    SRCS
        "main.c"
        "reseau.c"
        "horloge.c"
        "diagnostic-mtls.c"
        "sortie-manuelle.c"
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


# Activation volontaire; aucune cle ne doit etre copiee dans les sources.
set(CONTROLE_JOURNAL_MTLS OFF)
include("${CMAKE_CURRENT_LIST_DIR}/configuration-journal.locale.cmake" OPTIONAL)
if(CONTROLE_JOURNAL_MTLS)
    if(NOT EXISTS "${CMAKE_CURRENT_LIST_DIR}/configuration-wifi.locale.h")
        message(FATAL_ERROR "Le diagnostic mTLS requiert la configuration Wi-Fi locale.")
    endif()
    set(journal_pki "${CMAKE_CURRENT_LIST_DIR}/../../secrets/journal-pki/esp32")
    foreach(nom ca.cert.pem controleur.cert.pem controleur.cle.pem)
        if(NOT EXISTS "${journal_pki}/${nom}" OR IS_DIRECTORY "${journal_pki}/${nom}")
            message(FATAL_ERROR "Fichier PKI local manquant: ${nom}")
        endif()
    endforeach()
    target_compile_definitions(${COMPONENT_LIB} PRIVATE JOURNAL_MTLS_PRESENT=1)
    target_add_binary_data(${COMPONENT_LIB} "${journal_pki}/ca.cert.pem" TEXT RENAME_TO journal_ca)
    target_add_binary_data(${COMPONENT_LIB} "${journal_pki}/controleur.cert.pem" TEXT RENAME_TO journal_client)
    target_add_binary_data(${COMPONENT_LIB} "${journal_pki}/controleur.cle.pem" TEXT RENAME_TO journal_cle)
else()
    target_compile_definitions(${COMPONENT_LIB} PRIVATE JOURNAL_MTLS_PRESENT=0)
endif()

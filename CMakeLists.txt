cmake_minimum_required(VERSION 3.20)

project(simulation_controle_acces
    VERSION 0.1.0
    LANGUAGES CXX
)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(serveur-central serveur-central/principal.cpp)
add_executable(serveur-local serveur-local/principal.cpp)

foreach(cible serveur-central serveur-local)
    target_compile_options(${cible} PRIVATE -Wall -Wextra -Wpedantic)
endforeach()

# La bibliotheque regroupe les regles de decision et l'acces SQLite.
# L'interface de commande reste un executable sans logique metier.
find_package(SQLite3 REQUIRED)
add_library(cache-controle serveur-local/cache-sqlite.cpp)
target_link_libraries(cache-controle PUBLIC SQLite::SQLite3)
target_include_directories(cache-controle PUBLIC serveur-local)
target_compile_options(cache-controle PRIVATE -Wall -Wextra -Wpedantic)
add_executable(controle-local serveur-local/controle-local.cpp)
target_link_libraries(controle-local PRIVATE cache-controle)
target_compile_options(controle-local PRIVATE -Wall -Wextra -Wpedantic)

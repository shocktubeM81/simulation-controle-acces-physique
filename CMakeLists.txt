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

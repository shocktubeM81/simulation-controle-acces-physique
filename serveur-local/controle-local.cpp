// Interface en ligne de commande du moteur de decision local.
// La logique SQLite est separee pour faciliter les tests et l'evolution.
#include "cache-sqlite.hpp"

#include <exception>
#include <iostream>
#include <string>

int main(int argc, char** argv) {
    try {
        if (argc == 2 && std::string(argv[1]) == "initialiser") {
            controle::initialiser();
            return 0;
        }
        if (argc == 4 && std::string(argv[1]) == "verifier") {
            controle::verifier_acces(argv[2], argv[3], false);
            return 0;
        }
        if (argc == 4 && std::string(argv[1]) == "verifier-sync") {
            controle::verifier_acces(argv[2], argv[3], true);
            return 0;
        }
        std::cerr << "Usage : controle-local initialiser | verifier CODE PORTE | verifier-sync CODE PORTE\n";
        return 2;
    } catch (const std::exception& e) {
        std::cerr << "Erreur : " << e.what() << '\n';
        return 1;
    }
}

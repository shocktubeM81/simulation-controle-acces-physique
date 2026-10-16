#pragma once
#include <string>

namespace controle {

// Cree le cache de demonstration sans toucher au cache synchronise.
void initialiser();

// Evalue un droit local; le mode synchronise refuse les donnees perimees.
void verifier_acces(const std::string& identifiant, const std::string& porte,
                    bool exiger_synchro);

}  // namespace controle

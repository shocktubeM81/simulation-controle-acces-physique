// Premier essai : serveur TCP IPv4 pour le laboratoire de contrôle d'accès.
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cerrno>
#include <cstring>
#include <iostream>
#include <string>

int main(int argc, char* argv[]) {
    const std::string adresse = argc > 1 ? argv[1] : "127.0.0.1";
    const std::string texte_port = argc > 2 ? argv[2] : "5050";

    if (argc > 3) {
        std::cerr << "Utilisation : " << argv[0] << " [adresse_ipv4] [port]\n";
        return 1;
    }

    int port = 0;
    try {
        std::size_t position = 0;
        port = std::stoi(texte_port, &position);
        if (position != texte_port.size() || port < 1 || port > 65535) {
            throw std::invalid_argument("port invalide");
        }
    } catch (const std::exception&) {
        std::cerr << "Erreur : le port doit être compris entre 1 et 65535.\n";
        return 1;
    }

    sockaddr_in adresse_locale{};
    adresse_locale.sin_family = AF_INET;
    adresse_locale.sin_port = htons(static_cast<uint16_t>(port));

    if (inet_pton(AF_INET, adresse.c_str(), &adresse_locale.sin_addr) != 1) {
        std::cerr << "Erreur : adresse IPv4 invalide.\n";
        return 1;
    }

    const int prise_ecoute = socket(AF_INET, SOCK_STREAM, 0);
    if (prise_ecoute < 0) {
        std::cerr << "Impossible de créer la prise réseau : " << std::strerror(errno) << '\n';
        return 1;
    }

    int reutiliser = 1;
    setsockopt(prise_ecoute, SOL_SOCKET, SO_REUSEADDR, &reutiliser, sizeof(reutiliser));

    if (bind(prise_ecoute, reinterpret_cast<sockaddr*>(&adresse_locale),
             sizeof(adresse_locale)) < 0 ||
        listen(prise_ecoute, 5) < 0) {
        std::cerr << "Impossible de démarrer le serveur : " << std::strerror(errno) << '\n';
        close(prise_ecoute);
        return 1;
    }

    std::cout << "Serveur central à l'écoute sur " << adresse << ':' << port << std::endl;

    // Première version : une connexion à la fois; arrêt avec Ctrl+C.
    while (true) {
        const int prise_client = accept(prise_ecoute, nullptr, nullptr);
        if (prise_client < 0) {
            if (errno == EINTR) continue;
            std::cerr << "Erreur d'acceptation : " << std::strerror(errno) << '\n';
            break;
        }

        char tampon[1024]{};
        const ssize_t quantite = recv(prise_client, tampon, sizeof(tampon), 0);
        if (quantite > 0) {
            std::cout << "Message reçu : "
                      << std::string(tampon, static_cast<std::size_t>(quantite))
                      << std::endl;

            const std::string reponse = "ACCUSÉ DE RÉCEPTION\n";
            std::size_t envoyes = 0;
            while (envoyes < reponse.size()) {
                const ssize_t n = send(prise_client, reponse.data() + envoyes,
                                       reponse.size() - envoyes, MSG_NOSIGNAL);
                if (n <= 0) break;
                envoyes += static_cast<std::size_t>(n);
            }
        }
        close(prise_client);
    }

    close(prise_ecoute);
    return 1;
}

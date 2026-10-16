// Premier essai : client TCP IPv4 simulant un serveur local.
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cerrno>
#include <cstring>
#include <iostream>
#include <stdexcept>
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

    sockaddr_in destination{};
    destination.sin_family = AF_INET;
    destination.sin_port = htons(static_cast<uint16_t>(port));

    if (inet_pton(AF_INET, adresse.c_str(), &destination.sin_addr) != 1) {
        std::cerr << "Erreur : adresse IPv4 invalide.\n";
        return 1;
    }

    const int prise = socket(AF_INET, SOCK_STREAM, 0);
    if (prise < 0) {
        std::cerr << "Impossible de créer la prise réseau : " << std::strerror(errno) << '\n';
        return 1;
    }

    if (connect(prise, reinterpret_cast<sockaddr*>(&destination),
                sizeof(destination)) < 0) {
        std::cerr << "Connexion impossible : " << std::strerror(errno) << '\n';
        close(prise);
        return 1;
    }

    std::cout << "Connexion établie avec " << adresse << ':' << port << '\n';

    const std::string message = "BONJOUR DU SERVEUR LOCAL\n";
    std::size_t envoyes = 0;
    while (envoyes < message.size()) {
        const ssize_t n = send(prise, message.data() + envoyes,
                               message.size() - envoyes, MSG_NOSIGNAL);
        if (n <= 0) {
            std::cerr << "Échec de l'envoi : " << std::strerror(errno) << '\n';
            close(prise);
            return 1;
        }
        envoyes += static_cast<std::size_t>(n);
    }

    char tampon[1024]{};
    const ssize_t quantite = recv(prise, tampon, sizeof(tampon), 0);
    if (quantite > 0) {
        std::cout << "Réponse reçue : "
                  << std::string(tampon, static_cast<std::size_t>(quantite));
    } else {
        std::cerr << "Aucune réponse du serveur central.\n";
        close(prise);
        return 1;
    }

    close(prise);
    return 0;
}

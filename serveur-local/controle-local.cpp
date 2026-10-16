// Prototype autonome du cache local. Les identifiants sont entièrement fictifs.
// Ce programme n'ouvre aucun port et ne synchronise pas encore le serveur central.
#include <sqlite3.h>
#include <iostream>
#include <ctime>
#include <stdexcept>
#include <string>

namespace {
constexpr const char* chemin = "/donnees/autorisations.sqlite3";

void verifier(int rc, sqlite3* db, const std::string& operation) {
    if (rc != SQLITE_OK && rc != SQLITE_DONE && rc != SQLITE_ROW) {
        throw std::runtime_error(operation + " : " + sqlite3_errmsg(db));
    }
}

class Base {
public:
    explicit Base(bool creation) {
        const int flags = creation ? SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE
                                   : SQLITE_OPEN_READONLY;
        const int rc = sqlite3_open_v2(chemin, &db_, flags, nullptr);
        if (rc != SQLITE_OK) {
            const std::string message = db_ ? sqlite3_errmsg(db_) : "ouverture impossible";
            if (db_) sqlite3_close(db_);
            db_ = nullptr;
            throw std::runtime_error("SQLite : " + message +
                                     ". Exécuter d'abord la commande initialiser.");
        }
        sqlite3_busy_timeout(db_, 3000);
    }
    ~Base() { if (db_) sqlite3_close(db_); }
    sqlite3* get() const { return db_; }
    Base(const Base&) = delete;
    Base& operator=(const Base&) = delete;
private:
    sqlite3* db_ = nullptr;
};

void executer(sqlite3* db, const char* sql) {
    char* erreur = nullptr;
    const int rc = sqlite3_exec(db, sql, nullptr, nullptr, &erreur);
    if (rc != SQLITE_OK) {
        std::string message = erreur ? erreur : sqlite3_errmsg(db);
        sqlite3_free(erreur);
        throw std::runtime_error("SQLite : " + message);
    }
}

void initialiser() {
    Base base(true);
    // Fixture locale temporaire, distincte d'une synchronisation réelle.
    // Réexécutable sans écraser les données déjà présentes.
    executer(base.get(), R"SQL(
        BEGIN IMMEDIATE;
        CREATE TABLE IF NOT EXISTS personnes (
          id_personne INTEGER PRIMARY KEY, actif INTEGER NOT NULL CHECK (actif IN (0, 1))
        );
        CREATE TABLE IF NOT EXISTS identifiants (
          code TEXT PRIMARY KEY, id_personne INTEGER NOT NULL,
          actif INTEGER NOT NULL CHECK (actif IN (0, 1)),
          FOREIGN KEY (id_personne) REFERENCES personnes(id_personne)
        );
        CREATE TABLE IF NOT EXISTS portes (
          nom TEXT PRIMARY KEY, actif INTEGER NOT NULL CHECK (actif IN (0, 1))
        );
        CREATE TABLE IF NOT EXISTS autorisations (
          id_personne INTEGER NOT NULL, nom_porte TEXT NOT NULL,
          PRIMARY KEY (id_personne, nom_porte),
          FOREIGN KEY (id_personne) REFERENCES personnes(id_personne),
          FOREIGN KEY (nom_porte) REFERENCES portes(nom)
        );
        INSERT OR IGNORE INTO personnes VALUES (1,1),(2,1),(3,1),(4,1),(5,1),(6,1);
        INSERT OR IGNORE INTO portes VALUES
          ('Entree principale',1),('Laboratoire',1),('Salle informatique',1),('Local technique',1);
        INSERT OR IGNORE INTO identifiants VALUES
          ('FICTIF-0001',1,1),('FICTIF-0002',2,1),('FICTIF-0003',3,1),
          ('FICTIF-0004',4,1),('FICTIF-0005',5,1),('FICTIF-0006',6,1);
        INSERT OR IGNORE INTO autorisations VALUES
          (1,'Entree principale'),(1,'Laboratoire'),
          (2,'Entree principale'),(2,'Salle informatique'),
          (3,'Entree principale'),
          (4,'Entree principale'),(4,'Local technique'),
          (5,'Entree principale');
        COMMIT;
    )SQL");
    std::cout << "Cache SQLite prêt : " << chemin << '\n';
}

void verifier_acces(const std::string& identifiant, const std::string& porte,
                    bool exiger_synchro) {
    Base base(false);
    if (exiger_synchro) {
        sqlite3_stmt* horodatage = nullptr;
        const int prep = sqlite3_prepare_v2(base.get(),
            "SELECT instant_local FROM synchronisation WHERE id = 1",
            -1, &horodatage, nullptr);
        if (prep != SQLITE_OK) {
            if (horodatage) sqlite3_finalize(horodatage);
            std::cout << "REFUSE\\n";
            std::cerr << "Aucune synchronisation validée\\n";
            return;
        }
        const int result = sqlite3_step(horodatage);
        const long long dernier = result == SQLITE_ROW ?
            sqlite3_column_int64(horodatage, 0) : -1;
        sqlite3_finalize(horodatage);
        const long long maintenant = static_cast<long long>(std::time(nullptr));
        // Profil standard, valeur documentée dans politique-synchronisation.json.
        if (dernier < 0 || maintenant < dernier || maintenant - dernier > 3600) {
            std::cout << "REFUSE\\n";
            std::cerr << "Cache absent, expiré ou horloge incohérente\\n";
            return;
        }
    }
    const char* requete = exiger_synchro ? R"SQL(
        SELECT EXISTS (
          SELECT 1 FROM identifiants i
          JOIN personnes p ON p.id_personne = i.id_personne
          JOIN autorisations a ON a.id_personne = p.id_personne
          JOIN portes po ON po.nom = a.nom_porte
          WHERE i.code = ?1 AND po.nom = ?2
            AND i.actif = 1 AND p.actif = 1 AND po.actif = 1
          AND (a.date_debut IS NULL OR datetime(a.date_debut) <= datetime('now'))
          AND (a.date_fin IS NULL OR datetime(a.date_fin) > datetime('now'))
        )
    )SQL" : R"SQL(
        SELECT EXISTS (
          SELECT 1 FROM identifiants i
          JOIN personnes p ON p.id_personne = i.id_personne
          JOIN autorisations a ON a.id_personne = p.id_personne
          JOIN portes po ON po.nom = a.nom_porte
          WHERE i.code = ?1 AND po.nom = ?2
            AND i.actif = 1 AND p.actif = 1 AND po.actif = 1
        )
    )SQL";
    sqlite3_stmt* statement = nullptr;
    verifier(sqlite3_prepare_v2(base.get(), requete, -1, &statement, nullptr),
             base.get(), "Préparation");
    try {
        verifier(sqlite3_bind_text(statement, 1, identifiant.c_str(), -1, SQLITE_TRANSIENT),
                 base.get(), "Identifiant");
        verifier(sqlite3_bind_text(statement, 2, porte.c_str(), -1, SQLITE_TRANSIENT),
                 base.get(), "Porte");
        const int rc = sqlite3_step(statement);
        if (rc != SQLITE_ROW) {
            verifier(rc, base.get(), "Décision");
            throw std::runtime_error("Aucun résultat SQL");
        }
        std::cout << (sqlite3_column_int(statement, 0) ? "AUTORISE" : "REFUSE") << '\n';
    } catch (...) {
        sqlite3_finalize(statement);
        throw;
    }
    sqlite3_finalize(statement);
}
}

int main(int argc, char** argv) {
    try {
        if (argc == 2 && std::string(argv[1]) == "initialiser") {
            initialiser();
            return 0;
        }
        if (argc == 4 && std::string(argv[1]) == "verifier") {
            verifier_acces(argv[2], argv[3], false);
            return 0;
        }
        std::cerr << "Usage : controle-local initialiser | verifier CODE PORTE\n";
        return 2;
    } catch (const std::exception& e) {
        std::cerr << "Erreur : " << e.what() << '\n';
        return 1;
    }
}

-- Script rejouable, exécuté après le démarrage du conteneur PostgreSQL.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'api_anonyme') THEN
        CREATE ROLE api_anonyme NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'api_authentificateur') THEN
        CREATE ROLE api_authentificateur LOGIN NOINHERIT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'api_proprietaire') THEN
        CREATE ROLE api_proprietaire NOLOGIN;
    END IF;
END
$$;

-- Le mot de passe est reçu par psql sans argument de ligne de commande.
SELECT format('ALTER ROLE api_authentificateur PASSWORD %L', :'passe') \gexec
GRANT api_anonyme TO api_authentificateur;
GRANT CONNECT ON DATABASE controle_acces_simulation TO api_authentificateur;
GRANT SELECT ON TABLE personnes, identifiants, portes, autorisations TO api_proprietaire;
CREATE SCHEMA IF NOT EXISTS api AUTHORIZATION api_proprietaire;

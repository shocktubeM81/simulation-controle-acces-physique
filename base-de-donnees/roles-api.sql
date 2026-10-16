-- À exécuter en tant qu'administrateur PostgreSQL (postgres).
-- Comptes techniques distincts du compte personnel david.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'api_anonyme') THEN
        CREATE ROLE api_anonyme NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'api_authentificateur') THEN
        CREATE ROLE api_authentificateur LOGIN NOINHERIT;
    END IF;
END
$$;

GRANT api_anonyme TO api_authentificateur;
GRANT CONNECT ON DATABASE controle_acces_simulation TO api_authentificateur;

-- Le mot de passe du rôle de connexion se définit séparément,
-- de manière interactive, à l'aide de \password dans psql.

-- À exécuter avec le rôle propriétaire des tables (david sur l'EliteBook).
-- Seule la fonction de décision est exposée par PostgREST.
BEGIN;

CREATE SCHEMA IF NOT EXISTS api;
REVOKE ALL ON SCHEMA api FROM PUBLIC;

CREATE OR REPLACE FUNCTION api.verifier_acces(
    code_identifiant TEXT,
    nom_porte TEXT
)
RETURNS TABLE (decision TEXT)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = ''
AS $fonction$
    SELECT CASE WHEN EXISTS (
        SELECT 1
        FROM public.identifiants AS i
        JOIN public.personnes AS p ON p.id_personne = i.id_personne
        JOIN public.autorisations AS a ON a.id_personne = p.id_personne
        JOIN public.portes AS po ON po.id_porte = a.id_porte
        WHERE i.code = code_identifiant
          AND po.nom = nom_porte
          AND i.actif
          AND p.actif
          AND po.actif
          AND (a.date_debut IS NULL OR a.date_debut <= NOW())
          AND (a.date_fin IS NULL OR a.date_fin > NOW())
    )
    THEN 'AUTORISE'::TEXT
    ELSE 'REFUSE'::TEXT END AS decision;
$fonction$;

REVOKE ALL ON FUNCTION api.verifier_acces(TEXT, TEXT) FROM PUBLIC;
GRANT USAGE ON SCHEMA api TO api_anonyme;
GRANT EXECUTE ON FUNCTION api.verifier_acces(TEXT, TEXT) TO api_anonyme;

COMMIT;

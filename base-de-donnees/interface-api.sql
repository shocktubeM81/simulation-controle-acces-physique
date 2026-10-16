-- Fonction API : création sous un rôle applicatif restreint.
-- Seule la fonction de décision est exposée par PostgREST.
BEGIN;

-- Le script s'exécute pendant l'initialisation PostgreSQL, comme superutilisateur.
-- La fonction SECURITY DEFINER appartient au rôle applicatif limité.
SET LOCAL ROLE api_proprietaire;
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

-- Instantané fictif pour la synchronisation expérimentale.
-- Accessible uniquement sur le port local PostgREST; transport SSH requis
-- pour atteindre ce port depuis le Raspberry Pi.
CREATE OR REPLACE FUNCTION api.exporter_autorisations()
RETURNS JSONB
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = ''
AS $fonction$
    SELECT jsonb_build_object(
        'schema_version', 1,
        'captured_at', to_char(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"'),
        'personnes', (SELECT COALESCE(jsonb_agg(jsonb_build_object(
            'id_personne', id_personne, 'actif', actif) ORDER BY id_personne), '[]'::jsonb)
            FROM public.personnes),
        'identifiants', (SELECT COALESCE(jsonb_agg(jsonb_build_object(
            'code', code, 'id_personne', id_personne, 'actif', actif) ORDER BY code), '[]'::jsonb)
            FROM public.identifiants),
        'portes', (SELECT COALESCE(jsonb_agg(jsonb_build_object(
            'nom', nom, 'actif', actif) ORDER BY nom), '[]'::jsonb)
            FROM public.portes),
        'autorisations', (SELECT COALESCE(jsonb_agg(jsonb_build_object(
            'id_personne', id_personne, 'nom_porte', po.nom,
            'date_debut', a.date_debut, 'date_fin', a.date_fin)
            ORDER BY id_personne, po.nom), '[]'::jsonb)
            FROM public.autorisations a
            JOIN public.portes po ON po.id_porte = a.id_porte)
    );
$fonction$;

REVOKE ALL ON FUNCTION api.exporter_autorisations() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION api.exporter_autorisations() TO api_anonyme;

COMMIT;

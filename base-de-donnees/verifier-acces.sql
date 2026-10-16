-- Exemple : FICTIF-0001 à la porte Laboratoire => autorisé.
-- Exemple : FICTIF-0003 à la porte Laboratoire => refusé.
-- Modifier les deux valeurs dans la CTE pour tester d'autres cas.
WITH demande AS (
    SELECT
        'FICTIF-0001'::VARCHAR AS code,
        'Laboratoire'::VARCHAR AS porte
)
SELECT
    d.code,
    d.porte,
    CASE WHEN EXISTS (
        SELECT 1
        FROM identifiants AS i
        JOIN personnes AS p ON p.id_personne = i.id_personne
        JOIN autorisations AS a ON a.id_personne = p.id_personne
        JOIN portes AS po ON po.id_porte = a.id_porte
        WHERE i.code = d.code
          AND po.nom = d.porte
          AND i.actif
          AND p.actif
          AND po.actif
          AND (a.date_debut IS NULL OR a.date_debut <= NOW())
          AND (a.date_fin IS NULL OR a.date_fin > NOW())
    ) THEN 'AUTORISE' ELSE 'REFUSE' END AS decision
FROM demande AS d;

-- Données fictives : ne pas utiliser d'identifiants réels.
-- Le script est prévu pour une base de démonstration vide.
BEGIN;

INSERT INTO personnes (nom, prenom) VALUES
    ('Tremblay', 'Alice'),
    ('Gagnon', 'Malik'),
    ('Roy', 'Camille'),
    ('Bouchard', 'Noah'),
    ('Côté', 'Emma'),
    ('Pelletier', 'Alex');

INSERT INTO portes (nom) VALUES
    ('Entree principale'),
    ('Laboratoire'),
    ('Salle informatique'),
    ('Local technique');

INSERT INTO identifiants (id_personne, code) VALUES
    ((SELECT id_personne FROM personnes WHERE nom = 'Tremblay' AND prenom = 'Alice'), 'FICTIF-0001'),
    ((SELECT id_personne FROM personnes WHERE nom = 'Gagnon' AND prenom = 'Malik'), 'FICTIF-0002'),
    ((SELECT id_personne FROM personnes WHERE nom = 'Roy' AND prenom = 'Camille'), 'FICTIF-0003'),
    ((SELECT id_personne FROM personnes WHERE nom = 'Bouchard' AND prenom = 'Noah'), 'FICTIF-0004'),
    ((SELECT id_personne FROM personnes WHERE nom = 'Côté' AND prenom = 'Emma'), 'FICTIF-0005'),
    ((SELECT id_personne FROM personnes WHERE nom = 'Pelletier' AND prenom = 'Alex'), 'FICTIF-0006');

INSERT INTO autorisations (id_personne, id_porte)
SELECT p.id_personne, po.id_porte
FROM personnes AS p
CROSS JOIN portes AS po
WHERE
    (p.prenom = 'Alice' AND po.nom IN ('Entree principale', 'Laboratoire'))
    OR (p.prenom = 'Malik' AND po.nom IN ('Entree principale', 'Salle informatique'))
    OR (p.prenom = 'Camille' AND po.nom = 'Entree principale')
    OR (p.prenom = 'Noah' AND po.nom IN ('Entree principale', 'Local technique'))
    OR (p.prenom = 'Emma' AND po.nom = 'Entree principale');

COMMIT;

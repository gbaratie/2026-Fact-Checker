-- =============================================================================
-- Sync candidats présidentielle 2027 → table public.candidates (Neon)
-- Coller dans le SQL Editor Neon et exécuter en une fois.
--
-- Effets :
--   1. Supprime les candidats hors liste cible (+ données liées)
--   2. Upsert (insert ou maj) de tous les candidats cibles
--   3. Affiche un contrôle final
--
-- Statuts : declared | potential | withdrawn
-- Partis : libellés courts alignés sur l’existant (RN, LFI, LR, …)
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 1) Suppression des candidats absents de la liste cible
--    (prod actuelle : fabien-roussel, francois-ruffin, jordan-bardella ;
--     la requête couvre aussi d’éventuels résidus hors liste)
-- -----------------------------------------------------------------------------
CREATE TEMP TABLE _candidates_to_delete ON COMMIT DROP AS
SELECT c.id
FROM candidates c
WHERE c.slug NOT IN (
  'edouard-philippe',
  'bruno-retailleau',
  'david-lisnard',
  'laurent-wauquiez',
  'xavier-bertrand',
  'marine-le-pen',
  'nicolas-dupont-aignan',
  'florian-philippot',
  'francois-asselineau',
  'clara-egger',
  'antoine-mikolajczak',
  'nathalie-arthaud',
  'gabriel-attal',
  'gerald-darmanin',
  'sebastien-lecornu',
  'jean-luc-melenchon',
  'raphael-glucksmann',
  'marine-tondelier',
  'olivier-faure',
  'segolene-royal',
  'philippe-brun',
  'bernard-cazeneuve',
  'michel-barnier',
  'valerie-pecresse',
  'eric-zemmour'
);

CREATE TEMP TABLE _sources_to_delete ON COMMIT DROP AS
SELECT source_id AS id FROM interviews
WHERE candidate_id IN (SELECT id FROM _candidates_to_delete)
UNION
SELECT source_id FROM parliamentary_votes
WHERE candidate_id IN (SELECT id FROM _candidates_to_delete)
UNION
SELECT source_id FROM articles
WHERE candidate_id IN (SELECT id FROM _candidates_to_delete)
UNION
SELECT source_id FROM program_documents
WHERE candidate_id IN (SELECT id FROM _candidates_to_delete);

DELETE FROM interviews
WHERE candidate_id IN (SELECT id FROM _candidates_to_delete);

DELETE FROM parliamentary_votes
WHERE candidate_id IN (SELECT id FROM _candidates_to_delete);

DELETE FROM articles
WHERE candidate_id IN (SELECT id FROM _candidates_to_delete);

DELETE FROM program_documents
WHERE candidate_id IN (SELECT id FROM _candidates_to_delete);

DELETE FROM sources
WHERE id IN (SELECT id FROM _sources_to_delete WHERE id IS NOT NULL);

DELETE FROM candidates
WHERE id IN (SELECT id FROM _candidates_to_delete);

-- -----------------------------------------------------------------------------
-- 2) Upsert de la liste cible
--    ON CONFLICT (slug) : met à jour full_name, party, status
--    Ne touche PAS external_ids / parliamentary_group_id (préserve CLAIR, etc.)
-- -----------------------------------------------------------------------------
INSERT INTO candidates (id, slug, full_name, party, external_ids, status)
VALUES
  -- === Candidats déclarés ===
  -- Bloc central / droite
  (gen_random_uuid(), 'edouard-philippe',      'Édouard Philippe',       'Horizons',        '{}'::json, 'declared'),
  (gen_random_uuid(), 'bruno-retailleau',      'Bruno Retailleau',       'LR',              '{}'::json, 'declared'),
  -- Les Républicains
  (gen_random_uuid(), 'david-lisnard',         'David Lisnard',          'LR',              '{}'::json, 'declared'),
  (gen_random_uuid(), 'laurent-wauquiez',      'Laurent Wauquiez',       'LR',              '{}'::json, 'declared'),
  (gen_random_uuid(), 'xavier-bertrand',       'Xavier Bertrand',        'LR',              '{}'::json, 'declared'),
  -- Extrême droite / souverainistes
  (gen_random_uuid(), 'marine-le-pen',         'Marine Le Pen',          'RN',              '{}'::json, 'declared'),
  (gen_random_uuid(), 'nicolas-dupont-aignan', 'Nicolas Dupont-Aignan',  'DLF',             '{}'::json, 'declared'),
  (gen_random_uuid(), 'florian-philippot',     'Florian Philippot',      'Les Patriotes',   '{}'::json, 'declared'),
  (gen_random_uuid(), 'francois-asselineau',   'François Asselineau',    'UPR',             '{}'::json, 'declared'),
  (gen_random_uuid(), 'clara-egger',           'Clara Egger',            'Équinoxe',        '{}'::json, 'declared'),
  (gen_random_uuid(), 'antoine-mikolajczak',   'Antoine Mikolajczak',    NULL,              '{}'::json, 'declared'),
  -- Extrême gauche
  (gen_random_uuid(), 'nathalie-arthaud',      'Nathalie Arthaud',       'LO',              '{}'::json, 'declared'),

  -- === Principaux candidats pressentis ===
  -- Bloc central
  (gen_random_uuid(), 'gabriel-attal',         'Gabriel Attal',          'RE',              '{}'::json, 'potential'),
  (gen_random_uuid(), 'gerald-darmanin',       'Gérald Darmanin',        'RE',              '{}'::json, 'potential'),
  (gen_random_uuid(), 'sebastien-lecornu',     'Sébastien Lecornu',      'RE',              '{}'::json, 'potential'),
  -- Gauche
  (gen_random_uuid(), 'jean-luc-melenchon',    'Jean-Luc Mélenchon',     'LFI',             '{}'::json, 'potential'),
  (gen_random_uuid(), 'raphael-glucksmann',    'Raphaël Glucksmann',     'Place publique',  '{}'::json, 'potential'),
  (gen_random_uuid(), 'marine-tondelier',      'Marine Tondelier',       'Les Écologistes', '{}'::json, 'potential'),
  (gen_random_uuid(), 'olivier-faure',         'Olivier Faure',          'PS',              '{}'::json, 'potential'),
  (gen_random_uuid(), 'segolene-royal',        'Ségolène Royal',         'PS',              '{}'::json, 'potential'),
  (gen_random_uuid(), 'philippe-brun',         'Philippe Brun',          'PS',              '{}'::json, 'potential'),
  (gen_random_uuid(), 'bernard-cazeneuve',     'Bernard Cazeneuve',      NULL,              '{}'::json, 'potential'),
  -- Droite
  (gen_random_uuid(), 'michel-barnier',        'Michel Barnier',         'LR',              '{}'::json, 'potential'),
  (gen_random_uuid(), 'valerie-pecresse',      'Valérie Pécresse',       'Libres!',         '{}'::json, 'potential'),
  -- Reconquête
  (gen_random_uuid(), 'eric-zemmour',          'Éric Zemmour',           'Reconquête',      '{}'::json, 'potential')
ON CONFLICT (slug) DO UPDATE SET
  full_name = EXCLUDED.full_name,
  party     = EXCLUDED.party,
  status    = EXCLUDED.status;
  -- external_ids et parliamentary_group_id volontairement non écrasés

COMMIT;

-- -----------------------------------------------------------------------------
-- 3) Contrôle après sync (attendu : 12 declared + 13 potential = 25)
-- -----------------------------------------------------------------------------
SELECT status, COUNT(*) AS n
FROM candidates
GROUP BY status
ORDER BY status;

SELECT
  slug,
  full_name,
  party,
  status,
  external_ids ->> 'clair_slug' AS clair_slug
FROM candidates
ORDER BY
  CASE status WHEN 'declared' THEN 0 WHEN 'potential' THEN 1 ELSE 2 END,
  full_name;

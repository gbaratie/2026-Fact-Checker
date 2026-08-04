-- =============================================================================
-- Sync candidats présidentielle 2027 → public.candidates (Neon SQL Editor)
--
-- IMPORTANT :
--   1. Efface tout le contenu de l’éditeur
--   2. Colle CE fichier en entier (ne sélectionne pas un extrait)
--   3. Clique Run
--
-- Attendu : 12 declared + 13 potential = 25
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1) Supprimer les candidats hors liste (+ données liées) — 1 seule requête
-- -----------------------------------------------------------------------------
WITH doomed AS (
  SELECT id
  FROM candidates
  WHERE slug NOT IN (
    'edouard-philippe', 'bruno-retailleau', 'david-lisnard', 'laurent-wauquiez',
    'xavier-bertrand', 'marine-le-pen', 'nicolas-dupont-aignan', 'florian-philippot',
    'francois-asselineau', 'clara-egger', 'antoine-mikolajczak', 'nathalie-arthaud',
    'gabriel-attal', 'gerald-darmanin', 'sebastien-lecornu', 'jean-luc-melenchon',
    'raphael-glucksmann', 'marine-tondelier', 'olivier-faure', 'segolene-royal',
    'philippe-brun', 'bernard-cazeneuve', 'michel-barnier', 'valerie-pecresse',
    'eric-zemmour'
  )
),
src AS (
  SELECT source_id AS id FROM interviews
  WHERE candidate_id IN (SELECT id FROM doomed)
  UNION
  SELECT source_id FROM parliamentary_votes
  WHERE candidate_id IN (SELECT id FROM doomed)
  UNION
  SELECT source_id FROM articles
  WHERE candidate_id IN (SELECT id FROM doomed)
  UNION
  SELECT source_id FROM program_documents
  WHERE candidate_id IN (SELECT id FROM doomed)
),
del_interviews AS (
  DELETE FROM interviews
  WHERE candidate_id IN (SELECT id FROM doomed)
  RETURNING id
),
del_votes AS (
  DELETE FROM parliamentary_votes
  WHERE candidate_id IN (SELECT id FROM doomed)
  RETURNING id
),
del_articles AS (
  DELETE FROM articles
  WHERE candidate_id IN (SELECT id FROM doomed)
  RETURNING id
),
del_programs AS (
  DELETE FROM program_documents
  WHERE candidate_id IN (SELECT id FROM doomed)
  RETURNING id
),
del_sources AS (
  DELETE FROM sources
  WHERE id IN (SELECT id FROM src WHERE id IS NOT NULL)
  RETURNING id
)
DELETE FROM candidates
WHERE id IN (SELECT id FROM doomed);

-- -----------------------------------------------------------------------------
-- 2) Upsert liste cible
--    Met à jour full_name / party / status
--    Ne touche PAS external_ids ni parliamentary_group_id
-- -----------------------------------------------------------------------------
INSERT INTO candidates (id, slug, full_name, party, external_ids, status)
VALUES
  (gen_random_uuid(), 'edouard-philippe',      'Édouard Philippe',       'Horizons',        '{}'::json, 'declared'),
  (gen_random_uuid(), 'bruno-retailleau',      'Bruno Retailleau',       'LR',              '{}'::json, 'declared'),
  (gen_random_uuid(), 'david-lisnard',         'David Lisnard',          'LR',              '{}'::json, 'declared'),
  (gen_random_uuid(), 'laurent-wauquiez',      'Laurent Wauquiez',       'LR',              '{}'::json, 'declared'),
  (gen_random_uuid(), 'xavier-bertrand',       'Xavier Bertrand',        'LR',              '{}'::json, 'declared'),
  (gen_random_uuid(), 'marine-le-pen',         'Marine Le Pen',          'RN',              '{}'::json, 'declared'),
  (gen_random_uuid(), 'nicolas-dupont-aignan', 'Nicolas Dupont-Aignan',  'DLF',             '{}'::json, 'declared'),
  (gen_random_uuid(), 'florian-philippot',     'Florian Philippot',      'Les Patriotes',   '{}'::json, 'declared'),
  (gen_random_uuid(), 'francois-asselineau',   'François Asselineau',    'UPR',             '{}'::json, 'declared'),
  (gen_random_uuid(), 'clara-egger',           'Clara Egger',            'Équinoxe',        '{}'::json, 'declared'),
  (gen_random_uuid(), 'antoine-mikolajczak',   'Antoine Mikolajczak',    NULL,              '{}'::json, 'declared'),
  (gen_random_uuid(), 'nathalie-arthaud',      'Nathalie Arthaud',       'LO',              '{}'::json, 'declared'),
  (gen_random_uuid(), 'gabriel-attal',         'Gabriel Attal',          'RE',              '{}'::json, 'potential'),
  (gen_random_uuid(), 'gerald-darmanin',       'Gérald Darmanin',        'RE',              '{}'::json, 'potential'),
  (gen_random_uuid(), 'sebastien-lecornu',     'Sébastien Lecornu',      'RE',              '{}'::json, 'potential'),
  (gen_random_uuid(), 'jean-luc-melenchon',    'Jean-Luc Mélenchon',     'LFI',             '{}'::json, 'potential'),
  (gen_random_uuid(), 'raphael-glucksmann',    'Raphaël Glucksmann',     'Place publique',  '{}'::json, 'potential'),
  (gen_random_uuid(), 'marine-tondelier',      'Marine Tondelier',       'Les Écologistes', '{}'::json, 'potential'),
  (gen_random_uuid(), 'olivier-faure',         'Olivier Faure',          'PS',              '{}'::json, 'potential'),
  (gen_random_uuid(), 'segolene-royal',        'Ségolène Royal',         'PS',              '{}'::json, 'potential'),
  (gen_random_uuid(), 'philippe-brun',         'Philippe Brun',          'PS',              '{}'::json, 'potential'),
  (gen_random_uuid(), 'bernard-cazeneuve',     'Bernard Cazeneuve',      NULL,              '{}'::json, 'potential'),
  (gen_random_uuid(), 'michel-barnier',        'Michel Barnier',         'LR',              '{}'::json, 'potential'),
  (gen_random_uuid(), 'valerie-pecresse',      'Valérie Pécresse',       'Libres!',         '{}'::json, 'potential'),
  (gen_random_uuid(), 'eric-zemmour',          'Éric Zemmour',           'Reconquête',      '{}'::json, 'potential')
ON CONFLICT (slug) DO UPDATE SET
  full_name = EXCLUDED.full_name,
  party     = EXCLUDED.party,
  status    = EXCLUDED.status;

-- -----------------------------------------------------------------------------
-- 3) Contrôle
-- -----------------------------------------------------------------------------
SELECT status, COUNT(*) AS n
FROM candidates
GROUP BY status
ORDER BY status;

SELECT slug, full_name, party, status,
       external_ids ->> 'clair_slug' AS clair_slug
FROM candidates
ORDER BY
  CASE status WHEN 'declared' THEN 0 WHEN 'potential' THEN 1 ELSE 2 END,
  full_name;

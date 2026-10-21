-- Run in the original Supabase project's SQL Editor as postgres.
-- Sets presentation names only. Preserves all other metadata and permissions.
BEGIN;
DO $$
BEGIN
    IF current_user <> 'postgres' THEN
        RAISE EXCEPTION 'Run as postgres in SQL Editor';
    END IF;
    IF (SELECT count(*) FROM auth.users WHERE id IN (
        'c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid,
        '74acf117-be21-4460-877d-4f50993ac6da'::uuid
    )) <> 2 THEN
        RAISE EXCEPTION 'Expected Finn and Naja in this project. No changes applied.';
    END IF;
END $$;

UPDATE auth.users AS u
SET raw_user_meta_data = coalesce(u.raw_user_meta_data, '{}'::jsonb)
    || jsonb_build_object('display_name', names.display_name)
FROM (VALUES
    ('c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid, 'Finn'),
    ('74acf117-be21-4460-877d-4f50993ac6da'::uuid, 'Naja')
) AS names(id, display_name)
WHERE u.id = names.id;
COMMIT;

SELECT id, raw_user_meta_data ->> 'display_name' AS display_name
FROM auth.users
WHERE id IN (
    'c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid,
    '74acf117-be21-4460-877d-4f50993ac6da'::uuid
)
ORDER BY display_name;

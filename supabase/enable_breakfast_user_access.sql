-- Run the whole file as postgres in the ORIGINAL Supabase project.
-- Repeatable permission setup; does not change breakfast or booking data.
BEGIN;
DO $$
DECLARE sequence_name text;
BEGIN
 IF current_user <> 'postgres' THEN RAISE EXCEPTION 'Run as postgres'; END IF;
 IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
   WHERE n.nspname='public' AND c.relname='breakfast_notes' AND c.relrowsecurity) THEN
   RAISE EXCEPTION 'Expected RLS enabled on public.breakfast_notes';
 END IF;
 IF (SELECT count(*) FROM auth.users WHERE id IN (
   'c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid,
   '74acf117-be21-4460-877d-4f50993ac6da'::uuid,
   '4399ca28-e347-43c5-b22f-6e8be0772f61'::uuid)) <> 3 THEN
   RAISE EXCEPTION 'Expected three portal users; check project and UIDs';
 END IF;
 FOR sequence_name IN
   SELECT pg_get_serial_sequence('public.breakfast_notes', column_name)
   FROM information_schema.columns
   WHERE table_schema='public' AND table_name='breakfast_notes'
 LOOP
   IF sequence_name IS NOT NULL THEN
     EXECUTE format('GRANT USAGE ON SEQUENCE %s TO authenticated',sequence_name);
   END IF;
 END LOOP;
END $$;
GRANT SELECT ON public.breakfast_notes TO authenticated;
GRANT INSERT (dato, "ekstra_gæster", assistance, comments),
      UPDATE (dato, "ekstra_gæster", assistance, comments)
ON public.breakfast_notes TO authenticated;

DROP POLICY IF EXISTS portal_breakfast_select ON public.breakfast_notes;
CREATE POLICY portal_breakfast_select ON public.breakfast_notes AS PERMISSIVE FOR SELECT TO authenticated
USING ((SELECT auth.uid()) IN ('c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid, '74acf117-be21-4460-877d-4f50993ac6da'::uuid, '4399ca28-e347-43c5-b22f-6e8be0772f61'::uuid))
;

DROP POLICY IF EXISTS portal_breakfast_insert ON public.breakfast_notes;
CREATE POLICY portal_breakfast_insert ON public.breakfast_notes AS PERMISSIVE FOR INSERT TO authenticated
WITH CHECK ((SELECT auth.uid()) IN ('c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid, '74acf117-be21-4460-877d-4f50993ac6da'::uuid, '4399ca28-e347-43c5-b22f-6e8be0772f61'::uuid))
;

DROP POLICY IF EXISTS portal_breakfast_insert_guard ON public.breakfast_notes;
CREATE POLICY portal_breakfast_insert_guard ON public.breakfast_notes AS RESTRICTIVE FOR INSERT TO authenticated
WITH CHECK ((SELECT auth.uid()) IN ('c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid, '74acf117-be21-4460-877d-4f50993ac6da'::uuid, '4399ca28-e347-43c5-b22f-6e8be0772f61'::uuid))
;

DROP POLICY IF EXISTS portal_breakfast_update ON public.breakfast_notes;
CREATE POLICY portal_breakfast_update ON public.breakfast_notes AS PERMISSIVE FOR UPDATE TO authenticated
USING ((SELECT auth.uid()) IN ('c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid, '74acf117-be21-4460-877d-4f50993ac6da'::uuid, '4399ca28-e347-43c5-b22f-6e8be0772f61'::uuid))
WITH CHECK ((SELECT auth.uid()) IN ('c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid, '74acf117-be21-4460-877d-4f50993ac6da'::uuid, '4399ca28-e347-43c5-b22f-6e8be0772f61'::uuid))
;

DROP POLICY IF EXISTS portal_breakfast_update_guard ON public.breakfast_notes;
CREATE POLICY portal_breakfast_update_guard ON public.breakfast_notes AS RESTRICTIVE FOR UPDATE TO authenticated
USING ((SELECT auth.uid()) IN ('c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid, '74acf117-be21-4460-877d-4f50993ac6da'::uuid, '4399ca28-e347-43c5-b22f-6e8be0772f61'::uuid))
WITH CHECK ((SELECT auth.uid()) IN ('c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid, '74acf117-be21-4460-877d-4f50993ac6da'::uuid, '4399ca28-e347-43c5-b22f-6e8be0772f61'::uuid))
;

NOTIFY pgrst, 'reload schema';
COMMIT;
SELECT policyname, cmd, permissive FROM pg_policies
WHERE schemaname='public' AND tablename='breakfast_notes'
AND policyname LIKE 'portal_breakfast_%' ORDER BY policyname;

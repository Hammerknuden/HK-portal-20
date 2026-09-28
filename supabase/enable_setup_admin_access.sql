-- Run in original project SQL Editor as postgres. Installs permissions only.
-- Does not change prices, events or close any season.
BEGIN;
DO $$
DECLARE relation_name text; seq_name text;
BEGIN
 IF current_user <> 'postgres' THEN RAISE EXCEPTION 'Run as postgres'; END IF;
 IF (SELECT count(*) FROM auth.users WHERE id IN (
 'c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid,
 '74acf117-be21-4460-877d-4f50993ac6da'::uuid)) <> 2 THEN
   RAISE EXCEPTION 'Both administrators must exist';
 END IF;
 FOREACH relation_name IN ARRAY ARRAY['high_season','Events'] LOOP
   IF NOT EXISTS(SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
      WHERE n.nspname='public' AND c.relname=relation_name AND c.relrowsecurity) THEN
     RAISE EXCEPTION 'RLS must already be enabled on %',relation_name;
   END IF;
 END LOOP;
 IF NOT EXISTS(SELECT 1 FROM pg_proc WHERE oid=to_regprocedure('public.close_booking_season(integer)')
   AND NOT prosecdef AND prorettype='jsonb'::regtype AND position('statistik_historik' IN prosrc)>0) THEN
   RAISE EXCEPTION 'Expected existing combined history/statistics season-close function';
 END IF;
 seq_name := pg_get_serial_sequence('public."Events"','id');
 IF seq_name IS NOT NULL THEN EXECUTE format('GRANT USAGE ON SEQUENCE %s TO authenticated',seq_name); END IF;
END $$;
GRANT SELECT ON public.high_season, public."Events" TO authenticated;
GRANT UPDATE (enk_low,enk_high,dobb_low,dobb_high,pris_morgenmad) ON public.high_season TO authenticated;
GRANT INSERT,UPDATE,DELETE ON public."Events" TO authenticated;

DROP POLICY IF EXISTS portal_setup_high_season_select ON public."high_season";
CREATE POLICY portal_setup_high_season_select ON public."high_season" AS PERMISSIVE FOR SELECT TO authenticated
USING ((SELECT auth.uid()) IN ('c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid, '74acf117-be21-4460-877d-4f50993ac6da'::uuid));

DROP POLICY IF EXISTS portal_setup_high_season_update ON public."high_season";
CREATE POLICY portal_setup_high_season_update ON public."high_season" AS PERMISSIVE FOR UPDATE TO authenticated
USING ((SELECT auth.uid()) IN ('c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid, '74acf117-be21-4460-877d-4f50993ac6da'::uuid))
WITH CHECK ((SELECT auth.uid()) IN ('c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid, '74acf117-be21-4460-877d-4f50993ac6da'::uuid));

DROP POLICY IF EXISTS portal_setup_high_season_update_guard ON public."high_season";
CREATE POLICY portal_setup_high_season_update_guard ON public."high_season" AS RESTRICTIVE FOR UPDATE TO authenticated
USING ((SELECT auth.uid()) IN ('c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid, '74acf117-be21-4460-877d-4f50993ac6da'::uuid))
WITH CHECK ((SELECT auth.uid()) IN ('c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid, '74acf117-be21-4460-877d-4f50993ac6da'::uuid));

DROP POLICY IF EXISTS portal_setup_events_select ON public."Events";
CREATE POLICY portal_setup_events_select ON public."Events" AS PERMISSIVE FOR SELECT TO authenticated
USING ((SELECT auth.uid()) IN ('c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid, '74acf117-be21-4460-877d-4f50993ac6da'::uuid));

DROP POLICY IF EXISTS portal_setup_events_insert ON public."Events";
CREATE POLICY portal_setup_events_insert ON public."Events" AS PERMISSIVE FOR INSERT TO authenticated
WITH CHECK ((SELECT auth.uid()) IN ('c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid, '74acf117-be21-4460-877d-4f50993ac6da'::uuid));

DROP POLICY IF EXISTS portal_setup_events_insert_guard ON public."Events";
CREATE POLICY portal_setup_events_insert_guard ON public."Events" AS RESTRICTIVE FOR INSERT TO authenticated
WITH CHECK ((SELECT auth.uid()) IN ('c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid, '74acf117-be21-4460-877d-4f50993ac6da'::uuid));

DROP POLICY IF EXISTS portal_setup_events_update ON public."Events";
CREATE POLICY portal_setup_events_update ON public."Events" AS PERMISSIVE FOR UPDATE TO authenticated
USING ((SELECT auth.uid()) IN ('c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid, '74acf117-be21-4460-877d-4f50993ac6da'::uuid))
WITH CHECK ((SELECT auth.uid()) IN ('c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid, '74acf117-be21-4460-877d-4f50993ac6da'::uuid));

DROP POLICY IF EXISTS portal_setup_events_update_guard ON public."Events";
CREATE POLICY portal_setup_events_update_guard ON public."Events" AS RESTRICTIVE FOR UPDATE TO authenticated
USING ((SELECT auth.uid()) IN ('c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid, '74acf117-be21-4460-877d-4f50993ac6da'::uuid))
WITH CHECK ((SELECT auth.uid()) IN ('c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid, '74acf117-be21-4460-877d-4f50993ac6da'::uuid));

DROP POLICY IF EXISTS portal_setup_events_delete ON public."Events";
CREATE POLICY portal_setup_events_delete ON public."Events" AS PERMISSIVE FOR DELETE TO authenticated
USING ((SELECT auth.uid()) IN ('c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid, '74acf117-be21-4460-877d-4f50993ac6da'::uuid));

DROP POLICY IF EXISTS portal_setup_events_delete_guard ON public."Events";
CREATE POLICY portal_setup_events_delete_guard ON public."Events" AS RESTRICTIVE FOR DELETE TO authenticated
USING ((SELECT auth.uid()) IN ('c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid, '74acf117-be21-4460-877d-4f50993ac6da'::uuid));

-- Keep the existing legacy function and its transaction/validation logic intact.
-- The wrapper exposes only season closure, never general history writes.
CREATE OR REPLACE FUNCTION public.close_booking_season_authenticated(p_season integer)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog SET lock_timeout='5s'
AS $$
BEGIN
 IF auth.uid() IS NULL OR NOT ((SELECT auth.uid()) IN ('c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid, '74acf117-be21-4460-877d-4f50993ac6da'::uuid)) THEN
   RAISE EXCEPTION USING ERRCODE='42501', MESSAGE='Kun administratorer kan afslutte sæsonen';
 END IF;
 IF p_season IS NULL OR p_season NOT BETWEEN 2026 AND 9999 THEN
   RAISE EXCEPTION 'Ugyldigt sæsonår';
 END IF;
 RETURN public.close_booking_season(p_season);
END $$;
REVOKE ALL ON FUNCTION public.close_booking_season_authenticated(integer) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.close_booking_season_authenticated(integer) TO authenticated;
-- Original privileged close function remains unavailable directly to portal users.
REVOKE EXECUTE ON FUNCTION public.close_booking_season(integer) FROM PUBLIC,anon,authenticated;
NOTIFY pgrst, 'reload schema';
COMMIT;
SELECT policyname,cmd,permissive FROM pg_policies
WHERE schemaname='public' AND policyname LIKE 'portal_setup_%'
ORDER BY tablename,policyname;

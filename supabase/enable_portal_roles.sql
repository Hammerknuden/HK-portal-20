-- Run the entire file as postgres in the ORIGINAL project, BEFORE deploying the new code.
-- Replaces access policies only on the seven portal tables. Booking data is not changed.
BEGIN;
SET LOCAL lock_timeout = '5s';
DO $$ BEGIN
 IF current_user <> 'postgres' THEN RAISE EXCEPTION 'Run as postgres'; END IF;
 IF (SELECT count(*) FROM auth.users WHERE id IN (
 'c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid,
 '74acf117-be21-4460-877d-4f50993ac6da'::uuid,
 '4399ca28-e347-43c5-b22f-6e8be0772f61'::uuid)) <> 3 THEN
 RAISE EXCEPTION 'Wrong project or initial users missing'; END IF;
 IF NOT EXISTS (SELECT 1 FROM storage.buckets WHERE id='guest-registrations' AND NOT public) THEN
 RAISE EXCEPTION 'Expected private guest-registrations bucket'; END IF;
END $$;
CREATE TABLE IF NOT EXISTS public.portal_members (
 user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE RESTRICT,
 role text NOT NULL CHECK (role IN ('admin','user')),
 active boolean NOT NULL DEFAULT true,
 updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.portal_members ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.portal_members FROM PUBLIC,anon,authenticated;
-- Rerunning must never reactivate or promote a changed account.
INSERT INTO public.portal_members(user_id,role) VALUES
 ('c8fb3b6c-00ed-4883-a52f-ef182f10ec3e','admin'),
 ('74acf117-be21-4460-877d-4f50993ac6da','admin'),
 ('4399ca28-e347-43c5-b22f-6e8be0772f61','user')
ON CONFLICT (user_id) DO NOTHING;

CREATE OR REPLACE FUNCTION public.portal_current_role() RETURNS text
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog
AS $$ SELECT role FROM public.portal_members WHERE user_id=auth.uid() AND active $$;
CREATE OR REPLACE FUNCTION public.portal_is_admin() RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog
AS $$ SELECT coalesce(public.portal_current_role()='admin',false) $$;
CREATE OR REPLACE FUNCTION public.portal_is_active() RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog
AS $$ SELECT public.portal_current_role() IS NOT NULL $$;
REVOKE ALL ON FUNCTION public.portal_current_role(),public.portal_is_admin(),public.portal_is_active() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.portal_current_role(),public.portal_is_admin(),public.portal_is_active() TO authenticated,anon;

CREATE OR REPLACE FUNCTION public.portal_list_members()
RETURNS TABLE(user_id uuid,role text,active boolean,updated_at timestamptz)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog
AS $$ BEGIN
 IF NOT public.portal_is_admin() THEN RAISE EXCEPTION USING ERRCODE='42501',MESSAGE='Administrator required'; END IF;
 RETURN QUERY SELECT m.user_id,m.role,m.active,m.updated_at FROM public.portal_members m ORDER BY m.user_id;
END $$;

CREATE OR REPLACE FUNCTION public.portal_set_member(p_user_id uuid,p_role text,p_active boolean,
 p_expected_role text,p_expected_active boolean)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog
AS $$ DECLARE old public.portal_members%rowtype;
BEGIN
 -- Serialize all role changes, then recheck the caller under the lock.
 LOCK TABLE public.portal_members IN SHARE ROW EXCLUSIVE MODE;
 IF NOT public.portal_is_admin() THEN RAISE EXCEPTION USING ERRCODE='42501',MESSAGE='Administrator required'; END IF;
 IF p_role IS NULL OR p_role NOT IN ('admin','user') OR p_active IS NULL THEN RAISE EXCEPTION 'Invalid role/status'; END IF;
 IF NOT EXISTS(SELECT 1 FROM auth.users WHERE id=p_user_id AND email_confirmed_at IS NOT NULL) THEN
 RAISE EXCEPTION 'User must accept the invitation first'; END IF;
 SELECT * INTO old FROM public.portal_members WHERE user_id=p_user_id;
 IF old.role IS DISTINCT FROM p_expected_role OR old.active IS DISTINCT FROM p_expected_active THEN
 RAISE EXCEPTION 'Access changed since preview; reload Setup'; END IF;
 IF old.role='admin' AND old.active AND NOT (p_role='admin' AND p_active)
 AND (SELECT count(*) FROM public.portal_members WHERE role='admin' AND active)<=1 THEN
 RAISE EXCEPTION 'Cannot remove the last active administrator'; END IF;
 INSERT INTO public.portal_members(user_id,role,active) VALUES(p_user_id,p_role,p_active)
 ON CONFLICT(user_id) DO UPDATE SET role=EXCLUDED.role,active=EXCLUDED.active,updated_at=clock_timestamp();
 RETURN jsonb_build_object('user_id',p_user_id,'role',p_role,'active',p_active);
END $$;
REVOKE ALL ON FUNCTION public.portal_list_members(),public.portal_set_member(uuid,text,boolean,text,boolean) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.portal_list_members(),public.portal_set_member(uuid,text,boolean,text,boolean) TO authenticated;

-- Snapshot existing policies once, including Storage, for manual review/recovery.
CREATE SCHEMA IF NOT EXISTS portal_private;
REVOKE ALL ON SCHEMA portal_private FROM PUBLIC,anon,authenticated;
CREATE TABLE IF NOT EXISTS portal_private.role_policy_backup AS SELECT * FROM pg_policies WHERE false;
INSERT INTO portal_private.role_policy_backup
SELECT p.* FROM pg_policies p WHERE
 ((p.schemaname='public' AND p.tablename IN ('hk_dtb','historie_new','bookin_pace','high_season','breakfast_notes','Events','statistik_historik'))
 OR (p.schemaname='storage' AND p.tablename='objects'))
 AND NOT EXISTS(SELECT 1 FROM portal_private.role_policy_backup b WHERE b.schemaname=p.schemaname AND b.tablename=p.tablename AND b.policyname=p.policyname);

DO $$ DECLARE t text; p record; op text; allowed text;
BEGIN
 FOREACH t IN ARRAY ARRAY['hk_dtb','historie_new','bookin_pace','high_season','breakfast_notes','Events','statistik_historik'] LOOP
 IF NOT EXISTS(SELECT 1 FROM pg_class c JOIN pg_namespace n ON c.relnamespace=n.oid WHERE n.nspname='public' AND c.relname=t AND c.relrowsecurity) THEN
 RAISE EXCEPTION 'Missing table or RLS on %',t; END IF;
 FOR p IN SELECT policyname FROM pg_policies WHERE schemaname='public' AND tablename=t LOOP
 EXECUTE format('DROP POLICY %I ON public.%I',p.policyname,t); END LOOP;
 EXECUTE format('GRANT SELECT ON public.%I TO authenticated',t);
 EXECUTE format('CREATE POLICY portal_role_read ON public.%I FOR SELECT TO authenticated USING ((SELECT public.portal_is_active()))',t);
 FOREACH op IN ARRAY ARRAY['INSERT','UPDATE','DELETE'] LOOP
 allowed := CASE
 WHEN t='hk_dtb' AND op IN ('INSERT','UPDATE') THEN 'public.portal_is_active()'
 WHEN t='hk_dtb' AND op='DELETE' THEN 'public.portal_is_admin()'
 WHEN t='breakfast_notes' AND op IN ('INSERT','UPDATE') THEN 'public.portal_is_active()'
 WHEN t='Events' OR (t='high_season' AND op='UPDATE') THEN 'public.portal_is_admin()'
 ELSE NULL END;
 IF allowed IS NOT NULL THEN
 EXECUTE format('CREATE POLICY %I ON public.%I FOR %s TO authenticated %s %s',
 'portal_role_'||lower(op),t,op,
 CASE WHEN op IN ('UPDATE','DELETE') THEN 'USING ((SELECT '||allowed||'))' ELSE '' END,
 CASE WHEN op IN ('INSERT','UPDATE') THEN 'WITH CHECK ((SELECT '||allowed||'))' ELSE '' END);
 END IF;
 END LOOP;
 END LOOP;
END $$;
-- Preserve existing column grants and add the documented application operations.
GRANT INSERT,UPDATE,DELETE ON public.hk_dtb,public."Events" TO authenticated;
GRANT INSERT(dato,"ekstra_gæster",assistance,comments),UPDATE(dato,"ekstra_gæster",assistance,comments) ON public.breakfast_notes TO authenticated;
GRANT UPDATE(enk_low,enk_high,dobb_low,dobb_high,pris_morgenmad,start_season,end_season) ON public.high_season TO authenticated;

-- Storage guard overrides old permissive UID policies, including for disabled users.
DO $$ DECLARE p record; op text; rule text;
BEGIN
 IF EXISTS(SELECT 1 FROM pg_policies WHERE schemaname='storage' AND tablename='objects' AND permissive='RESTRICTIVE' AND policyname NOT LIKE 'portal_role_%') THEN
 RAISE EXCEPTION 'Review existing restrictive Storage policies before migration'; END IF;
 FOREACH op IN ARRAY ARRAY['SELECT','INSERT','UPDATE','DELETE'] LOOP
 rule := CASE WHEN op IN ('SELECT','INSERT') THEN 'public.portal_is_admin()' ELSE 'false' END;
 EXECUTE format('DROP POLICY IF EXISTS %I ON storage.objects','portal_role_storage_'||lower(op));
 EXECUTE format('CREATE POLICY %I ON storage.objects AS RESTRICTIVE FOR %s TO PUBLIC %s %s',
 'portal_role_storage_'||lower(op),op,
 CASE WHEN op IN ('SELECT','UPDATE','DELETE') THEN 'USING (bucket_id <> ''guest-registrations'' OR ('||rule||'))' ELSE '' END,
 CASE WHEN op IN ('INSERT','UPDATE') THEN 'WITH CHECK (bucket_id <> ''guest-registrations'' OR ('||rule||'))' ELSE '' END);
 END LOOP;
END $$;
DROP POLICY IF EXISTS portal_role_guest_read ON storage.objects;
CREATE POLICY portal_role_guest_read ON storage.objects FOR SELECT TO authenticated USING (bucket_id='guest-registrations' AND public.portal_is_admin());
DROP POLICY IF EXISTS portal_role_guest_upload ON storage.objects;
CREATE POLICY portal_role_guest_upload ON storage.objects FOR INSERT TO authenticated WITH CHECK (bucket_id='guest-registrations' AND public.portal_is_admin());

-- Upgrade only the identity predicates in the INSTALLED RPCs: preserve newer business logic.
CREATE TABLE IF NOT EXISTS portal_private.role_function_backup(signature text PRIMARY KEY,definition text NOT NULL);
DO $$ DECLARE sig text; definition text; replacement text; pattern text; changed text;
BEGIN
 FOREACH sig IN ARRAY ARRAY[
 'public.swap_booking_rooms(bigint[],bigint[],integer,integer)',
 'public.apply_optimizer_plan_authenticated(uuid,integer,bigint,jsonb)',
 'public.apply_calendar_moves_authenticated(uuid,integer,jsonb)',
 'public.close_booking_season_authenticated(integer)'] LOOP
 IF to_regprocedure(sig) IS NULL THEN RAISE EXCEPTION 'Required installed function missing: %',sig; END IF;
 SELECT pg_get_functiondef(to_regprocedure(sig)) INTO definition;
 INSERT INTO portal_private.role_function_backup VALUES(sig,definition) ON CONFLICT DO NOTHING;
 IF position('portal_is_active()' IN definition)>0 OR position('portal_is_admin()' IN definition)>0 THEN CONTINUE; END IF;
 IF position('c8fb3b6c-00ed-4883-a52f-ef182f10ec3e' IN definition)=0 OR position('74acf117-be21-4460-877d-4f50993ac6da' IN definition)=0 THEN
 RAISE EXCEPTION 'Unexpected function guard: %',sig; END IF;
 IF sig='public.close_booking_season_authenticated(integer)' THEN
 pattern := '[(]SELECT auth[.]uid[(][)][)] IN [(][^)]*[)]';
 replacement := 'public.portal_is_admin()';
 ELSE
 IF position('4399ca28-e347-43c5-b22f-6e8be0772f61' IN definition)=0 THEN RAISE EXCEPTION 'Unexpected member guard'; END IF;
 pattern := 'auth[.]uid[(][)] IS NULL OR auth[.]uid[(][)] NOT IN [(][^)]*[)]';
 replacement := 'NOT public.portal_is_active()';
 END IF;
 changed := regexp_replace(definition,pattern,replacement,'i');
 IF changed=definition OR position('c8fb3b6c-00ed-4883-a52f-ef182f10ec3e' IN changed)>0 OR position('4399ca28-e347-43c5-b22f-6e8be0772f61' IN changed)>0 THEN
 RAISE EXCEPTION 'Guard replacement failed: %',sig; END IF;
 EXECUTE changed;
 END LOOP;
END $$;
NOTIFY pgrst,'reload schema';
COMMIT;
SELECT user_id,role,active FROM public.portal_members ORDER BY role,user_id;

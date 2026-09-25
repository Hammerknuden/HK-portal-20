-- Booking permissions for the ORIGINAL Supabase project.
-- Run this complete file in SQL Editor. Repeatable; no booking data is changed.
-- Finn and Naja: SELECT/INSERT/UPDATE/DELETE.
-- Ordinary approved user: SELECT/INSERT/UPDATE, including web='cansl'; no DELETE.
-- Other tables, Storage, RPC permissions and legacy service-role access are unchanged.
BEGIN;
LOCK TABLE public.hk_dtb IN SHARE ROW EXCLUSIVE MODE;
DO $$
DECLARE seq_name text;
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND c.relname='hk_dtb' AND c.relrowsecurity
    ) THEN
        RAISE EXCEPTION 'Expected RLS enabled on public.hk_dtb. No changes applied.';
    END IF;
    IF (SELECT count(*) FROM auth.users WHERE id IN (
        'c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid,
        '74acf117-be21-4460-877d-4f50993ac6da'::uuid,
        '4399ca28-e347-43c5-b22f-6e8be0772f61'::uuid
    )) <> 3 THEN
        RAISE EXCEPTION 'Expected three existing portal users. Check project and UIDs.';
    END IF;
    seq_name := pg_get_serial_sequence('public.hk_dtb', 'id');
    IF seq_name IS NOT NULL THEN
        EXECUTE format('GRANT USAGE ON SEQUENCE %s TO authenticated', seq_name);
    END IF;
END $$;

-- Retire only our temporary booking-test policies, if still present.
DROP POLICY IF EXISTS auth_write_probe_insert ON public.hk_dtb;
DROP POLICY IF EXISTS auth_write_probe_update ON public.hk_dtb;
DROP POLICY IF EXISTS auth_booking_300_update ON public.hk_dtb;
DROP POLICY IF EXISTS auth_booking_300_user_update ON public.hk_dtb;
DROP POLICY IF EXISTS auth_booking_301_insert ON public.hk_dtb;

GRANT SELECT, INSERT, UPDATE, DELETE ON public.hk_dtb TO authenticated;

DROP POLICY IF EXISTS portal_booking_select ON public.hk_dtb;
CREATE POLICY portal_booking_select ON public.hk_dtb
AS PERMISSIVE FOR SELECT TO authenticated
USING ((SELECT auth.uid()) IN (
        'c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid,
        '74acf117-be21-4460-877d-4f50993ac6da'::uuid,
        '4399ca28-e347-43c5-b22f-6e8be0772f61'::uuid
    ));

DROP POLICY IF EXISTS portal_booking_insert ON public.hk_dtb;
CREATE POLICY portal_booking_insert ON public.hk_dtb
AS PERMISSIVE FOR INSERT TO authenticated
WITH CHECK ((SELECT auth.uid()) IN (
        'c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid,
        '74acf117-be21-4460-877d-4f50993ac6da'::uuid,
        '4399ca28-e347-43c5-b22f-6e8be0772f61'::uuid
    ));

DROP POLICY IF EXISTS portal_booking_insert_guard ON public.hk_dtb;
CREATE POLICY portal_booking_insert_guard ON public.hk_dtb
AS RESTRICTIVE FOR INSERT TO authenticated
WITH CHECK ((SELECT auth.uid()) IN (
        'c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid,
        '74acf117-be21-4460-877d-4f50993ac6da'::uuid,
        '4399ca28-e347-43c5-b22f-6e8be0772f61'::uuid
    ));

DROP POLICY IF EXISTS portal_booking_update ON public.hk_dtb;
CREATE POLICY portal_booking_update ON public.hk_dtb
AS PERMISSIVE FOR UPDATE TO authenticated
USING ((SELECT auth.uid()) IN (
        'c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid,
        '74acf117-be21-4460-877d-4f50993ac6da'::uuid,
        '4399ca28-e347-43c5-b22f-6e8be0772f61'::uuid
    ))
WITH CHECK ((SELECT auth.uid()) IN (
        'c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid,
        '74acf117-be21-4460-877d-4f50993ac6da'::uuid,
        '4399ca28-e347-43c5-b22f-6e8be0772f61'::uuid
    ));

DROP POLICY IF EXISTS portal_booking_update_guard ON public.hk_dtb;
CREATE POLICY portal_booking_update_guard ON public.hk_dtb
AS RESTRICTIVE FOR UPDATE TO authenticated
USING ((SELECT auth.uid()) IN (
        'c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid,
        '74acf117-be21-4460-877d-4f50993ac6da'::uuid,
        '4399ca28-e347-43c5-b22f-6e8be0772f61'::uuid
    ))
WITH CHECK ((SELECT auth.uid()) IN (
        'c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid,
        '74acf117-be21-4460-877d-4f50993ac6da'::uuid,
        '4399ca28-e347-43c5-b22f-6e8be0772f61'::uuid
    ));

DROP POLICY IF EXISTS portal_booking_delete ON public.hk_dtb;
CREATE POLICY portal_booking_delete ON public.hk_dtb
AS PERMISSIVE FOR DELETE TO authenticated
USING ((SELECT auth.uid()) IN (
        'c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid,
        '74acf117-be21-4460-877d-4f50993ac6da'::uuid
    ));

DROP POLICY IF EXISTS portal_booking_delete_guard ON public.hk_dtb;
CREATE POLICY portal_booking_delete_guard ON public.hk_dtb
AS RESTRICTIVE FOR DELETE TO authenticated
USING ((SELECT auth.uid()) IN (
        'c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid,
        '74acf117-be21-4460-877d-4f50993ac6da'::uuid
    ));

COMMIT;

-- Result rows confirm the installed policies, rather than "No rows returned".
SELECT policyname, permissive, roles, cmd, qual, with_check
FROM pg_policies
WHERE schemaname='public' AND tablename='hk_dtb'
  AND policyname LIKE 'portal_booking_%'
ORDER BY policyname;

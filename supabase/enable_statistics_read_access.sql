-- Read-only statistics access in the original Supabase project.
BEGIN;
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND c.relname='statistik_historik' AND c.relrowsecurity) THEN
        RAISE EXCEPTION 'Expected statistik_historik with RLS enabled';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_proc WHERE oid=to_regprocedure('public.calculate_season_statistics(integer)')
        AND NOT prosecdef AND provolatile='s') THEN
        RAISE EXCEPTION 'Expected STABLE SECURITY INVOKER statistics function';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_proc WHERE oid=to_regprocedure('public.statistik_number(text)')
        AND NOT prosecdef AND provolatile='i') THEN
        RAISE EXCEPTION 'Expected IMMUTABLE SECURITY INVOKER numeric helper';
    END IF;
END $$;
GRANT SELECT ON public.statistik_historik TO authenticated;
DROP POLICY IF EXISTS portal_statistics_read ON public.statistik_historik;
CREATE POLICY portal_statistics_read ON public.statistik_historik
FOR SELECT TO authenticated USING (
    (SELECT auth.uid()) IN (
        'c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid,
        '74acf117-be21-4460-877d-4f50993ac6da'::uuid,
        '4399ca28-e347-43c5-b22f-6e8be0772f61'::uuid
    )
);
-- These invoker functions retain the caller's RLS permissions on source tables.
GRANT EXECUTE ON FUNCTION public.statistik_number(text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.calculate_season_statistics(integer) TO authenticated;
COMMIT;
-- No grant on close_booking_season; no data or Storage changes.
SELECT policyname, cmd FROM pg_policies
WHERE schemaname='public' AND tablename='statistik_historik'
AND policyname='portal_statistics_read';

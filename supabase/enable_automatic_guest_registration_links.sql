-- Enable Supabase Cron (pg_cron) under Integrations before running this file.
-- Run as postgres in the ORIGINAL project SQL Editor. No PDF deletion.
BEGIN;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname='pg_cron') THEN
    RAISE EXCEPTION 'Enable pg_cron under Integrations / Cron, then run this file again';
  END IF;
  IF current_user <> 'postgres' THEN
    RAISE EXCEPTION 'Run as postgres in SQL Editor';
  END IF;
END $$;

CREATE OR REPLACE FUNCTION public.link_guest_registration_history()
RETURNS bigint LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog
AS $function$
DECLARE linked bigint;
BEGIN
  -- Serialise our runs; never wait behind a long-running writer.
  IF NOT pg_try_advisory_xact_lock(202526, 148) THEN RETURN 0; END IF;
  WITH parsed AS (
    SELECT o.name, regexp_match(o.name, '^(2025|2026)/(2025|2026)-([0-9]+)[.]pdf$') AS parts
    FROM storage.objects o
    WHERE o.bucket_id='guest-registrations'
  ), files AS (
    SELECT name, parts[1] AS season_key,
      coalesce(nullif(ltrim(parts[3], '0'), ''), '0') AS booking_key
    FROM parsed WHERE parts IS NOT NULL AND parts[1]=parts[2]
  ), unique_files AS (
    SELECT season_key, booking_key, min(name) AS path
    FROM files GROUP BY season_key, booking_key HAVING count(*)=1
  ), unique_history AS (
    SELECT season, booking_nr FROM public.historie_new
    WHERE season IN (2025,2026) AND booking_nr IS NOT NULL
    GROUP BY season, booking_nr HAVING count(*)=1
  ), updated AS (
    UPDATE public.historie_new h SET storage_path=f.path
    FROM unique_history u, unique_files f
    WHERE h.season=u.season AND h.booking_nr=u.booking_nr
      AND f.season_key=h.season::text AND f.booking_key=h.booking_nr::text
      AND nullif(btrim(h.storage_path),'') IS NULL
    RETURNING h.id
  ) SELECT count(*) INTO linked FROM updated;
  RETURN linked;
END $function$;

REVOKE ALL ON FUNCTION public.link_guest_registration_history() FROM PUBLIC, anon, authenticated;
-- A named schedule is updated on re-run, not duplicated for the same owner.
SELECT cron.schedule('hk-link-guest-registrations', '*/5 * * * *',
  'SELECT public.link_guest_registration_history();');
-- Initial run also links any already uploaded 2025 PDFs.
SELECT public.link_guest_registration_history() AS nye_koblinger;
COMMIT;
SELECT jobid, jobname, schedule, active FROM cron.job
WHERE jobname='hk-link-guest-registrations';

-- Original Supabase project: remove ONLY the completed booking-test policies/indexes.
-- No booking rows, tables, general SELECT policies or Storage policies are changed.
-- Repeatable. Legacy access is not changed by this cleanup.
begin;
drop policy if exists auth_write_probe_insert on public.hk_dtb;
drop policy if exists auth_write_probe_update on public.hk_dtb;
drop policy if exists auth_booking_300_update on public.hk_dtb;
drop policy if exists auth_booking_300_user_update on public.hk_dtb;
drop policy if exists auth_booking_301_insert on public.hk_dtb;
drop index if exists public.auth_write_probe_single_booking;
drop index if exists public.auth_booking_301_single_row;
commit;
-- Inspection only: the original 2099 test row may still need manual cleanup.
select id, season, booking_number, navn from public.hk_dtb
where (season=2099 and booking_number=99999)
   or (season=2026 and booking_number in (300,301));

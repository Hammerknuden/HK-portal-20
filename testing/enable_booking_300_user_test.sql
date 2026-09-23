-- Run once in the original Supabase project after the admin booking-300 test.
-- Adds UPDATE for the ordinary test user on this test row only.
begin;
lock table public.hk_dtb in share row exclusive mode;
do $$
declare test_id bigint;
begin
  if not exists (select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace
    where n.nspname='public' and c.relname='hk_dtb' and c.relrowsecurity) then
    raise exception 'RLS must be enabled';
  end if;
  if not exists (select 1 from auth.users where id='4399ca28-e347-43c5-b22f-6e8be0772f61'::uuid) then
    raise exception 'Ordinary test user not found';
  end if;
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='hk_dtb'
    and policyname='auth_booking_300_update' and cmd='UPDATE') then
    raise exception 'Existing administrator test policy not found';
  end if;
  if exists (select 1 from pg_policies where schemaname='public' and tablename='hk_dtb'
    and cmd in ('ALL','INSERT','UPDATE','DELETE') and policyname not in
    ('auth_booking_300_update','auth_write_probe_insert','auth_write_probe_update')) then
    raise exception 'Unexpected write policy exists; inspect before continuing';
  end if;
  if (select count(*) from public.hk_dtb where season=2026 and booking_number=300) <> 1 then
    raise exception 'Expected exactly one row for booking 300';
  end if;
  select id into test_id from public.hk_dtb where season=2026 and booking_number=300 and navn='NN'
    and checkin_date >= date '2026-10-01' and checkout_date <= date '2026-11-01'
    and checkout_date > checkin_date;
  if test_id is null then raise exception 'Booking name or October dates do not match'; end if;
  execute format($policy$
    create policy auth_booking_300_user_update on public.hk_dtb for update to authenticated
    using (id=%s and season=2026 and booking_number=300 and navn='NN'
      and (select auth.uid())='4399ca28-e347-43c5-b22f-6e8be0772f61'::uuid)
    with check (id=%s and season=2026 and booking_number=300 and navn='NN'
      and checkin_date >= date '2026-10-01' and checkout_date <= date '2026-11-01'
      and checkout_date > checkin_date
      and (select auth.uid())='4399ca28-e347-43c5-b22f-6e8be0772f61'::uuid)
  $policy$, test_id, test_id);
end $$;
grant update on public.hk_dtb to authenticated;
commit;
-- Cleanup after testing:
-- DROP POLICY auth_booking_300_user_update ON public.hk_dtb;

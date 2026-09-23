-- Original Supabase project. Enables UPDATE on the existing test row only.
begin;
lock table public.hk_dtb in share row exclusive mode;
do $$
declare test_id bigint;
begin
  if not exists (select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace
    where n.nspname='public' and c.relname='hk_dtb' and c.relrowsecurity) then
    raise exception 'RLS must be enabled';
  end if;
  if (select count(*) from public.hk_dtb where season=2026 and booking_number=300) <> 1 then
    raise exception 'Expected exactly one row for booking 300, season 2026';
  end if;
  select id into test_id from public.hk_dtb where season=2026 and booking_number=300
    and navn='NN' and checkin_date=date '2026-10-01' and checkout_date=date '2026-10-04';
  if test_id is null then raise exception 'Name or dates do not match the agreed test booking'; end if;
  if exists (select 1 from pg_policies where schemaname='public' and tablename='hk_dtb'
    and cmd in ('ALL','UPDATE','INSERT','DELETE')
    and policyname not in ('auth_write_probe_insert','auth_write_probe_update')) then
    raise exception 'Unexpected write policies exist; inspect before continuing';
  end if;
  execute format($policy$
    create policy auth_booking_300_update on public.hk_dtb for update to authenticated
    using (id=%s and season=2026 and booking_number=300 and navn='NN'
      and (select auth.uid()) in ('c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid,
                                '74acf117-be21-4460-877d-4f50993ac6da'::uuid))
    with check (id=%s and season=2026 and booking_number=300 and navn='NN'
      and checkin_date >= date '2026-10-01' and checkout_date <= date '2026-11-01'
      and checkout_date > checkin_date
      and (select auth.uid()) in ('c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid,
                                '74acf117-be21-4460-877d-4f50993ac6da'::uuid))
  $policy$, test_id, test_id);
end $$;
grant update on public.hk_dtb to authenticated;
commit;
-- After testing: DROP POLICY auth_booking_300_update ON public.hk_dtb;
-- This does not delete the booking. Remove it later through legacy.

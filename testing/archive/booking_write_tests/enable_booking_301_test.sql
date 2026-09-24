-- Run once in the ORIGINAL project; creates no booking itself.
begin;
lock table public.hk_dtb in share row exclusive mode;
do $$
declare seq_name text;
begin
  if not exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace
    where n.nspname='public' and c.relname='hk_dtb' and c.relrowsecurity) then
    raise exception 'RLS must be enabled';
  end if;
  if exists(select 1 from public.hk_dtb where season=2026 and booking_number=301) then
    raise exception 'Booking 301 already exists. Stop and inspect it';
  end if;
  if (select count(*) from auth.users where id in (
    'c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid,
    '74acf117-be21-4460-877d-4f50993ac6da'::uuid,
    '4399ca28-e347-43c5-b22f-6e8be0772f61'::uuid)) <> 3 then
    raise exception 'Expected users not found';
  end if;
  if exists(select 1 from pg_policies where schemaname='public' and tablename='hk_dtb'
    and cmd in ('ALL','INSERT') and policyname <> 'auth_write_probe_insert') then
    raise exception 'Unexpected INSERT policy exists. Inspect before proceeding';
  end if;
  seq_name := pg_get_serial_sequence('public.hk_dtb','id');
  if seq_name is not null then execute format('grant usage on sequence %s to authenticated',seq_name); end if;
end $$;
create unique index auth_booking_301_single_row on public.hk_dtb(season,booking_number)
where season=2026 and booking_number=301;
grant select, insert on public.hk_dtb to authenticated;
create policy auth_booking_301_insert on public.hk_dtb for insert to authenticated
with check (
  (select auth.uid()) in ('c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid,
                         '74acf117-be21-4460-877d-4f50993ac6da'::uuid,
                         '4399ca28-e347-43c5-b22f-6e8be0772f61'::uuid)
  and season=2026 and booking_number=301 and navn='AA'
  and checkin_date=date '2026-10-02' and checkout_date=date '2026-10-06'
  and numb_rooms=1 and room_number=7
);
commit;
-- After testing, disable ENABLE_BOOKING_301_TEST, then:
-- DROP POLICY auth_booking_301_insert ON public.hk_dtb;
-- DROP INDEX public.auth_booking_301_single_row;
-- Delete the test booking through legacy when finished.

-- Manual setup in the ORIGINAL Supabase project. No booking is inserted here.
-- Grants INSERT/UPDATE only for the two named admins and a fixed test booking.
begin;
lock table public.hk_dtb in share row exclusive mode;
do $$
declare seq_name text;
begin
    if not exists (select 1 from pg_class c join pg_namespace n on n.oid = c.relnamespace
                   where n.nspname = 'public' and c.relname = 'hk_dtb' and c.relrowsecurity) then
        raise exception 'RLS must already be enabled on hk_dtb';
    end if;
    if (select count(*) from auth.users where id in (
        'c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid,
        '74acf117-be21-4460-877d-4f50993ac6da'::uuid)) <> 2 then
        raise exception 'The two administrators were not found. Check the project.';
    end if;
    if exists (select 1 from public.hk_dtb where season = 2099 and booking_number = 99999) then
        raise exception 'Test number already exists. Stop and inspect it before setup.';
    end if;
    if exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'hk_dtb'
               and cmd in ('ALL', 'INSERT', 'UPDATE', 'DELETE')) then
        raise exception 'Write policies already exist. Review before enabling the test.';
    end if;
    -- Serial sequences need USAGE separately from table privileges.
    seq_name := pg_get_serial_sequence('public.hk_dtb', 'id');
    if seq_name is not null then
        execute format('grant usage on sequence %s to authenticated', seq_name);
    end if;
end $$;

-- Prevent duplicate test rows, including concurrent clicks from two users.
create unique index auth_write_probe_single_booking
    on public.hk_dtb (season, booking_number)
    where season = 2099 and booking_number = 99999;

grant select, insert, update on public.hk_dtb to authenticated;

create policy auth_write_probe_insert on public.hk_dtb
for insert to authenticated with check (
    (select auth.uid()) in ('c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid,
                           '74acf117-be21-4460-877d-4f50993ac6da'::uuid)
    and season = 2099 and booking_number = 99999
    and navn = 'AUTH WRITE TEST - NOT A GUEST'
    and web = 'cansl' and room_number = 7
    and checkin_date = date '2099-01-01' and checkout_date = date '2099-01-02'
    and booking_date = date '2099-01-01'
    and numb_rooms = 1 and numb_guests = 0 and pris = '0'
    and movable = false and email is null and telefon is null
);

create policy auth_write_probe_update on public.hk_dtb
for update to authenticated
using (
    (select auth.uid()) in ('c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid,
                           '74acf117-be21-4460-877d-4f50993ac6da'::uuid)
    and season = 2099 and booking_number = 99999
    and navn = 'AUTH WRITE TEST - NOT A GUEST' and web = 'cansl'
)
with check (
    (select auth.uid()) in ('c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid,
                           '74acf117-be21-4460-877d-4f50993ac6da'::uuid)
    and season = 2099 and booking_number = 99999
    and navn = 'AUTH WRITE TEST - NOT A GUEST'
    and web = 'cansl' and room_number = 7
    and checkin_date = date '2099-01-01' and checkout_date = date '2099-01-02'
    and booking_date = date '2099-01-01'
    and numb_rooms = 1 and numb_guests = 0 and pris = '0'
    and movable = false and email is null and telefon is null
);
commit;

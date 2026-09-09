-- Run after 20260909_booking_pace_season_status.sql.
-- One transaction copies/finalizes history and switches the pace source.
-- Original hk_dtb rows are retained. Never called by the migration itself.
begin;

-- The application uses spouse; older schema migrations used spouce.
alter table public.historie_new add column if not exists spouse text;

create or replace function public.close_booking_season(p_season integer)
returns jsonb
language plpgsql
security invoker
set search_path = pg_catalog, public, pg_temp
as $function$
begin
    if p_season is null or p_season < 2026 then
        raise exception 'Kun sæsoner fra 2026 kan afsluttes her.';
    end if;
    -- Block concurrent booking/history writes throughout copying and validation.
    lock table public.high_season in share row exclusive mode;
    lock table public.hk_dtb in share row exclusive mode;
    lock table public.historie_new in share row exclusive mode;
    if not exists (select 1 from public.high_season where season = p_season) then
        raise exception 'Sæsonen findes ikke i sæsonopsætningen.';
    end if;
    if exists (select 1 from public.high_season where season = p_season and pace_archived) then
        return jsonb_build_object('season', p_season, 'already_archived', true);
    end if;

create temporary table close_season_source on commit drop as
select *,
    bool_or(regexp_replace(lower(coalesce(web, '')), '[^a-z0-9]', '', 'g') = 'cansl')
        over (partition by season, booking_number) as is_cancelled
from public.hk_dtb
where season = p_season;

    if exists (
        select 1 from close_season_source
        where booking_number is null
           or booking_number < 1 or booking_number > 2147483647
    ) then
        raise exception 'Invalid or missing booking number. Nothing has been copied.';
    end if;
    if exists (
        select 1 from close_season_source
        where (not is_cancelled and (checkin_date is null or checkout_date is null
                                    or checkout_date <= checkin_date))
           or checkout_date < checkin_date
    ) then
        raise exception 'Invalid stay dates. Nothing has been copied.';
    end if;
    if exists (
        select booking_number from close_season_source
        group by booking_number
        having count(distinct booking_date) > 1
    ) then
        raise exception 'A booking has multiple booking dates. Review before copying.';
    end if;

-- Group metadata by booking. Prefer a row carrying the original booking date,
-- then the lowest source ID. Empty fields are filled from other booking rows.
create temporary table close_season_bookings on commit drop as
select
    season,
    booking_number::integer as booking_nr,
    (array_agg(nullif(btrim(navn), '') order by booking_date is null, id)
        filter (where nullif(btrim(navn), '') is not null))[1] as navn,
    (array_agg(nullif(btrim(familie_navn), '') order by booking_date is null, id)
        filter (where nullif(btrim(familie_navn), '') is not null))[1] as familie_navn,
    case when bool_and(is_cancelled) then min(checkin_date)
         else min(checkin_date) filter (where not is_cancelled) end as indcheck,
    case when bool_and(is_cancelled) then max(checkout_date)
         else max(checkout_date) filter (where not is_cancelled) end as udcheck,
    min(booking_date) as booking_date,
    (array_agg(nullif(btrim(nation), '') order by booking_date is null, id)
        filter (where nullif(btrim(nation), '') is not null))[1] as nationalitet,
    case when bool_and(is_cancelled) then 'cansl' else
        (array_agg(nullif(btrim(web), '') order by booking_date is null, id)
         filter (where not is_cancelled and nullif(btrim(web), '') is not null))[1]
    end as web,
    (array_agg(nullif(btrim(email), '') order by booking_date is null, id)
        filter (where nullif(btrim(email), '') is not null))[1] as email,
    (array_agg(nullif(btrim(telefon), '') order by booking_date is null, id)
        filter (where nullif(btrim(telefon), '') is not null))[1] as phone,
    (array_agg(nullif(btrim(spouse), '') order by booking_date is null, id)
        filter (where nullif(btrim(spouse), '') is not null))[1] as spouse,
    string_agg(distinct nullif(btrim(comments), ''), E'\n') as comments,
    bool_and(is_cancelled) as fully_cancelled,
    coalesce(sum(checkout_date - checkin_date)
        filter (where not is_cancelled), 0)::integer as room_nights
from close_season_source
group by season, booking_number;

    if exists (select 1 from close_season_bookings where navn is null) then
        raise exception 'A booking has no guest name. Nothing has been copied.';
    end if;

-- Combine arrivals and departures on the same day BEFORE calculating occupancy.
-- A room switch on checkout day must not count as two simultaneous rooms.
create temporary table close_season_rooms on commit drop as
with events as (
    select booking_number, checkin_date as day, 1 as delta
    from close_season_source where not is_cancelled
    union all
    select booking_number, checkout_date as day, -1 as delta
    from close_season_source where not is_cancelled
), daily as (
    select booking_number, day, sum(delta) as delta
    from events group by booking_number, day
), occupancy as (
    select booking_number,
        sum(delta) over (partition by booking_number order by day
                        rows unbounded preceding) as rooms
    from daily
)
select booking_number, max(rooms)::integer as num_rooms
from occupancy group by booking_number;


if not exists (select 1 from close_season_source) then
    raise exception 'Sæsonen har ingen bookinger i hk_dtb.';
end if;
if exists (select 1 from close_season_bookings where booking_date is null and not fully_cancelled) then
    raise exception 'Der mangler bookingdatoer. Sæsonen er ikke afsluttet.';
end if;
if exists (
    select booking_nr from public.historie_new where season = p_season
    group by booking_nr having count(*) > 1
) then
    raise exception 'Historikken har dublerede bookingnumre. Sæsonen er ikke afsluttet.';
end if;
-- Existing pre-copies must match the final source; documents and guest metadata
-- are retained. Refuse unexplained extra history bookings rather than erase them.
if exists (
    select 1 from public.historie_new h where h.season = p_season
    and not exists (select 1 from close_season_bookings b where b.booking_nr = h.booking_nr)
) then
    raise exception 'Historikken har bookinger, som mangler i hk_dtb. Afstem sæsonen først.';
end if;

update public.historie_new h
set booking_date = b.booking_date, indcheck = b.indcheck, udcheck = b.udcheck,
    web = b.web, num_rooms = coalesce(r.num_rooms, 0), room_nights = b.room_nights
from close_season_bookings b
left join close_season_rooms r on r.booking_number = b.booking_nr
where h.season = p_season and h.booking_nr = b.booking_nr;

insert into public.historie_new (
    season, booking_nr, navn, familie_navn, indcheck, udcheck,
    booking_date, nationalitet, web, email, phone, spouse, comments,
    num_rooms, room_nights
)
select b.season, b.booking_nr, b.navn, b.familie_navn, b.indcheck, b.udcheck,
    b.booking_date, b.nationalitet, b.web, b.email, b.phone, b.spouse, b.comments,
    coalesce(r.num_rooms, 0), b.room_nights
from close_season_bookings b
left join close_season_rooms r on r.booking_number = b.booking_nr
where not exists (
    select 1 from public.historie_new h
    where h.season = p_season and h.booking_nr = b.booking_nr
);

if (select count(*) from public.historie_new where season = p_season)
    <> (select count(*) from close_season_bookings)
   or (select coalesce(sum(room_nights), 0) from public.historie_new where season = p_season)
    <> (select coalesce(sum(room_nights), 0) from close_season_bookings) then
    raise exception 'Afstemning af historikken fejlede. Ingen ændringer er gemt.';
end if;

update public.high_season set pace_archived = true where season = p_season;
return jsonb_build_object(
    'season', p_season, 'already_archived', false,
    'bookings', (select count(*) from close_season_bookings),
    'room_nights', (select coalesce(sum(room_nights), 0) from close_season_bookings)
);
end;
$function$;

-- Setup uses the server-side database client after require_admin().
revoke all on function public.close_booking_season(integer) from public, anon, authenticated;
grant execute on function public.close_booking_season(integer) to service_role;
commit;

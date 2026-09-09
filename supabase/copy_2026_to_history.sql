-- Manual COPY of 2026. Never deletes or updates hk_dtb.
-- Existing historie_new bookings (including storage_path) are skipped.
-- This is a snapshot, not an ongoing synchronization.
begin;

-- Serialize history writers while checking for existing bookings.
lock table public.historie_new in share row exclusive mode;

create temporary table copy_2026_source on commit drop as
select *,
    regexp_replace(lower(coalesce(web, '')), '[^a-z0-9]', '', 'g') = 'cansl'
        as is_cancelled
from public.hk_dtb
where season = 2026;

do $$
begin
    if exists (
        select 1 from copy_2026_source
        where booking_number is null
           or booking_number < 1 or booking_number > 2147483647
    ) then
        raise exception 'Invalid or missing booking number. Nothing has been copied.';
    end if;
    if exists (
        select 1 from copy_2026_source
        where (not is_cancelled and (checkin_date is null or checkout_date is null
                                    or checkout_date <= checkin_date))
           or checkout_date < checkin_date
    ) then
        raise exception 'Invalid stay dates. Nothing has been copied.';
    end if;
    if exists (
        select booking_number from copy_2026_source
        group by booking_number
        having count(distinct booking_date) > 1
    ) then
        raise exception 'A booking has multiple booking dates. Review before copying.';
    end if;
end $$;

-- Group metadata by booking. Prefer a row carrying the original booking date,
-- then the lowest source ID. Empty fields are filled from other booking rows.
create temporary table copy_2026_bookings on commit drop as
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
from copy_2026_source
group by season, booking_number;

do $$
begin
    if exists (select 1 from copy_2026_bookings where navn is null) then
        raise exception 'A booking has no guest name. Nothing has been copied.';
    end if;
end $$;

-- Combine arrivals and departures on the same day BEFORE calculating occupancy.
-- A room switch on checkout day must not count as two simultaneous rooms.
create temporary table copy_2026_rooms on commit drop as
with events as (
    select booking_number, checkin_date as day, 1 as delta
    from copy_2026_source where not is_cancelled
    union all
    select booking_number, checkout_date as day, -1 as delta
    from copy_2026_source where not is_cancelled
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

-- Leave automatic ID, created_at, deleted_at and storage_path to their defaults.
-- No guessed document paths are assigned. No existing row is overwritten.
create temporary table copy_2026_inserted (
    booking_nr integer, web text, num_rooms integer, room_nights integer
) on commit drop;

with inserted as (
    insert into public.historie_new (
        season, booking_nr, navn, familie_navn, indcheck, udcheck,
        booking_date, nationalitet, web, email, phone, spouse, comments,
        num_rooms, room_nights
    )
    select b.season, b.booking_nr, b.navn, b.familie_navn, b.indcheck, b.udcheck,
        b.booking_date, b.nationalitet, b.web, b.email, b.phone, b.spouse, b.comments,
        coalesce(r.num_rooms, 0), b.room_nights
    from copy_2026_bookings b
    left join copy_2026_rooms r on r.booking_number = b.booking_nr
    where not exists (
        select 1 from public.historie_new h
        where h.season = b.season and h.booking_nr = b.booking_nr
    )
    returning booking_nr, web, num_rooms, room_nights
)
insert into copy_2026_inserted select * from inserted;

-- Only counts, not personal data, are returned for verification.
select
    (select count(*) from copy_2026_source) as source_room_rows,
    (select count(*) from copy_2026_bookings) as source_bookings,
    count(*) as copied_bookings,
    (select count(*) from copy_2026_bookings) - count(*) as existing_bookings_skipped,
    count(*) filter (where web = 'cansl') as copied_cancelled_bookings,
    coalesce(sum(room_nights), 0) as copied_room_nights,
    (select count(*) from copy_2026_bookings where booking_date is null)
        as source_bookings_without_booking_date
from copy_2026_inserted;

commit;

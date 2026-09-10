-- Kør efter 20260910_create_statistik_historik.sql og 20260910_close_booking_season.sql.
-- Installerer beregninger og fælles afslutning. Afslutter ikke nogen sæson.
begin;

create or replace function public.statistik_number(p_value text)
returns numeric language sql immutable security invoker
set search_path = pg_catalog
as $$
    select case when replace(btrim(p_value), ',', '.') ~ '^[+-]?[0-9]+([.][0-9]+)?$'
        then replace(btrim(p_value), ',', '.')::numeric else null end;
$$;

create or replace function public.calculate_season_statistics(p_season integer)
returns table(report_type text, data jsonb, metadata jsonb)
language sql stable security invoker
set search_path = pg_catalog, public
as $stats$
with source as materialized (
    select h.*, bool_or(regexp_replace(lower(coalesce(web, '')), '[^a-z0-9]', '', 'g') = 'cansl')
        over (partition by season, coalesce(booking_number::text, 'row:' || id::text)) as cancelled
    from public.hk_dtb h where season = p_season
), active as materialized (
    select *, checkout_date - checkin_date as nights,
        public.statistik_number(pris::text) as amount,
        public.statistik_number(numb_guests::text) as guests,
        upper(btrim(coalesce(nation, ''))) as country,
        case when upper(btrim(coalesce(web, ''))) = 'BC' then 'Booking.com' else 'Egne bookinger' end as channel,
        upper(btrim(coalesce(known, ''))) in ('Y', 'YY') as is_returning,
        upper(btrim(coalesce(morgenmad, ''))) = 'Y' as breakfast,
        case when lower(btrim(coalesce(web, ''))) = 'web' then
            public.statistik_number(substring(replace(coalesce(rabat::text, '0'), ',', '.') from '(-?[0-9]+(?:[.][0-9]+)?)'))
        else 0 end as discount
    from source where not cancelled
), valid as materialized (
    select * from active where nights > 0
), price as (
    select public.statistik_number(pris_morgenmad::text) as breakfast_price
    from public.high_season where season = p_season
), meta as (
    select jsonb_build_object(
        'source', 'hk_dtb', 'revenue_month_basis', 'checkout_date', 'currency', 'DKK',
        'breakfast_price', (select breakfast_price from price), 'vat_rate', 0.25,
        'source_rows', (select count(*) from source),
        'missing_country_rows', (select count(*) from valid where country = ''),
        'invalid_rows', (select count(*) from active where nights is null or nights <= 0
            or amount is null or guests is null or guests < 0
            or (breakfast and (discount is null or coalesce((select breakfast_price from price), -1) < 0)))
    ) as value
), countries as (
    select case when country in ('DK','DE','SE','NO','NL') then country else 'ANDRE' end as country_group,
        sum(coalesce(guests, 0)) as arrivals, sum(coalesce(guests, 0) * nights) as guest_nights
    from valid where country <> '' group by 1
), channels as (
    select channel, sum(nights) as room_nights from valid group by channel
), returning_guests as (
    select case when is_returning then 'Tidligere besøgende' else 'Øvrige egne bookinger' end as guest_group,
        sum(nights) as room_nights from valid where channel = 'Egne bookinger' group by 1
), revenue as (
    select extract(month from checkout_date)::integer as month, sum(coalesce(amount,0)) as gross_revenue
    from valid group by 1
), breakfast_nights as (
    select extract(month from d.day)::integer as month, coalesce(v.guests,0) as servings,
        coalesce(v.guests,0) * coalesce((select breakfast_price from price),0)
        * (1 - greatest(0, least(1, case when abs(v.discount) > 1 then v.discount / 100 else v.discount end))) / 1.25 as net_revenue
    from valid v
    cross join lateral generate_series(v.checkin_date::timestamp, (v.checkout_date - 1)::timestamp, interval '1 day') d(day)
    where v.breakfast
), breakfast_totals as (
    select month, sum(servings) as servings, sum(net_revenue) as net_revenue
    from breakfast_nights group by month
), checkins as (
    select checkin_date as date, count(distinct coalesce(booking_number::text, 'row:' || id::text)) as checkins
    from valid group by checkin_date
), lengths as (
    select extract(month from checkin_date)::integer as month,
        count(*) as stay_count, sum(nights) as total_nights
    from valid group by 1
), reports as (
    select 'room_nights'::text as report_type,
        jsonb_build_array(jsonb_build_object('room_nights', (select coalesce(sum(nights),0) from valid))) as data
    union all select 'danmarks_statistik', coalesce((select jsonb_agg(to_jsonb(c) order by country_group) from countries c), '[]'::jsonb)
    union all select 'booking_channels', coalesce((select jsonb_agg(to_jsonb(c) order by channel) from channels c), '[]'::jsonb)
    union all select 'returning_guests', coalesce((select jsonb_agg(to_jsonb(c) order by guest_group) from returning_guests c), '[]'::jsonb)
    union all select 'gross_revenue_monthly', (
        select jsonb_agg(jsonb_build_object('month', m, 'gross_revenue', coalesce(r.gross_revenue,0)) order by m)
        from generate_series(1,12) m left join revenue r on r.month = m)
    union all select 'breakfast_monthly', (
        select jsonb_agg(jsonb_build_object('month', m, 'servings', coalesce(b.servings,0), 'net_revenue', coalesce(b.net_revenue,0)) order by m)
        from generate_series(1,12) m left join breakfast_totals b on b.month = m)
    union all select 'checkins_daily', coalesce((select jsonb_agg(to_jsonb(c) order by date) from checkins c), '[]'::jsonb)
    union all select 'booking_length_monthly', coalesce((select jsonb_agg(to_jsonb(c) order by month) from lengths c), '[]'::jsonb)
)
select r.report_type, r.data, meta.value from reports r cross join meta;
$stats$;

revoke all on function public.statistik_number(text) from public, anon, authenticated;
revoke all on function public.calculate_season_statistics(integer) from public, anon, authenticated;
grant execute on function public.statistik_number(text) to service_role;
grant execute on function public.calculate_season_statistics(integer) to service_role;

-- Kendte historiske tal: øvrige måneder er ukendte, ikke nul.
insert into public.statistik_historik (season, report_type, data, metadata)
select year, 'gross_revenue_monthly', jsonb_agg(jsonb_build_object('month', month, 'gross_revenue', amount) order by month),
    '{"source":"legacy_statistics_page","currency":"DKK","known_months":[5,6,7,8,9]}'::jsonb
from (values
    (2024,5,86980),(2024,6,143719),(2024,7,151706),(2024,8,146913),(2024,9,107810),
    (2025,5,78599),(2025,6,121385),(2025,7,146531),(2025,8,159691),(2025,9,104591)
) v(year, month, amount)
group by year on conflict (season, report_type) do nothing;

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
    lock table public.statistik_historik in share row exclusive mode;
    -- Complete historical snapshots are immutable on repeated button clicks.
    if (select count(*) from public.statistik_historik where season = p_season) = 8 then
        if not exists (select 1 from public.high_season where season = p_season and pace_archived) then
            raise exception 'Statistik findes allerede, men sæsonstatus er åben. Afstem status først.';
        end if;
        return jsonb_build_object('season', p_season, 'already_archived', true);
    end if;
    if exists (select 1 from public.statistik_historik where season = p_season) then
        raise exception 'Statistikhistorikken er ufuldstændig. Ingen eksisterende tal overskrives.';
    end if;
    if not exists (select 1 from public.hk_dtb where season = p_season) then
        raise exception 'Der er ingen kildedata til sæsonens statistik.';
    end if;
    if exists (select 1 from public.calculate_season_statistics(p_season)
               where (metadata->>'invalid_rows')::integer > 0) then
        raise exception 'Ugyldige datoer, priser, gæsteantal eller morgenmadsoplysninger. Ret data før afslutning.';
    end if;
    insert into public.statistik_historik (season, report_type, data, metadata)
    select p_season, report_type, data, metadata from public.calculate_season_statistics(p_season);

    -- 2026 was copied previously. Freeze statistics without touching its bookings.
    if p_season = 2026 then
        if not exists (select 1 from public.historie_new where season = p_season) then
            raise exception 'Bookinghistorikken for 2026 mangler. Statistikken er ikke gemt.';
        end if;
        if exists (select 1 from public.historie_new where season = p_season
            and regexp_replace(lower(coalesce(web, '')), '[^a-z0-9]', '', 'g') <> 'cansl'
            and (booking_date is null or room_nights is null)) then
            raise exception 'Bookinghistorikken for 2026 mangler pace-oplysninger. Afstem historikken først.';
        end if;
        update public.high_season set pace_archived = true where season = p_season;
        return jsonb_build_object('season', p_season, 'statistics_archived', true, 'bookings_copied', false);
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


revoke all on function public.close_booking_season(integer) from public, anon, authenticated;
grant execute on function public.close_booking_season(integer) to service_role;
commit;

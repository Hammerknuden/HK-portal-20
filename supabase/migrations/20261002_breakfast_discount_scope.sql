-- Gemmer om bookingrabatten kun gælder værelset og retter morgenmadsstatistikken.
-- Eksisterende bookinger får false, så den gemte generelle rabat også gælder morgenmad.
begin;

alter table public.hk_dtb
    add column if not exists breakfast_discount_exempt boolean not null default false;

comment on column public.hk_dtb.breakfast_discount_exempt is
    'True når bookingrabatten kun gælder værelset og ikke morgenmad.';

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
        case
            when lower(btrim(coalesce(web, ''))) = 'web'
                and not coalesce(breakfast_discount_exempt, false)
            then public.statistik_number(substring(
                replace(coalesce(rabat::text, '0'), ',', '.')
                from '(-?[0-9]+(?:[.][0-9]+)?)'
            ))
            else 0
        end as breakfast_discount
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
            or (pris is not null and amount is null)
            or (guests is null and (numb_guests is not null or booking_date is not null))
            or guests < 0
            or (breakfast and (breakfast_discount is null
                or coalesce((select breakfast_price from price), -1) < 0)))
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
    select extract(month from checkout_date)::integer as month,
        sum(coalesce(amount,0)) as gross_revenue
    from valid group by 1
), breakfast_nights as (
    select extract(month from d.day)::integer as month,
        coalesce(v.guests,0) as servings,
        coalesce(v.guests,0) * coalesce((select breakfast_price from price),0)
        * (1 - greatest(0, least(1, case
            when abs(v.breakfast_discount) > 1 then v.breakfast_discount / 100
            else v.breakfast_discount
        end))) / 1.25 as net_revenue
    from valid v
    cross join lateral generate_series(
        v.checkin_date::timestamp,
        (v.checkout_date - 1)::timestamp,
        interval '1 day'
    ) d(day)
    where v.breakfast
), breakfast_totals as (
    select month, sum(servings) as servings, sum(net_revenue) as net_revenue
    from breakfast_nights group by month
), checkins as (
    select checkin_date as date,
        count(distinct coalesce(booking_number::text, 'row:' || id::text)) as checkins
    from valid group by checkin_date
), lengths as (
    select extract(month from checkin_date)::integer as month,
        count(*) as stay_count, sum(nights) as total_nights
    from valid group by 1
), reports as (
    select 'room_nights'::text as report_type,
        jsonb_build_array(jsonb_build_object(
            'room_nights', (select coalesce(sum(nights),0) from valid)
        )) as data
    union all select 'danmarks_statistik', coalesce(
        (select jsonb_agg(to_jsonb(c) order by country_group) from countries c), '[]'::jsonb)
    union all select 'booking_channels', coalesce(
        (select jsonb_agg(to_jsonb(c) order by channel) from channels c), '[]'::jsonb)
    union all select 'returning_guests', coalesce(
        (select jsonb_agg(to_jsonb(c) order by guest_group) from returning_guests c), '[]'::jsonb)
    union all select 'gross_revenue_monthly', (
        select jsonb_agg(jsonb_build_object(
            'month', m, 'gross_revenue', coalesce(r.gross_revenue,0)
        ) order by m)
        from generate_series(1,12) m left join revenue r on r.month = m)
    union all select 'breakfast_monthly', (
        select jsonb_agg(jsonb_build_object(
            'month', m, 'servings', coalesce(b.servings,0),
            'net_revenue', coalesce(b.net_revenue,0)
        ) order by m)
        from generate_series(1,12) m left join breakfast_totals b on b.month = m)
    union all select 'checkins_daily', coalesce(
        (select jsonb_agg(to_jsonb(c) order by date) from checkins c), '[]'::jsonb)
    union all select 'booking_length_monthly', coalesce(
        (select jsonb_agg(to_jsonb(c) order by month) from lengths c), '[]'::jsonb)
)
select r.report_type, r.data, meta.value from reports r cross join meta;
$stats$;

revoke all on function public.calculate_season_statistics(integer)
    from public, anon, authenticated;
grant execute on function public.calculate_season_statistics(integer) to service_role;
grant execute on function public.calculate_season_statistics(integer) to authenticated;

notify pgrst, 'reload schema';
commit;

-- Diagnose for 2026. Kun SELECT: ændrer ingen data.
-- Viser samme kontroller som advarslerne på statistiksiden.
with source as materialized (
    select h.*, bool_or(regexp_replace(lower(coalesce(web, '')), '[^a-z0-9]', '', 'g') = 'cansl')
        over (partition by season, coalesce(booking_number::text, 'row:' || id::text)) as cancelled
    from public.hk_dtb h where season = 2026
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
), checked as (
    select *,
        nights is null or nights <= 0 as invalid_dates,
        (pris is not null and amount is null) as invalid_price,
        (guests is null and (numb_guests is not null or booking_date is not null)) or guests < 0 as invalid_guests,
        breakfast and discount is null as invalid_discount,
        breakfast and coalesce((
            select public.statistik_number(pris_morgenmad::text)
            from public.high_season where season = 2026
        ), -1) < 0 as invalid_breakfast_price,
        coalesce(nights > 0 and country = '', false) as missing_country
    from active
)
select id, season, booking_number, room_number,
    checkin_date, checkout_date, web, nation, pris, numb_guests, morgenmad, rabat,
    concat_ws('; ',
        case when invalid_dates then 'Manglende datoer eller udcheck ikke efter indcheck' end,
        case when invalid_price then 'Udfyldt pris kan ikke læses som tal' end,
        case when invalid_guests then 'Gæsteantal mangler på hovedrækken eller er ugyldigt' end,
        case when invalid_discount then 'Morgenmad: rabat kan ikke læses som tal' end,
        case when invalid_breakfast_price then 'Morgenmadspris mangler eller er ugyldig i sæsonopsætningen' end,
        case when missing_country then 'Landekode mangler' end
    ) as aarsag
from checked
where invalid_dates or invalid_price or invalid_guests
    or invalid_discount or invalid_breakfast_price or missing_country
order by booking_number, id;

-- Kør i Supabase SQL Editor i det eksisterende projekt.
-- Opretter kun tabellen. Flytter ingen data og afslutter ingen sæsoner.
begin;

create table if not exists public.statistik_historik (
    season integer not null check (season between 1900 and 9999),
    report_type text not null check (report_type in (
        'room_nights',
        'danmarks_statistik',
        'booking_channels',
        'returning_guests',
        'gross_revenue_monthly',
        'breakfast_monthly',
        'checkins_daily',
        'booking_length_monthly'
    )),
    format_version integer not null default 1 check (format_version > 0),
    data jsonb not null check (jsonb_typeof(data) = 'array'),
    metadata jsonb not null default '{}'::jsonb
        check (jsonb_typeof(metadata) = 'object'),
    archived_at timestamptz not null default now(),
    primary key (season, report_type)
);

comment on table public.statistik_historik is
    'Frosne statistikopgørelser pr. sæson. Kun aggregerede tal, ingen gæstenavne eller kontaktoplysninger. Booking pace ligger fortsat i bookin_pace/historie_new.';
comment on column public.statistik_historik.season is
    'Opholdets sæson; uafhængig af kalenderåret hvor opgørelsen arkiveres eller læses.';
comment on column public.statistik_historik.report_type is
    'En række pr. opgørelse og sæson. Manglende række betyder ikke arkiveret; ikke nul omsætning.';
comment on column public.statistik_historik.format_version is
    'Version af dataformat og beregningsdefinition, så historiske tal kan læses uændret.';
comment on column public.statistik_historik.data is
    'JSON-liste med aggregerede rækker. room_nights: room_nights. danmarks_statistik: country_group, arrivals, guest_nights. booking_channels: channel, room_nights. returning_guests: guest_group, room_nights. gross_revenue_monthly: month, gross_revenue. breakfast_monthly: month, servings, net_revenue. checkins_daily: date, checkins. booking_length_monthly: month, stay_count, total_nights. Beløb gemmes som tal i DKK, aldrig formateret tekst. Måned 1-12; dato YYYY-MM-DD.';
comment on column public.statistik_historik.metadata is
    'Beregningsgrundlag: fx source, revenue_month_basis, breakfast_price, vat_rate og udeladte rækker. Ingen personoplysninger. Daglige indcheckninger bevarer valgfri periodedeling; bookinglængde gemmes som antal og sum, så gennemsnit kan beregnes.';
comment on column public.statistik_historik.archived_at is
    'Tidspunkt for lagring af den frosne opgørelse. Ikke bookingdato eller sæsonafslutningsstatus.';

-- Samme serveradgang som sæsonafslutningsfunktionen.
-- Ingen offentlig læse- eller skriveadgang via anon/authenticated.
alter table public.statistik_historik enable row level security;
revoke all on table public.statistik_historik from public, anon, authenticated;
grant select, insert, update, delete on table public.statistik_historik to service_role;

commit;

begin;

alter table public.high_season
    add column if not exists pace_archived boolean not null default false;

comment on column public.high_season.pace_archived is
    'Booking pace fra 2026: false bruger hk_dtb, true bruger afstemt historie_new. Skiftes eksplicit i Setup efter arkivering, aldrig automatisk ved aarsskifte.';

-- Exact room-night total; unknown historical values must not be guessed.
alter table public.historie_new
    add column if not exists room_nights integer check (room_nights >= 0);

comment on column public.historie_new.room_nights is
    'Samlet antal ikke-annullerede vaerelsesnaetter ved arkivering. NULL betyder ukendt.';

commit;

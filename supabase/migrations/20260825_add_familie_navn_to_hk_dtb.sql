alter table public.hk_dtb
    add column if not exists familie_navn text;

comment on column public.hk_dtb.familie_navn is
    'Gæstens familienavn, svarende til familie_navn i historie_new.';

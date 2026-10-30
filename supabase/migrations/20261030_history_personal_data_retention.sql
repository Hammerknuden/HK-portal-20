-- Install only: does not remove any personal data until explicitly invoked.
-- Requires the statistics and 20261029 registration-retention migrations.
begin;
alter table public.historie_new add column if not exists personal_data_deleted_at timestamptz;
alter table public.historie_new alter column navn drop not null;
comment on column public.historie_new.personal_data_deleted_at is
    'Seneste gennemfoerte rydning af personfelter efter indcheck + 5 kalenderaar. Statistik, nationalitet og bookingnummer bevares.';

create or replace function public.clear_history_personal_data(
    p_execute boolean default false, p_limit integer default 100
) returns jsonb
language plpgsql security invoker
set search_path = pg_catalog
as $function$
declare
    assignments text;
    has_personal_data text;
    result jsonb;
begin
    if p_limit is null or p_limit < 1 or p_limit > 1000 or p_execute is null then
        raise exception 'Invalid history retention arguments';
    end if;
    -- Same order as season closing. Freeze archive status and snapshots while clearing.
    set local lock_timeout = '5s';
    lock table public.high_season in share mode;
    lock table public.statistik_historik in share mode;
    lock table public.historie_new in share row exclusive mode;

    -- Include both legacy spellings and optional note columns if present.
    select string_agg(format('%I = null', attname), ', ' order by attnum),
           string_agg(format('h.%I is not null', attname), ' or ' order by attnum)
    into assignments, has_personal_data
    from pg_attribute
    where attrelid = 'public.historie_new'::regclass
      and attnum > 0 and not attisdropped
      and attname = any(array['navn','familie_navn','email','phone',
                             'spouse','spouce','comments','notes','note']);

    -- A marked row is reprocessed if a later import reintroduces personal fields.
    execute format($sql$
        with due as materialized (
            select h.id,
                (h.storage_path is null and h.registration_deleted_at is not null) as document_ready,
                (h.season < 2026 or (
                    exists (select 1 from public.high_season s where s.season=h.season and s.pace_archived)
                    and (select count(*) from public.statistik_historik s where s.season=h.season)=8
                )) as statistics_ready
            from public.historie_new h
            where (h.indcheck + interval '5 years') at time zone 'Europe/Copenhagen' <= now()
              and (h.personal_data_deleted_at is null or (%s))
        ), selected as (
            select id from due where document_ready and statistics_ready order by id limit $1
        ), cleared as (
            update public.historie_new h set %s, personal_data_deleted_at=now()
            where $2 and h.id in (select id from selected) returning h.id
        )
        select jsonb_build_object(
            'history_due', (select count(*) from due),
            'history_eligible', (select count(*) from due where document_ready and statistics_ready),
            'history_processed', (select count(*) from cleared),
            'history_documents_pending', (select count(*) from due where not document_ready),
            'history_statistics_pending', (select count(*) from due where not statistics_ready),
            'history_missing_checkin', (select count(*) from public.historie_new where indcheck is null)
        )
    $sql$, has_personal_data, assignments) into result using p_limit, p_execute;
    return result;
end;
$function$;
revoke all on function public.clear_history_personal_data(boolean, integer) from public, anon, authenticated;
grant execute on function public.clear_history_personal_data(boolean, integer) to service_role;
commit;

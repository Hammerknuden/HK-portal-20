-- Run as postgres in original project. No bookings are moved by installation.
-- Separate authenticated endpoint; legacy function and receipt privileges unchanged.
begin;
do $$ begin
 if current_user <> 'postgres' then raise exception 'Run as postgres'; end if;
 if to_regclass('public.optimizer_plan_receipts') is null then
   raise exception 'Install the existing optimizer migration first';
 end if;
end $$;
create or replace function public.apply_optimizer_plan_authenticated(
    p_request_id uuid, p_season integer, p_candidate_id bigint, p_moves jsonb
) returns jsonb
language plpgsql
security definer
set search_path = pg_catalog, pg_temp
set lock_timeout = '5s'
as $function$
declare
    v_today date := (statement_timestamp() at time zone 'Europe/Copenhagen')::date;
    v_payload jsonb;
    v_receipt public.optimizer_plan_receipts%rowtype;
    v_count integer;
    v_updated integer;
    v_result jsonb;
begin
    -- All three approved portal users may optimize; no caller controls this check.
    if auth.uid() is null or auth.uid() not in (
        'c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid,
        '74acf117-be21-4460-877d-4f50993ac6da'::uuid,
        '4399ca28-e347-43c5-b22f-6e8be0772f61'::uuid
    ) then
        raise exception using errcode='42501', message='Ingen adgang til optimering';
    end if;
    if p_request_id is null or p_season is null or p_candidate_id is null
       or jsonb_typeof(p_moves) is distinct from 'array' then
        raise exception 'Ugyldig flytteplan.';
    end if;
    v_count := jsonb_array_length(p_moves);
    if v_count < 1 or v_count > 1000 then
        raise exception 'Ugyldigt antal flytninger.';
    end if;
    v_payload := jsonb_build_object('season', p_season, 'candidate_id', p_candidate_id, 'moves', p_moves);

    -- Also blocks inserts/deletes and other legacy writers while checking and
    -- saving. Reads remain possible. Released at commit or rollback.
    lock table public.hk_dtb in share row exclusive mode;
    select * into v_receipt from public.optimizer_plan_receipts where request_id = p_request_id;
    if found then
        if v_receipt.payload is distinct from v_payload then
            raise exception 'Samme gemme-ID er brugt til en anden plan.';
        end if;
        return v_receipt.result;
    end if;

    create temporary table optimizer_moves on commit drop as
    select * from jsonb_to_recordset(p_moves) as m(
        id bigint, from_room integer, to_room integer, checkin_date date, checkout_date date
    );
    if (select count(distinct id) from optimizer_moves) <> v_count
       or exists (select 1 from optimizer_moves where id is null or from_room is null
          or to_room is null or checkin_date is null or checkout_date is null
          or to_room not between 1 and 5 or from_room = to_room
          or checkin_date <= v_today or checkout_date <= checkin_date
          or (id = p_candidate_id and from_room <> 7)
          or (id <> p_candidate_id and from_room not between 1 and 5))
       or not exists (select 1 from optimizer_moves where id = p_candidate_id) then
        raise exception 'Planen skal flytte hele fremtidige ophold fra værelse 7 til 1–5.';
    end if;

    if (select count(*) from public.hk_dtb b join optimizer_moves m on m.id = b.id) <> v_count
       or exists (
          select 1 from public.hk_dtb b join optimizer_moves m on m.id = b.id
          where b.season is distinct from p_season or b.movable is distinct from true
             or b.room_number::integer is distinct from m.from_room
             or b.checkin_date is distinct from m.checkin_date
             or b.checkout_date is distinct from m.checkout_date
       ) then
        raise exception 'En booking er ændret, låst, slettet eller tilhører en anden sæson. Kør analysen igen.';
    end if;

    -- Match Python cancellation semantics: all rows of a cancelled booking
    -- within the same season are excluded; blank numbers do not form a group.
    create temporary table optimizer_cancelled on commit drop as
    select id, season, regexp_replace(trim(coalesce(booking_number::text, '')), '\.0+$', '') as booking_key
    from public.hk_dtb
    where regexp_replace(lower(coalesce(web, '')), '[^a-z0-9]', '', 'g') = 'cansl';
    if exists (
        select 1 from public.hk_dtb b join optimizer_moves m on m.id = b.id
        where exists (select 1 from optimizer_cancelled c where c.id = b.id or
           (c.season is not distinct from b.season and c.booking_key <> ''
            and c.booking_key = regexp_replace(trim(coalesce(b.booking_number::text, '')), '\.0+$', '')))
    ) then
        raise exception 'En berørt booking er annulleret. Kør analysen igen.';
    end if;

    update public.hk_dtb b set room_number = m.to_room
    from optimizer_moves m where b.id = m.id;
    get diagnostics v_updated = row_count;
    if v_updated <> v_count
       or (select count(*) from public.hk_dtb b join optimizer_moves m on m.id = b.id) <> v_count
       or exists (
        select 1 from public.hk_dtb b join optimizer_moves m on m.id = b.id
        where b.room_number::integer is distinct from m.to_room
           or b.checkin_date is distinct from m.checkin_date
           or b.checkout_date is distinct from m.checkout_date
           or b.season is distinct from p_season or b.movable is distinct from true
    ) then
        raise exception 'Flytningen kunne ikke gemmes samlet.';
    end if;

    -- Check the actual final data, including rows from other seasons and
    -- unchanged neighbours, after all updates. Any exception rolls everything back.
    create temporary table optimizer_final on commit drop as
    select b.* from public.hk_dtb b
    where b.room_number::integer in (
        select from_room from optimizer_moves where from_room between 1 and 5
        union select to_room from optimizer_moves
    ) and (b.checkout_date is null or b.checkout_date > v_today)
      and not exists (select 1 from optimizer_cancelled c where c.id = b.id or
           (c.season is not distinct from b.season and c.booking_key <> ''
            and c.booking_key = regexp_replace(trim(coalesce(b.booking_number::text, '')), '\.0+$', '')));
    if exists (select 1 from optimizer_final where checkin_date is null or checkout_date is null
               or checkout_date <= checkin_date)
       or exists (select 1 from optimizer_final a join optimizer_final b
          on a.id < b.id and a.room_number = b.room_number
          and a.checkin_date < b.checkout_date and b.checkin_date < a.checkout_date) then
        raise exception 'Flytningen giver overlap eller ugyldige ophold. Ingen flytninger er gemt.';
    end if;

    v_result := jsonb_build_object('status', 'saved', 'request_id', p_request_id,
        'candidate_id', p_candidate_id, 'season', p_season, 'moved_count', v_count);
    insert into public.optimizer_plan_receipts(request_id, payload, result)
    values (p_request_id, v_payload, v_result);
    return v_result;
end;
$function$;
revoke all on function public.apply_optimizer_plan_authenticated(uuid,integer,bigint,jsonb) from public,anon,authenticated;
grant execute on function public.apply_optimizer_plan_authenticated(uuid,integer,bigint,jsonb) to authenticated;
notify pgrst, 'reload schema';
commit;

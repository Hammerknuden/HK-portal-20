-- Sets deadlines only. Does not delete files or customer history.
begin;
alter table public.historie_new add column if not exists delete_at timestamptz;
alter table public.historie_new add column if not exists registration_deleted_at timestamptz;

create or replace function public.set_registration_deadline()
returns trigger language plpgsql set search_path = pg_catalog as $$
begin
    -- Calendar years, at local midnight; independent of database session timezone.
    new.delete_at := (new.indcheck + interval '2 years') at time zone 'Europe/Copenhagen';
    return new;
end;
$$;
drop trigger if exists set_registration_deadline on public.historie_new;
create trigger set_registration_deadline
before insert or update of indcheck, delete_at on public.historie_new
for each row execute function public.set_registration_deadline();

update public.historie_new
set delete_at = (indcheck + interval '2 years') at time zone 'Europe/Copenhagen';

comment on column public.historie_new.delete_at is
    'Slettefrist for gaesteregistreringens PDF: indcheck + 2 kalenderaar. Ikke kundekartotekets frist.';
comment on column public.historie_new.registration_deleted_at is
    'Tidspunkt da slettejobbet bekraeftede at PDF var fjernet eller ikke fandtes. Ikke sletning af bookingraekken.';
create index if not exists historie_new_registration_due_idx
on public.historie_new(delete_at) where registration_deleted_at is null;
commit;

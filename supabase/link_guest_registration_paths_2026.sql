-- Match existing files with or without leading zeros. Keep actual object path.
-- Preserve existing links. Skip ambiguous file and history matches.
BEGIN;
LOCK TABLE public.historie_new IN SHARE ROW EXCLUSIVE MODE;
WITH files AS (
    SELECT name,
           coalesce(nullif(ltrim(substring(name FROM '^2026/2026-([0-9]+)[.]pdf$'), '0'), ''), '0') AS booking_key
    FROM storage.objects
    WHERE bucket_id='guest-registrations' AND name ~ '^2026/2026-[0-9]+[.]pdf$'
), grouped_files AS (
    SELECT booking_key, count(*) AS file_count, min(name) AS file_path
    FROM files GROUP BY booking_key
), candidates AS (
    SELECT h.id, h.booking_nr, h.storage_path, f.file_path,
           coalesce(f.file_count, 0) AS file_count,
           count(*) OVER (PARTITION BY h.booking_nr) AS history_count
    FROM public.historie_new h
    LEFT JOIN grouped_files f ON f.booking_key=h.booking_nr::text
    WHERE h.season=2026
), updated AS (
    UPDATE public.historie_new h SET storage_path=c.file_path
    FROM candidates c
    WHERE h.id=c.id AND h.season=2026
      AND nullif(btrim(h.storage_path),'') IS NULL
      AND c.file_count=1 AND c.history_count=1
    RETURNING h.id
)
SELECT count(*) AS nye_koblinger FROM updated;
COMMIT;

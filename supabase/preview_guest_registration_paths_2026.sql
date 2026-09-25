-- Read-only summary; handles both 001.pdf and 1.pdf. No UI row-limit ambiguity.
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
)
SELECT
    count(*) AS historikraekker,
    count(*) FILTER (WHERE nullif(btrim(storage_path),'') IS NOT NULL) AS allerede_koblet,
    count(*) FILTER (WHERE nullif(btrim(storage_path),'') IS NULL AND file_count=1 AND history_count=1) AS klar_til_kobling,
    count(*) FILTER (WHERE nullif(btrim(storage_path),'') IS NULL AND file_count=0) AS uden_matchende_fil,
    count(*) FILTER (WHERE nullif(btrim(storage_path),'') IS NULL AND file_count>0
                    AND (file_count>1 OR history_count>1)) AS kraever_kontrol,
    (SELECT count(*) FROM files) AS pdf_filer_med_genkendt_navn
FROM candidates;

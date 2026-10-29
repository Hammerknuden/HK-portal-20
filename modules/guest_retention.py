"""Retention worker: PostgreSQL locks protect history while Storage API deletes PDFs.

No file contents, names, paths or credentials are written to logs.
Database rollback cannot restore a deleted file: retries verify Storage metadata.
"""
import re

BUCKET = "guest-registrations"


def valid_path(path):
    return (isinstance(path, str) and path.lower().endswith('.pdf')
            and '\\' not in path and ':' not in path
            and all(part not in ('', '.', '..') for part in path.split('/')))


def filename_key(path):
    match = re.fullmatch(r'(\d{4})/\1-(\d+)\.pdf', path)
    return (int(match[1]), int(match[2])) if match else None


def purge_batch(connection, storage, *, execute=False, limit=100):
    """One bounded transaction. Shared/ambiguous paths abort before any deletion.

    Lock history writes (including document linking/check-in edits) until commit.
    Read-only Storage metadata is checked after API removal, even for absent files.
    """
    if not 1 <= limit <= 100:
        raise ValueError('Batch size must be between 1 and 100')
    with connection.transaction():
        with connection.cursor() as cur:
            cur.execute("set local lock_timeout = '5s'")
            cur.execute("set local statement_timeout = '30s'")
            cur.execute("lock table public.historie_new in share row exclusive mode")
            cur.execute("""select id, season, booking_nr, storage_path,
                delete_at <= now() as due, registration_deleted_at is not null as done
                from public.historie_new""")
            rows = cur.fetchall()
            cur.execute('select name from storage.objects where bucket_id = %s', (BUCKET,))
            objects = {row[0] for row in cur.fetchall()}
            by_key, references = {}, {}
            for row in rows:
                by_key.setdefault((row[1], row[2]), []).append(row)
                if row[3]:
                    references.setdefault(row[3], []).append(row)
            # Also find uploaded documents not linked yet (e.g. 2024 or future seasons).
            keyed_objects = {}
            for path in objects:
                keyed_objects.setdefault(filename_key(path), []).append(path)
            candidates = []
            for row in rows:
                row_id, season, booking, path, due, done = row
                if not due:
                    continue
                matches = keyed_objects.get((season, booking), [])
                paths = set(matches)
                if path:
                    paths.add(path)
                if done and not path and not matches:
                    continue
                if len(by_key[(season, booking)]) != 1 or len(paths) > 1:
                    raise ValueError('Ambiguous registration mapping; nothing deleted')
                for item in paths:
                    if not valid_path(item) or any(other[0] != row_id for other in references.get(item, [])):
                        raise ValueError('Invalid or shared registration path; nothing deleted')
                    key = filename_key(item)
                    if key is not None and key != (season, booking):
                        raise ValueError('Registration filename disagrees with booking; nothing deleted')
                candidates.append((row_id, next(iter(paths), None)))
            candidates.sort(key=lambda value: value[0])
            selected = candidates[:limit]
            if execute:
                for row_id, path in selected:
                    if path and path in objects:
                        storage.from_(BUCKET).remove([path])
                        cur.execute('select 1 from storage.objects where bucket_id = %s and name = %s', (BUCKET, path))
                        if cur.fetchone():
                            raise RuntimeError('Storage deletion not confirmed; retry required')
                    cur.execute('''update public.historie_new set storage_path = null,
                        registration_deleted_at = now() where id = %s''', (row_id,))
            return {'due': len(candidates), 'processed': len(selected) if execute else 0,
                    'files_to_remove': sum(path in objects for _, path in selected),
                    'missing_checkin': sum(row[4] is None for row in rows),
                    'unmatched_files': sum(filename_key(path) not in by_key and path not in references for path in objects)}

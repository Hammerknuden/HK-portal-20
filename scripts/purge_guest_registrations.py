"""Scheduled server entry point. Preview by default; --execute performs deletion."""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from modules.guest_retention import purge_batch
from modules.season_backup import database_environment, is_server_key


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--history-only', action='store_true',
                        help='Process five-year history fields instead of registration PDFs')
    args = parser.parse_args()
    try:
        import psycopg
        from supabase import create_client
        url = os.environ['SUPABASE_URL']
        key = os.environ['SUPABASE_RETENTION_KEY']
        if not is_server_key(key):
            raise ValueError('Server key required')
        env = database_environment(os.environ['SUPABASE_RETENTION_DB_URL'], url)
        client = create_client(url, key)
        with psycopg.connect(host=env['PGHOST'], port=env['PGPORT'],
                              user=env['PGUSER'], password=env['PGPASSWORD'],
                              dbname=env['PGDATABASE'], sslmode='require',
                              connect_timeout=20, application_name='hk-registration-retention') as conn:
            # Bounded runs, with commits between batches and no OFFSET skipping.
            for _ in range(20):
                if args.history_only:
                    with conn.transaction():
                        with conn.cursor() as cur:
                            cur.execute("set local statement_timeout = '60s'")
                            cur.execute('select public.clear_history_personal_data(%s, %s)',
                                        (args.execute, 100))
                            counts = cur.fetchone()[0]
                    remaining = counts['history_eligible']
                    processed = counts['history_processed']
                else:
                    counts = purge_batch(conn, client.storage, execute=args.execute)
                    remaining, processed = counts['due'], counts['processed']
                print(json.dumps(counts))
                if not args.execute or remaining <= processed:
                    return
            raise RuntimeError('Batch limit reached; another run is required')
    except Exception:
        # Raw SDK/DB exceptions can contain credentials and personal information.
        print('Retention job failed. Check configuration, mapping and Storage access; retry after correction.', file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()

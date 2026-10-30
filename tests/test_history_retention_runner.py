import io
import unittest
from contextlib import nullcontext, redirect_stdout, redirect_stderr
from unittest.mock import Mock, patch

from scripts import purge_guest_registrations as runner


class HistoryRetentionRunnerTests(unittest.TestCase):
    def run_history(self, counts, *, execute=False, error=None):
        connection, cursor = Mock(), Mock()
        connection.transaction.side_effect = lambda: nullcontext()
        connection.cursor.side_effect = lambda: nullcontext(cursor)
        cursor.fetchone.side_effect = [(value,) for value in counts]
        if error:
            cursor.execute.side_effect = error
        psycopg, supabase = Mock(), Mock()
        psycopg.connect.return_value = nullcontext(connection)
        env = dict(SUPABASE_URL='https://example.supabase.co',
                   SUPABASE_RETENTION_KEY='sb_secret_test', SUPABASE_RETENTION_DB_URL='private')
        settings = dict(PGHOST='db', PGPORT='5432', PGUSER='postgres',
                        PGPASSWORD='private', PGDATABASE='postgres')
        output, errors = io.StringIO(), io.StringIO()
        args = ['retention', '--history-only'] + (['--execute'] if execute else [])
        with patch.dict('sys.modules', {'psycopg': psycopg, 'supabase': supabase}), \
                patch.dict('os.environ', env), patch('sys.argv', args), \
                patch.object(runner, 'database_environment', return_value=settings), \
                patch.object(runner, 'purge_batch') as pdf, \
                redirect_stdout(output), redirect_stderr(errors):
            if error:
                with self.assertRaises(SystemExit):
                    runner.main()
            else:
                runner.main()
            pdf.assert_not_called()
        return cursor, output.getvalue(), errors.getvalue()

    def test_preview_calls_read_only_function_once_even_with_multiple_batches_due(self):
        cursor, output, _ = self.run_history([{'history_eligible': 482, 'history_processed': 0}])
        self.assertIn('"history_processed": 0', output)
        cursor.execute.assert_any_call('select public.clear_history_personal_data(%s, %s)', (False, 100))
        self.assertEqual(cursor.fetchone.call_count, 1)

    def test_execute_repeats_using_eligible_count_not_blocked_total(self):
        cursor, _, _ = self.run_history([
            {'history_due': 205, 'history_eligible': 182, 'history_processed': 100},
            {'history_due': 105, 'history_eligible': 82, 'history_processed': 82},
        ], execute=True)
        self.assertEqual(cursor.fetchone.call_count, 2)
        cursor.execute.assert_any_call('select public.clear_history_personal_data(%s, %s)', (True, 100))

    def test_database_failure_does_not_leak_raw_exception(self):
        _, _, errors = self.run_history([], error=RuntimeError('secret-password-and-guest-name'))
        self.assertIn('Retention job failed', errors)
        self.assertNotIn('secret-password', errors)


if __name__ == '__main__':
    unittest.main()

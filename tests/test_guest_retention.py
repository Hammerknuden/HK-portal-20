import unittest
from contextlib import nullcontext
from unittest.mock import Mock

from modules.guest_retention import purge_batch


class Cursor:
    def __init__(self, rows, objects):
        self.rows = rows
        self.objects = set(objects)
        self.updated = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def execute(self, sql, params=None):
        self.sql, self.params = sql, params
        if sql.startswith('update public.historie_new'):
            self.updated.append(params[0])

    def fetchall(self):
        if 'select id, season' in self.sql:
            return self.rows
        return [(path,) for path in self.objects]

    def fetchone(self):
        return (1,) if self.params[1] in self.objects else None


class RetentionTests(unittest.TestCase):
    def run_batch(self, rows, objects, execute=True, remove_error=False, remove_noop=False):
        cursor = Cursor(rows, objects)
        connection = Mock()
        connection.transaction.side_effect = lambda: nullcontext()
        connection.cursor.return_value = cursor
        storage = Mock()

        def remove(paths):
            if remove_error:
                raise RuntimeError('Storage unavailable')
            if not remove_noop:
                cursor.objects.difference_update(paths)

        storage.from_.return_value.remove.side_effect = remove
        return cursor, storage, lambda: purge_batch(connection, storage, execute=execute)

    def test_due_file_deleted_before_history_reference_cleared(self):
        cursor, storage, run = self.run_batch(
            [(1, 2024, 7, '2024/2024-007.pdf', True, False),
             (2, 2026, 8, '2026/2026-8.pdf', False, False)],
            ['2024/2024-007.pdf', '2026/2026-8.pdf'])
        self.assertEqual(run()['processed'], 1)
        storage.from_.return_value.remove.assert_called_once_with(['2024/2024-007.pdf'])
        self.assertEqual(cursor.updated, [1])
        self.assertIn('2026/2026-8.pdf', cursor.objects)

    def test_preview_never_mutates(self):
        cursor, storage, run = self.run_batch([(1, 2024, 1, '2024/2024-1.pdf', True, False)],
                                             ['2024/2024-1.pdf'], execute=False)
        self.assertEqual(run()['files_to_remove'], 1)
        self.assertFalse(cursor.updated)
        storage.from_.assert_not_called()

    def test_missing_upload_and_missing_file_are_completed(self):
        cursor, storage, run = self.run_batch(
            [(1, 2024, 1, None, True, False), (2, 2024, 2, '2024/2024-2.pdf', True, False)], [])
        self.assertEqual(run()['processed'], 2)
        storage.from_.assert_not_called()
        self.assertEqual(cursor.updated, [1, 2])

    def test_unlinked_upload_and_late_reupload_are_found(self):
        cursor, storage, run = self.run_batch([(1, 2024, 1, None, True, True)], ['2024/2024-001.pdf'])
        self.assertEqual(run()['processed'], 1)
        self.assertFalse(cursor.objects)

    def test_failed_or_unconfirmed_storage_delete_keeps_reference(self):
        for kwargs in ({'remove_error': True}, {'remove_noop': True}):
            cursor, _, run = self.run_batch([(1, 2024, 1, '2024/2024-1.pdf', True, False)],
                                           ['2024/2024-1.pdf'], **kwargs)
            with self.assertRaises(RuntimeError):
                run()
            self.assertFalse(cursor.updated)

    def test_missing_checkin_and_unmatched_file_are_reported_not_deleted(self):
        cursor, storage, run = self.run_batch([(1, 2024, 1, None, None, False)], ['2024/2024-2.pdf'])
        result = run()
        self.assertEqual(result['missing_checkin'], 1)
        self.assertEqual(result['unmatched_files'], 1)
        storage.from_.assert_not_called()

    def test_invalid_shared_and_ambiguous_paths_fail_before_any_deletion(self):
        for rows, objects in [
            ([(1, 2024, 1, '../bad.pdf', True, False)], []),
            ([(1, 2024, 1, 'shared.pdf', True, False),
              (2, 2026, 1, 'shared.pdf', False, False)], ['shared.pdf']),
            ([(1, 2024, 1, None, True, False)], ['2024/2024-1.pdf', '2024/2024-01.pdf']),
            ([(1, 2024, 1, '2026/2026-1.pdf', True, False)], ['2026/2026-1.pdf']),
        ]:
            cursor, storage, run = self.run_batch(rows, objects)
            with self.assertRaises(ValueError):
                run()
            storage.from_.assert_not_called()
            self.assertFalse(cursor.updated)


if __name__ == '__main__':
    unittest.main()

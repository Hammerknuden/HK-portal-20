import hashlib
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from modules.season_backup import BackupError, create_backup, database_environment, storage_inventory


SETTINGS = {"SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_BACKUP_KEY": "sb_secret_test",
            "SUPABASE_BACKUP_DB_URL": "postgresql://postgres.example:private%21@aws-0.pooler.supabase.com:5432/postgres"}


class Storage:
    def __init__(self):
        self.storage = self
        self.calls = []
        self.content = b"document"

    def list_buckets(self):
        return [{"id": "guests", "type": "STANDARD"}]

    def from_(self, bucket):
        return self

    def list(self, prefix, options):
        self.calls.append((prefix, options["offset"]))
        # Deliberately enforce pages smaller than requested.
        rows = ([{"name": "2026", "id": None, "metadata": None},
                 {"name": "root.pdf", "id": "root", "metadata": {"size": 8}}]
                if not prefix else [{"name": "guest.pdf", "id": "guest", "metadata": {"size": 8}}])
        offset = options["offset"]
        return rows[offset:offset + 1]

    def download(self, path):
        return self.content


def fake_dump(args, env):
    if "--file" in args:
        Path(args[args.index("--file") + 1]).write_bytes(b"database test payload")


class BackupTests(unittest.TestCase):
    def test_connection_password_not_in_arguments_and_project_match(self):
        env = database_environment(SETTINGS["SUPABASE_BACKUP_DB_URL"], SETTINGS["SUPABASE_URL"])
        self.assertEqual(env["PGPASSWORD"], "private!")
        self.assertEqual(env["PGSSLMODE"], "require")
        for url in (SETTINGS["SUPABASE_BACKUP_DB_URL"].replace("postgres.example", "postgres.other"),
                    SETTINGS["SUPABASE_BACKUP_DB_URL"].replace(":5432", ":6543")):
            with self.assertRaises(BackupError):
                database_environment(url, SETTINGS["SUPABASE_URL"])

    def test_nested_and_capped_pages_are_all_read(self):
        client = Storage()
        _, files = storage_inventory(client)
        self.assertEqual([o["path"] for o in files], ["2026/guest.pdf", "root.pdf"])
        self.assertIn(("", 2), client.calls)

    @patch("modules.season_backup.shutil.which", return_value="tool")
    @patch("modules.season_backup.run_database_tool", side_effect=fake_dump)
    def test_archive_checksums_contents_and_no_secrets(self, runner, which):
        name, content, count = create_backup(SETTINGS, Storage(), 2026, "efter")
        self.assertIn("2026-efter", name)
        self.assertEqual(count, 2)
        with ZipFile(io.BytesIO(content)) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            for entry in manifest["files"]:
                payload = archive.read(entry["path"])
                self.assertEqual(hashlib.sha256(payload).hexdigest(), entry["sha256"])
                self.assertNotIn(b"private!", payload)
                self.assertNotIn(b"sb_secret_test", payload)
            self.assertEqual(len(manifest["objects"]), 2)
        for call in runner.call_args_list:
            self.assertNotIn("private", " ".join(call.args[0]))

    @patch("modules.season_backup.shutil.which", return_value="tool")
    @patch("modules.season_backup.run_database_tool", side_effect=fake_dump)
    def test_download_failure_does_not_return_partial_backup(self, *_):
        client = Storage()
        client.download = lambda path: (_ for _ in ()).throw(RuntimeError("denied"))
        with self.assertRaises(RuntimeError):
            create_backup(SETTINGS, client, 2026, "foer")

    @patch("modules.season_backup.shutil.which", return_value="tool")
    @patch("modules.season_backup.run_database_tool", side_effect=fake_dump)
    def test_changed_storage_rejects_backup(self, *_):
        client = Storage()
        original = client.download
        def download(path):
            client.list_buckets = lambda: [{"id": "guests", "type": "STANDARD", "public": True}]
            return original(path)
        client.download = download
        with self.assertRaisesRegex(BackupError, "ændret"):
            create_backup(SETTINGS, client, 2026, "efter")

    @patch("modules.season_backup.shutil.which", return_value="tool")
    @patch("modules.season_backup.run_database_tool", side_effect=BackupError("database failed"))
    def test_database_failure_aborts(self, *_):
        with self.assertRaisesRegex(BackupError, "database failed"):
            create_backup(SETTINGS, Storage(), 2026, "efter")

    @patch("modules.season_backup.shutil.which", return_value="tool")
    def test_anon_key_rejected(self, *_):
        with self.assertRaises(BackupError):
            create_backup({**SETTINGS, "SUPABASE_BACKUP_KEY": "anon"}, Storage(), 2026, "efter")

    @patch("modules.season_backup.shutil.which", return_value="tool")
    @patch("modules.season_backup.run_database_tool", side_effect=fake_dump)
    @patch("modules.season_backup.MAX_BYTES", 1)
    def test_size_limit_does_not_release_archive(self, *_):
        with self.assertRaisesRegex(BackupError, "150 MB"):
            create_backup(SETTINGS, Storage(), 2026, "efter")

    def test_unsafe_storage_path_rejected(self):
        client = Storage()
        client.list = lambda prefix, options: [{"name": "../escape", "id": "file"}]
        with self.assertRaises(BackupError):
            storage_inventory(client)


if __name__ == "__main__":
    unittest.main()

import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("restore_storage_test", Path(__file__).resolve().parents[1] / "scripts/restore_storage_test.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class API:
    def __init__(self):
        self.buckets = []
        self.files = {}
        self.writes = 0

    def call(self, method, path, data=None, **kwargs):
        if path == "/bucket":
            if method == "GET":
                return self.buckets
            self.writes += 1
            self.buckets.append(data)
        elif path.startswith("/object/list/"):
            return ([{"name": name, "id": name, "metadata": {"size": len(content)}} for name, content in self.files.items()]
                    if data["offset"] == 0 else [])
        elif method == "POST":
            self.writes += 1
            self.files[path.rsplit("/", 1)[1]] = data
        else:
            return self.files[path.rsplit("/", 1)[1]]


class StorageRestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "file.bin").write_bytes(b"test document")
        manifest = {"buckets": [{"id": "private", "public": False}],
                    "objects": [{"bucket": "private", "path": "guest.pdf", "archive_path": "file.bin"}],
                    "files": [{"path": "file.bin", "bytes": 13, "sha256": hashlib.sha256(b"test document").hexdigest()}]}
        (self.root / "manifest.json").write_text(json.dumps(manifest))

    def test_upload_verify_and_idempotent_retry(self):
        api = API()
        self.assertEqual(module.restore(api, self.root, lambda _: None)["verified_files"], 1)
        writes = api.writes
        module.restore(api, self.root, lambda _: None)
        self.assertEqual(api.writes, writes)
        self.assertFalse(api.buckets[0]["public"])

    def test_corrupt_backup_stops_before_network_writes(self):
        api = API()
        (self.root / "file.bin").write_bytes(b"corrupt")
        with self.assertRaises(module.RestoreError):
            module.restore(api, self.root)
        self.assertEqual(api.writes, 0)

    def test_existing_different_file_not_overwritten(self):
        api = API()
        api.buckets = [{"id": "private", "public": False}]
        api.files = {"guest.pdf": b"other"}
        with self.assertRaises(module.RestoreError):
            module.restore(api, self.root)
        self.assertEqual(api.writes, 0)

    def test_other_project_key_rejected(self):
        import base64
        payload = base64.urlsafe_b64encode(json.dumps({"role": "service_role", "ref": "production"}).encode()).decode()
        with self.assertRaises(module.RestoreError):
            module.StorageAPI("header." + payload + ".signature")


if __name__ == "__main__":
    unittest.main()

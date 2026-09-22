"""Restore verified files only to the named backup-test project. Stdlib only."""
import base64
import getpass
import hashlib
import json
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, build_opener, HTTPRedirectHandler

TARGET = "ycasinssaffzpsyhgzgf"
BASE = f"https://{TARGET}.supabase.co/storage/v1"
BACKUP = Path(r"C:\Users\finnj\Downloads\backup-test\hammerknuden-2026-foer-20260920T165647Z-3b103ddd")


class RestoreError(Exception):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise RestoreError("Uventet omdirigering afvist. Intet sendes til en anden server.")


class StorageAPI:
    def __init__(self, key):
        self.headers = {"apikey": key}
        if not key.startswith("sb_secret_"):
            try:
                part = key.split(".")[1]
                payload = json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))
                if payload.get("role") != "service_role" or payload.get("ref") != TARGET:
                    raise ValueError
            except (ValueError, IndexError, TypeError):
                raise RestoreError("Brug testprojektets secret- eller service_role-noegle.") from None
            self.headers["Authorization"] = "Bearer " + key
        self.opener = build_opener(NoRedirect())

    def call(self, method, path, data=None, mime="application/json", raw=False):
        if data is not None and not isinstance(data, bytes):
            data = json.dumps(data).encode("utf-8")
        request = Request(BASE + path, data=data, method=method,
                          headers={**self.headers, "Content-Type": mime, "x-upsert": "false"})
        try:
            with self.opener.open(request, timeout=120) as response:
                content = response.read()
        except HTTPError as error:
            raise RestoreError(f"Storage svarede HTTP {error.code}. Kontrollér testprojektets noegle og Storage-adgang. Ingen filer overskrives.") from None
        except URLError:
            raise RestoreError("Netvaerksforbindelsen til testprojektet fejlede. Proev igen.") from None
        return content if raw else json.loads(content or b"null")


def inventory(api, bucket):
    pending, paths = [""], set()
    seen = set()
    while pending:
        prefix = pending.pop()
        if prefix in seen:
            raise RestoreError("Uventet Storage-mappestruktur.")
        seen.add(prefix)
        offset = 0
        while True:
            rows = api.call("POST", "/object/list/" + quote(bucket, safe=""),
                            {"prefix": prefix, "limit": 100, "offset": offset,
                             "sortBy": {"column": "name", "order": "asc"}})
            if not rows:
                break
            for row in rows:
                path = prefix + "/" + row["name"] if prefix else row["name"]
                if row.get("id") is None and row.get("metadata") is None:
                    pending.append(path)
                else:
                    if path in paths:
                        raise RestoreError("Storage-listen gentager en fil. Stopper.")
                    paths.add(path)
            offset += len(rows)
    return paths


def load_verified_backup(root):
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    entries = {item["path"]: item for item in manifest["files"]}
    objects = manifest["objects"]
    if len({(o["bucket"], o["path"]) for o in objects}) != len(objects):
        raise RestoreError("Dubletter i backupmanifestet.")
    bucket_ids = {b["id"] for b in manifest["buckets"]}
    for bucket in manifest["buckets"]:
        if bucket.get("public") is not False or bucket.get("type") not in (None, "STANDARD"):
            raise RestoreError("Denne test er kun klargjort til private standard-buckets.")
    for obj in objects:
        if obj["bucket"] not in bucket_ids:
            raise RestoreError("Ukendt bucket i manifest.")
        path = (root / obj["archive_path"]).resolve()
        if not path.is_relative_to(root.resolve()):
            raise RestoreError("Ugyldig lokal filsti.")
        entry = entries[obj["archive_path"]]
        content = path.read_bytes()
        if len(content) != entry["bytes"] or hashlib.sha256(content).hexdigest() != entry["sha256"]:
            raise RestoreError("En lokal fil bestod ikke kontrolsummen. Stopper foer upload.")
    return manifest, entries


def restore(api, root, progress=print):
    manifest, entries = load_verified_backup(root)
    existing = {b["id"]: b for b in api.call("GET", "/bucket")}
    expected = {b["id"]: {o["path"] for o in manifest["objects"] if o["bucket"] == b["id"]}
                for b in manifest["buckets"]}
    current = {}
    # Validate every destination before creating anything.
    for bucket in manifest["buckets"]:
        bid = bucket["id"]
        if bid in existing:
            other = existing[bid]
            if (other.get("public") is not False
                    or other.get("file_size_limit") != bucket.get("file_size_limit")
                    or sorted(other.get("allowed_mime_types") or []) != sorted(bucket.get("allowed_mime_types") or [])):
                raise RestoreError("Eksisterende bucket har andre indstillinger. Stopper uden at aendre den.")
            current[bid] = inventory(api, bid)
            if current[bid] - expected[bid]:
                raise RestoreError("Destinationen indeholder filer uden for denne backup. Stopper.")
        else:
            current[bid] = set()
    # Existing matching files are verified before any mutation; useful after interruption.
    for obj in manifest["objects"]:
        if obj["path"] in current[obj["bucket"]]:
            payload = api.call("GET", "/object/authenticated/" + quote(obj["bucket"], safe="") + "/" + quote(obj["path"], safe="/"), raw=True)
            if hashlib.sha256(payload).hexdigest() != entries[obj["archive_path"]]["sha256"]:
                raise RestoreError("En eksisterende fil har andet indhold. Den bliver ikke overskrevet.")
    for bucket in manifest["buckets"]:
        if bucket["id"] not in existing:
            api.call("POST", "/bucket", {"id": bucket["id"], "name": bucket["id"], "public": False,
                     "file_size_limit": bucket.get("file_size_limit"),
                     "allowed_mime_types": bucket.get("allowed_mime_types")})
    checked = 0
    for obj in manifest["objects"]:
        path = quote(obj["bucket"], safe="") + "/" + quote(obj["path"], safe="/")
        if obj["path"] not in current[obj["bucket"]]:
            content = (root / obj["archive_path"]).read_bytes()
            api.call("POST", "/object/" + path, content,
                     mime=(obj.get("metadata") or {}).get("mimetype") or "application/octet-stream")
        downloaded = api.call("GET", "/object/authenticated/" + path, raw=True)
        if hashlib.sha256(downloaded).hexdigest() != entries[obj["archive_path"]]["sha256"]:
            raise RestoreError("Kontrol efter upload fejlede. Gendannelsen er ikke godkendt.")
        checked += 1
        progress(f"Kontrolleret {checked}/{len(manifest['objects'])}")
    for bid, wanted in expected.items():
        if inventory(api, bid) != wanted:
            raise RestoreError("Det endelige filantal stemmer ikke.")
    return {"target": TARGET, "verified_files": checked, "buckets": len(expected),
            "scope": "Storage file bytes and paths verified; Auth and access-policy tests pending"}


def main():
    print(f"Gendanner private dokumenter til TESTPROJEKT {TARGET}.")
    print("Brug testprojektets API secret/service_role-noegle, IKKE databaseadgangskoden.")
    key = getpass.getpass("Indsaet testprojektets API-noegle (skjult): ").strip()
    result = restore(StorageAPI(key), BACKUP)
    report = Path(__file__).resolve().parents[1] / "tmp/restore-tools/restore-storage-result.json"
    report.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"OK: {result['verified_files']} dokumenter gendannet og kontrolleret i {result['buckets']} private buckets.")
    print("Auth, adgangspolitikker og funktionstest mangler stadig.")


if __name__ == "__main__":
    try:
        main()
    except (RestoreError, OSError, KeyError, ValueError) as error:
        print(str(error) if isinstance(error, RestoreError) else "Lokal backup eller opsaetning kunne ikke laeses. Kontakt fejlsogning.")
        print("Ved delvis upload kan scriptet koeres igen; eksisterende filer kontrolleres og overskrives aldrig.")
        sys.exit(1)

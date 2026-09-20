"""Read-only PostgreSQL/Storage backup. No credentials enter the archive."""
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from urllib.parse import unquote, urlsplit
from uuid import uuid4
from zipfile import ZipFile, ZIP_DEFLATED


MAX_BYTES = 150 * 1024 * 1024
DESTINATION = r"C:\Users\finnj\SynologyDrive\Supabase backup"


class BackupError(RuntimeError):
    pass


def database_environment(db_url, project_url):
    """Keep passwords out of process arguments, logs and downloaded files."""
    db, project = urlsplit(db_url), urlsplit(project_url)
    ref = (project.hostname or "").removesuffix(".supabase.co")
    username = unquote(db.username or "")
    same_project = (db.hostname == f"db.{ref}.supabase.co" and username == "postgres") or (
        (db.hostname or "").endswith(".pooler.supabase.com")
        and username == f"postgres.{ref}"
    )
    if (db.scheme not in ("postgres", "postgresql") or not db.password
            or not same_project or db.port not in (None, 5432) or project.scheme != "https"):
        raise BackupError("Databaseforbindelsen skal pege på samme Supabase-projekt "
                          "og bruge Direct connection eller Session pooler (port 5432).")
    env = os.environ.copy()
    env.update(PGHOST=db.hostname, PGPORT=str(db.port or 5432),
               PGUSER=username, PGPASSWORD=unquote(db.password),
               PGDATABASE=unquote(db.path.lstrip("/") or "postgres"),
               PGSSLMODE="require", PGCONNECT_TIMEOUT="20",
               PGAPPNAME="hammerknuden-season-backup")
    return env


def is_server_key(key):
    if key.startswith("sb_secret_"):
        return True
    try:
        payload = key.split(".")[1]
        return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))).get("role") == "service_role"
    except (ValueError, IndexError, TypeError):
        return False


def prerequisites(settings):
    missing = []
    for name in ("SUPABASE_URL", "SUPABASE_BACKUP_DB_URL", "SUPABASE_BACKUP_KEY"):
        if not settings.get(name):
            missing.append(f"Secrets: {name}")
    if settings.get("SUPABASE_BACKUP_KEY") and not is_server_key(settings["SUPABASE_BACKUP_KEY"]):
        missing.append("SUPABASE_BACKUP_KEY skal være en secret- eller service_role-nøgle")
    for name in ("pg_dump", "pg_dumpall", "pg_restore"):
        if not shutil.which(name):
            missing.append(f"Serverværktøj: {name} (postgresql-client)")
    return missing


def run_database_tool(args, env):
    try:
        result = subprocess.run(args, env=env, capture_output=True, timeout=900,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.TimeoutExpired):
        raise BackupError("Databasebackup kunne ikke gennemføres. Kontrollér serverværktøjer og forbindelse.") from None
    if result.returncode:
        if b"server version mismatch" in result.stderr:
            raise BackupError("Serverens pg_dump er for gammel. Installér PostgreSQL-klient i samme eller nyere hovedversion som Supabase.")
        raise BackupError("Databasebackup fejlede. Kontrollér databaseadgang, værktøjsversion og ledig plads. Ingen backup er frigivet.")


def storage_inventory(client):
    buckets, objects = [], []
    for bucket in client.storage.list_buckets():
        details = bucket if isinstance(bucket, dict) else bucket.model_dump(mode="json")
        if details.get("type") not in (None, "STANDARD"):
            raise BackupError("Storage indeholder en bucket-type, som denne backup ikke understøtter.")
        buckets.append(details)
        bucket_id = details["id"]
        pending = [""]
        visited = set()
        while pending:
            prefix = pending.pop()
            if prefix in visited:
                raise BackupError("Storage-mappelisten kunne ikke kontrolleres.")
            visited.add(prefix)
            offset = 0
            while True:
                rows = client.storage.from_(bucket_id).list(prefix, {
                    "limit": 100, "offset": offset,
                    "sortBy": {"column": "name", "order": "asc"},
                })
                for row in rows:
                    name = row["name"]
                    if not name or "/" in name or "\\" in name or name in (".", ".."):
                        raise BackupError("Storage indeholder et filnavn, der kræver manuel backup.")
                    path = f"{prefix}/{name}" if prefix else name
                    if row.get("id") is None and row.get("metadata") is None:
                        pending.append(path)
                    else:
                        objects.append({"bucket": bucket_id, "path": path,
                                        "id": row.get("id"), "updated_at": row.get("updated_at"),
                                        "metadata": row.get("metadata")})
                # Advance by actual count: API may enforce a smaller page size.
                if not rows:
                    break
                offset += len(rows)
    return sorted(buckets, key=lambda b: b["id"]), sorted(objects, key=lambda o: (o["bucket"], o["path"]))


def create_backup(settings, client, season, phase, progress=lambda message: None):
    missing = prerequisites(settings)
    if missing:
        raise BackupError("Backup er ikke konfigureret: " + "; ".join(missing))
    env = database_environment(settings["SUPABASE_BACKUP_DB_URL"], settings["SUPABASE_URL"])
    if phase not in ("foer", "efter"):
        raise BackupError("Vælg før eller efter sæsonafslutning.")
    season = int(season)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"hammerknuden-{season}-{phase}-{stamp}-{uuid4().hex[:8]}.zip"
    manifest = {"format_version": 1, "created_utc": stamp, "season_label": season,
                "phase": phase, "scope": "Alle sæsoner i databasen og almindelige Storage-buckets",
                "project_url": settings["SUPABASE_URL"], "files": []}
    with tempfile.TemporaryDirectory(prefix="hk-backup-") as temp:
        root = Path(temp)
        progress("Henter database, struktur og roller …")
        run_database_tool(["pg_dump", "--format=custom", "--no-password", "--file", str(root / "database.dump")], env)
        run_database_tool(["pg_dumpall", "--roles-only", "--no-role-passwords", "--no-password",
                           "--file", str(root / "roles.sql")], env)
        run_database_tool(["pg_restore", "--list", str(root / "database.dump")], env)
        progress("Henter dokumenter fra Storage …")
        buckets, objects = storage_inventory(client)
        manifest["buckets"] = buckets
        manifest["objects"] = objects
        size = sum(p.stat().st_size for p in root.iterdir())
        if size > MAX_BYTES:
            raise BackupError("Backuppen overstiger 150 MB. Brug et separat backupjob til denne størrelse.")
        for index, item in enumerate(objects):
            expected_size = (item.get("metadata") or {}).get("size")
            if expected_size is not None and size + int(expected_size) > MAX_BYTES:
                raise BackupError("Backuppen overstiger 150 MB. Brug et separat backupjob til denne størrelse.")
            content = client.storage.from_(item["bucket"]).download(item["path"])
            size += len(content)
            if size > MAX_BYTES:
                raise BackupError("Backuppen overstiger 150 MB. Brug et separat backupjob til denne størrelse.")
            if expected_size is not None and len(content) != int(expected_size):
                raise BackupError("En Storage-fil ændrede størrelse under backup. Prøv igen uden samtidige ændringer.")
            # Numeric archive names avoid traversal and Windows-invalid filenames.
            item["archive_path"] = f"storage/{index:08d}.bin"
            target = root / item["archive_path"]
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(content)
        buckets_after, objects_after = storage_inventory(client)
        if buckets != buckets_after or [{k: v for k, v in o.items() if k != "archive_path"} for o in objects] != objects_after:
            raise BackupError("Storage blev ændret under backup. Prøv igen, når ingen redigerer eller uploader.")
        guide = Path(__file__).resolve().parents[1] / "supabase" / "BACKUP.md"
        (root / "GENDANNELSE.md").write_bytes(guide.read_bytes())
        progress("Kontrollerer og pakker backup …")
        for path in sorted(root.rglob("*")):
            if path.is_file():
                manifest["files"].append({"path": path.relative_to(root).as_posix(),
                                          "bytes": path.stat().st_size,
                                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        archive = root / name
        with ZipFile(archive, "w", ZIP_DEFLATED) as z:
            for entry in manifest["files"]:
                z.write(root / entry["path"], entry["path"])
            z.write(root / "manifest.json", "manifest.json")
        with ZipFile(archive) as z:
            if z.testzip() is not None:
                raise BackupError("ZIP-kontrollen fejlede.")
            for entry in manifest["files"]:
                if hashlib.sha256(z.read(entry["path"])).hexdigest() != entry["sha256"]:
                    raise BackupError("Backupfilernes kontrolsummer stemmer ikke.")
        return name, archive.read_bytes(), len(objects)

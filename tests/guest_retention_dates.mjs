// Run: node tests/guest_retention_dates.mjs path/to/pglite/dist/index.js
import { pathToFileURL } from 'node:url';
import fs from 'node:fs';
import assert from 'node:assert/strict';
const { PGlite } = await import(pathToFileURL(process.argv[2]).href);
const db = new PGlite();
await db.exec('create role anon; create role authenticated;');
await db.exec(fs.readFileSync('supabase/migrations/20260820_create_historie.sql', 'utf8'));
await db.exec("insert into historie_new(season,booking_nr,navn,indcheck,storage_path) values (2024,1,'Test','2024-02-29','2024/2024-1.pdf'),(2026,2,'Test','2026-06-10',null),(2024,3,'Test',null,null)");
const migration = fs.readFileSync('supabase/migrations/20261029_guest_registration_retention.sql', 'utf8');
await db.exec(migration);
await db.exec(migration); // Safe reinstallation.
let result = await db.query("select booking_nr, to_char(delete_at at time zone 'UTC','YYYY-MM-DD HH24:MI') as due from historie_new order by booking_nr");
assert.deepEqual(result.rows.map(r=>r.due), ['2026-02-27 23:00', '2028-06-09 22:00', null]);
await db.exec("update historie_new set indcheck='2026-10-29', delete_at='2099-01-01' where booking_nr=2");
result = await db.query("select to_char(delete_at at time zone 'Europe/Copenhagen','YYYY-MM-DD HH24:MI') as due, storage_path, registration_deleted_at from historie_new where booking_nr=2");
assert.equal(result.rows[0].due, '2028-10-29 00:00');
assert.equal(result.rows[0].registration_deleted_at, null);
result = await db.query("select storage_path, navn from historie_new where booking_nr=1");
assert.equal(result.rows[0].storage_path, '2024/2024-1.pdf');
assert.equal(result.rows[0].navn, 'Test');
console.log('PASS: backfill, leap day, DST, missing dates, edits, no deletion, idempotent migration');
await db.close();

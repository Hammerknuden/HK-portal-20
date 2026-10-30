// Local PostgreSQL execution; never connects to Supabase.
import { pathToFileURL } from 'node:url';
import fs from 'node:fs';
import assert from 'node:assert/strict';
const { PGlite } = await import(pathToFileURL(process.argv[2]).href);
const db = new PGlite();
const rows = async sql => (await db.query(sql)).rows;
await db.exec(`create role anon; create role authenticated; create role service_role bypassrls;
create table high_season(season integer primary key, pace_archived boolean);
create table hk_dtb(id integer primary key, navn text);
insert into hk_dtb values(1,'Original copy unchanged');`);
for (const file of ['20260820_create_historie.sql', '20260905_add_booking_pace_fields_to_historie_new.sql',
                    '20260909_booking_pace_season_status.sql', '20260910_create_statistik_historik.sql',
                    '20261029_guest_registration_retention.sql']) {
  await db.exec(fs.readFileSync('supabase/migrations/'+file,'utf8'));
}
await db.exec(`alter table historie_new add column spouse text, add column notes text;
insert into high_season values(2026,true),(2027,false);
insert into statistik_historik(season,report_type,data)
select 2026, t, '[]'::jsonb from unnest(array['room_nights','danmarks_statistik','booking_channels',
  'returning_guests','gross_revenue_monthly','breakfast_monthly','checkins_daily','booking_length_monthly']) t;
insert into historie_new(season,booking_nr,navn,familie_navn,email,phone,spouse,spouce,comments,notes,
  indcheck,udcheck,booking_date,nationalitet,room_nights,num_rooms,web,registration_deleted_at)
select y, n, 'Guest', 'Surname','test@example.invalid','123','Partner','Legacy','Comment','Note',
 '2000-06-01','2000-06-04','1999-12-01','DK',6,2,w,now()
from (values(2022,1,'web'),(2026,2,'BC'),(2026,3,'cansl'),(2027,4,'web')) v(y,n,w);
insert into historie_new(season,booking_nr,navn,indcheck,registration_deleted_at)
values(2022,5,'Future',current_date,now()),(2022,6,'Missing',null,null),
 (2022,7,'PDF pending','2000-06-01',null);
update historie_new set storage_path='2022/2022-7.pdf' where booking_nr=7;`);
const migration = fs.readFileSync('supabase/migrations/20261030_history_personal_data_retention.sql','utf8');
await db.exec(migration);
await db.exec(migration);
const original = await rows('select * from historie_new order by id');
const statistics = await rows('select * from statistik_historik order by season,report_type');
const pace = await rows('select id,season,booking_nr,booking_date,room_nights,web from historie_new order by id');
let preview = (await rows('select clear_history_personal_data() as r'))[0].r;
assert.equal(preview.history_due,5);
assert.equal(preview.history_eligible,3);
assert.equal(preview.history_processed,0);
assert.equal(preview.history_documents_pending,1);
assert.equal(preview.history_statistics_pending,1);
assert.equal(preview.history_missing_checkin,1);
assert.deepEqual(await rows('select * from historie_new order by id'),original);
// Chunking must not lose or double-process rows.
assert.equal((await rows('select clear_history_personal_data(true,2) as r'))[0].r.history_processed,2);
assert.equal((await rows('select clear_history_personal_data(true,2) as r'))[0].r.history_processed,1);
assert.equal((await rows('select clear_history_personal_data(true,2) as r'))[0].r.history_processed,0);
const after = await rows('select * from historie_new order by id');
for (let i=0;i<after.length;i++) {
  if ([1,2,3].includes(after[i].booking_nr)) {
    for (const col of ['navn','familie_navn','email','phone','spouse','spouce','comments','notes']) {
      assert.equal(after[i][col],null);
    }
    assert.ok(after[i].personal_data_deleted_at);
    for (const col of Object.keys(original[i]).filter(k=>!['navn','familie_navn','email','phone','spouse','spouce','comments','notes','personal_data_deleted_at'].includes(k))) {
      assert.deepEqual(after[i][col],original[i][col],col);
    }
  } else assert.deepEqual(after[i],original[i]);
}
assert.deepEqual(await rows('select id,season,booking_nr,booking_date,room_nights,web from historie_new order by id'),pace);
assert.deepEqual(await rows('select * from statistik_historik order by season,report_type'),statistics);
assert.equal((await rows('select navn from hk_dtb'))[0].navn,'Original copy unchanged');
await db.exec("update historie_new set email='reimport@example.invalid' where booking_nr=1");
assert.equal((await rows('select clear_history_personal_data(true) as r'))[0].r.history_processed,1);
assert.equal((await rows('select email from historie_new where booking_nr=1'))[0].email,null);
// Incomplete archive and open years stay blocked, not silently damaged.
await db.exec("delete from statistik_historik where season=2026 and report_type='room_nights'; update historie_new set navn='Reimport' where booking_nr=2");
assert.equal((await rows('select clear_history_personal_data(true) as r'))[0].r.history_statistics_pending,2);
assert.equal((await rows('select navn from historie_new where booking_nr=2'))[0].navn,'Reimport');
for (const args of ['true,0','true,1001','null,100']) await assert.rejects(db.query(`select clear_history_personal_data(${args})`));
assert.equal((await rows("select has_function_privilege('authenticated','public.clear_history_personal_data(boolean,integer)','execute') as allowed"))[0].allowed,false);
assert.equal((await rows("select has_function_privilege('anon','public.clear_history_personal_data(boolean,integer)','execute') as allowed"))[0].allowed,false);
// Calendar-year boundary, independent of session timezone, including leap day.
assert.equal((await rows("select to_char((date '2024-02-29' + interval '5 years') at time zone 'Europe/Copenhagen' at time zone 'UTC','YYYY-MM-DD HH24:MI') as d"))[0].d,'2029-02-27 23:00');
console.log('PASS: preview, batching, idempotence, reimports, five-year dates, missing dates, document/archive guards, privileges, preserved pace fields/nationality/booking numbers/all snapshots');
await db.close();

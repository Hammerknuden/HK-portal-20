// Isolated PostgreSQL (PGlite), never connects to Supabase.
// node tests/optimizer_save.mjs path/to/pglite/dist/index.js
import { pathToFileURL } from 'node:url';
import { readFileSync } from 'node:fs';
import { randomUUID } from 'node:crypto';
import assert from 'node:assert/strict';
const { PGlite } = await import(pathToFileURL(process.argv[2]).href);
const db = new PGlite();
await db.exec(`
 create role anon; create role authenticated; create role service_role bypassrls;
 create table public.hk_dtb (
  id bigint primary key, booking_number bigint, room_number integer, season integer,
  checkin_date date, checkout_date date, movable boolean, web text
 );
 grant select, update on public.hk_dtb to service_role;
`);
await db.exec(readFileSync('supabase/migrations/20260917_apply_optimizer_plan.sql', 'utf8'));
const query = async (sql, params=[]) => (await db.query(sql, params)).rows;
const today = (await query("select (statement_timestamp() at time zone 'Europe/Copenhagen')::date::text as d"))[0].d;
const date = offset => {
 const d = new Date(today+'T00:00:00Z'); d.setUTCDate(d.getUTCDate()+offset); return d.toISOString().slice(0,10);
};
const season = Number(date(10).slice(0,4));
const moves = () => [
 {id:2, from_room:3, to_room:5, checkin_date:date(11), checkout_date:date(14)},
 {id:3, from_room:5, to_room:1, checkin_date:date(12), checkout_date:date(17)},
 {id:1, from_room:7, to_room:3, checkin_date:date(10), checkout_date:date(13)},
];
const seed = async () => {
 await db.exec('truncate hk_dtb, optimizer_plan_receipts');
 for (const m of moves()) await db.query(
  'insert into hk_dtb values ($1,$2,$3,$4,$5,$6,true,null)',
  [m.id,300+m.id,m.from_room,season,m.checkin_date,m.checkout_date]);
};
const call = async (id=randomUUID(), plan=moves(), year=season, candidate=1) =>
 (await query('select apply_optimizer_plan($1,$2,$3,$4::jsonb) as result', [id,year,candidate,JSON.stringify(plan)]))[0].result;
const snapshot = () => query('select * from hk_dtb order by id');
let count=0;
const test = async (name, fn) => {await fn();count++;console.log('OK',name);};
const reject = async (name, mutate, plan=moves, year=season, candidate=1) => test(name, async () => {
 await seed(); if(mutate) await mutate(); const before=await snapshot();
 await assert.rejects(call(randomUUID(),plan(),year,candidate));
 assert.deepEqual(await snapshot(),before);
 assert.equal((await query('select count(*)::int as n from optimizer_plan_receipts'))[0].n,0);
});

await test('save all three moves as service_role, keep dates', async () => {
 await seed(); const before=await snapshot();
 await db.exec('set role service_role');
 let result; try {result=await call();} finally {await db.exec('reset role');}
 assert.equal(result.status,'saved');assert.equal(result.moved_count,3);
 const after=await snapshot();
 assert.deepEqual(after.map(r=>r.room_number),[3,5,1]);
 for(let i=0;i<3;i++) assert.deepEqual({...after[i],room_number:before[i].room_number},before[i]);
});
await test('identical retry is idempotent, different payload rejected', async () => {
 await seed();const id=randomUUID();const result=await call(id);const after=await snapshot();
 assert.deepEqual(await call(id),result);
 const changed=moves();changed[0].to_room=4;
 await assert.rejects(call(id,changed));assert.deepEqual(await snapshot(),after);
 assert.equal((await query('select count(*)::int as n from optimizer_plan_receipts'))[0].n,1);
});
await reject('locked blocker',()=>db.exec('update hk_dtb set movable=false where id=2'));
await reject('unknown movable',()=>db.exec('update hk_dtb set movable=null where id=2'));
await reject('other season',()=>db.query('update hk_dtb set season=$1 where id=2',[season+1]));
await reject('changed source room',()=>db.exec('update hk_dtb set room_number=4 where id=2'));
await reject('changed stay',()=>db.query('update hk_dtb set checkout_date=$1 where id=2',[date(15)]));
await reject('deleted row',()=>db.exec('delete from hk_dtb where id=2'));
await reject('arriving today',()=>db.query('update hk_dtb set checkin_date=$1 where id=1',[today]),()=>{
 const p=moves();p[2].checkin_date=today;return p;
});
await reject('already checked in',()=>db.query('update hk_dtb set checkin_date=$1 where id=1',[date(-1)]),()=>{
 const p=moves();p[2].checkin_date=date(-1);return p;
});
await reject('duplicate row ID',null,()=>[...moves(),moves()[0]]);
await reject('missing temp candidate',null,()=>moves().slice(0,2));
await reject('room6 destination',null,()=>{const p=moves();p[0].to_room=6;return p;});
await reject('room7 destination',null,()=>{const p=moves();p[0].to_room=7;return p;});
await reject('no-op move',null,()=>{const p=moves();p[0].to_room=3;return p;});
await reject('room6 source',()=>db.exec('update hk_dtb set room_number=6 where id=2'),()=>{
 const p=moves();p[0].from_room=6;return p;
});
await reject('cancelled group through master row',()=>db.query(
 'insert into hk_dtb values(9,302,6,$1,$2,$3,true,$4)',[season,date(11),date(14),' CAN-SL ']));
await reject('overlap from new other-season booking rolls back all moves',()=>db.query(
 'insert into hk_dtb values(9,309,1,$1,$2,$3,false,null)',[season+1,date(15),date(18)]));
await reject('return move overlaps temp candidate',null,()=>{
 const p=moves();p[1].to_room=3;return p;
});
await test('adjacent departure and arrival is valid',async()=>{
 await seed();await db.query('insert into hk_dtb values(9,309,1,$1,$2,$3,false,null)',[season,date(17),date(18)]);
 assert.equal((await call()).status,'saved');
});
await test('cancelled neighbour does not block',async()=>{
 await seed();await db.query('insert into hk_dtb values(9,309,1,$1,$2,$3,false,$4)',[season,date(15),date(18),'cansl']);
 assert.equal((await call()).status,'saved');
});
await test('database error midway rolls back all updates and receipt',async()=>{
 await db.exec(`create function fail_optimizer_test() returns trigger language plpgsql as $$
 begin if new.id=3 then raise exception 'injected failure'; end if; return new; end; $$;
 create trigger fail_optimizer_test before update on hk_dtb for each row execute function fail_optimizer_test();`);
 await seed();const before=await snapshot();await assert.rejects(call());assert.deepEqual(await snapshot(),before);
 assert.equal((await query('select count(*)::int as n from optimizer_plan_receipts'))[0].n,0);
 await db.exec('drop trigger fail_optimizer_test on hk_dtb; drop function fail_optimizer_test()');
});
await test('public and authenticated callers cannot execute save',async()=>{
 for(const role of ['anon','authenticated']) {
  await db.exec(`set role ${role}`);
  try {await assert.rejects(call());} finally {await db.exec('reset role');}
 }
});
await db.close();console.log(`${count} SQL tests passed`);

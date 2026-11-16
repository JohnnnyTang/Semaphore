import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { DurableClient, DurableTransport, FixtureTransport, boardRows, commandId } from '../../web/durable-client.mjs';
const payloads = JSON.parse(await readFile(new URL('../../fixtures/durable/payloads.json', import.meta.url)));
const value = name => structuredClone(payloads.cases.find(item => item.name === name).value);
function setup(script) { const transport = new FixtureTransport(payloads, script); return { transport, client: new DurableClient(transport) }; }
test('cookie transport sends CSRF only on mutations and handles empty logout', async () => {
  const calls = []; const transport = new DurableTransport(async (url, options) => { calls.push({url, options}); return {status:204}; });
  transport.csrf = 'test'; await transport.request('/auth/session'); await transport.request('/auth/logout', {});
  assert.equal(calls[0].options.headers['X-CSRF-Token'], undefined); assert.equal(calls[1].options.headers['X-CSRF-Token'], 'test');
  assert.equal(calls[1].options.credentials, 'same-origin'); assert.equal(calls[1].options.cache, 'no-store');
});
test('lost create is never automatically retried; 404 discovery remains uncertain', async () => {
  const {client,transport} = setup([{path:'/games',networkError:true},{path:'/games/current',response:'not_found',status:404}]);
  await assert.rejects(client.create('fixture-artifact')); await assert.rejects(client.create('fixture-artifact'));
  await assert.rejects(client.discover()); assert.equal(client.creationUncertain,true);
  assert.equal(transport.calls.filter(call=>call.path==='/games').length,1);
});
test('successful discovery resolves uncertain creation', async () => {
  const {client} = setup([{path:'/games',networkError:true},{path:'/games/current',response:'envelope-snapshot'}]);
  await assert.rejects(client.create('fixture-artifact')); await client.discover(); assert.equal(client.creationUncertain,false);
});
test('uncertain clue preserves exact original ID, revision and payload; final receipt deduplicates', async () => {
  const game = value('envelope-snapshot').snapshot.game_id;
  const {client,transport} = setup([{path:`/games/${game}/commands`,networkError:true},{path:`/games/${game}/commands`,response:'envelope-pending'},{path:`/games/${game}/receipts/z1`,response:'envelope-clear'},{path:`/games/${game}`,response:'envelope-clear'}]);
  client.store.apply(value('envelope-snapshot')); await assert.rejects(client.send('icy','z1'));
  await client.retryCommand(); assert.deepEqual(transport.calls[0].body,transport.calls[1].body);
  const final = await client.refresh(); assert.ok(final.result); assert.equal(client.store.pending,null);
  assert.equal((await client.refresh()).result,null);
});
test('expired auth clears private state and CSRF', async () => {
  const {client,transport} = setup([{path:'/auth/login',response:'session'},{path:'/auth/session',response:'unauthenticated',status:401}]);
  await client.authenticate('login',value('login')); client.store.apply(value('envelope-snapshot'));
  await assert.rejects(client.restore()); assert.equal(client.session,null); assert.equal(client.store.snapshot,null); assert.equal(transport.csrf,null);
});
test('board cursor cannot cross artifact and invalid cursor does not silently restart', async () => {
  const {client,transport} = setup([{path:'/boards/first',response:'board'},{path:'/boards/first?cursor=bad',response:'invalid_cursor',status:400}]);
  await client.board('first'); await assert.rejects(client.board('second','cursor')); await assert.rejects(client.board('first','bad'));
  assert.equal(transport.calls.length,2);
});
test('empty lists and interrupted history preserve server competitive decision', async () => {
  const {client} = setup([{path:'/history',response:'history'},{path:'/boards/artifact',response:'board-empty'}]);
  const history = await client.page('/history'); assert.equal(history.items[1].competitive,false);
  assert.deepEqual((await client.board('artifact')).items,[]);
});
test('stale snapshots cannot rewind authoritative state', () => {
  const {client} = setup([]); client.store.apply(value('envelope-clear')); const revision = client.store.snapshot.revision;
  client.store.apply(value('envelope-snapshot')); assert.equal(client.store.snapshot.revision,revision);
});
test('public content uses text nodes, with semantic labels and reduced motion styling', async () => {
  const app = await readFile(new URL('../../web/durable-app.mjs', import.meta.url),'utf8');
  assert.ok(!app.includes('innerHTML')); assert.ok(app.includes('li.textContent'));
  const html = await readFile(new URL('../../web/durable.html', import.meta.url),'utf8'); assert.ok(html.includes('aria-live="polite"')); assert.ok(html.includes('for="clue"'));
  const css = await readFile(new URL('../../web/durable.css', import.meta.url),'utf8'); assert.ok(css.includes('prefers-reduced-motion')); assert.ok(css.includes('max-width:650px'));
});
test('late response after account removal cannot repopulate private state', async () => {
  let resolve; const client = new DurableClient({request:()=>new Promise(done=>{resolve=done;})});
  const pending = client.discover(); client.clearPrivate(); resolve(value('envelope-snapshot'));
  await assert.rejects(pending, /session_changed/); assert.equal(client.store.snapshot,null);
});
test('same-game discovery preserves uncertain command and receipt deduplication', async () => {
  const {client} = setup([{path:'/games/current',response:'envelope-snapshot'}]);
  client.store.apply(value('envelope-snapshot')); client.store.command('snow','keep-me'); client.store.seen.add('old');
  await client.discover(); assert.equal(client.store.pending.command_id,'keep-me'); assert.ok(client.store.seen.has('old'));
});
test('malformed JSON values fail safely as uncertain transport responses', async () => {
  for (const body of [null, [], 'text']) {
    const transport = new DurableTransport(async()=>({status:200,ok:true,json:async()=>body}));
    await assert.rejects(transport.request('/config'), /unavailable/);
  }
});
test('logout is a bodyless POST with session CSRF', async () => {
  let call; const transport = new DurableTransport(async (url,options)=>{call=options;return {status:204};});
  const client = new DurableClient(transport); transport.csrf='token'; await client.logout();
  assert.equal(call.method,'POST'); assert.equal(call.body,undefined); assert.equal(call.headers['X-CSRF-Token'],'token');
});


test('uncertain creation stays with its account through expiry but clears on account change', async () => {
  const first = value('session');
  const second = structuredClone(first); second.account.account_id = 'different-account';
  let response = first;
  const client = new DurableClient({ request: async path => {
    if (path === '/games') throw Object.assign(new Error('unavailable'), { code: 'unavailable' });
    if (path === '/auth/session') throw Object.assign(new Error('unauthenticated'), { status: 401 });
    return response;
  } });
  await client.authenticate('login', {});
  await assert.rejects(client.create('artifact'));
  await assert.rejects(client.restore());
  await client.authenticate('login', {});
  assert.equal(client.creationUncertain, true);
  await assert.rejects(client.create('artifact'), /creation_uncertain/);
  response = second;
  await client.authenticate('login', {});
  assert.equal(client.creationUncertain, false);
  assert.equal(client.uncertainAccountId, null);
});

test('explicit logout clears uncertain creation for the next signed-in account', async () => {
  const client = new DurableClient({request: async () => null});
  client.creationUncertain = true; client.uncertainAccountId = 'first-account';
  await client.logout();
  assert.equal(client.creationUncertain, false);
  assert.equal(client.uncertainAccountId, null);
});


test('session restoration preserves same-account commands and clears cross-tab account state', async () => {
  let response = value('session');
  let finishOldRequest;
  const client = new DurableClient({request: async path => {
    if (path === '/games/current') return new Promise(resolve => { finishOldRequest = resolve; });
    return structuredClone(response);
  }});
  await client.restore();
  client.store.apply(value('envelope-snapshot'));
  client.store.command('snow', 'uncertain-command');
  client.store.seen.add('already-animated');
  client.creationUncertain = true; client.uncertainAccountId = response.account.account_id;
  client.boardQuery = 'private-round';
  const priorStore = client.store;
  await client.restore();
  assert.equal(client.store, priorStore);
  assert.equal(client.store.pending.command_id, 'uncertain-command');
  assert.equal(client.creationUncertain, true);
  const oldRequest = client.discover();
  response = structuredClone(response); response.account.account_id = 'other-tab-account';
  await client.restore();
  finishOldRequest(value('envelope-snapshot'));
  await assert.rejects(oldRequest, /session_changed/);
  assert.equal(client.session.account.account_id, 'other-tab-account');
  assert.equal(client.store.snapshot, null);
  assert.equal(client.store.pending, null);
  assert.equal(client.store.seen.size, 0);
  assert.equal(client.creationUncertain, false);
  assert.equal(client.uncertainAccountId, null);
  assert.equal(client.boardQuery, null);
});


test('durable clear zone uses authoritative ranks 1 through zone_size', () => {
  const snapshot = value('envelope-snapshot').snapshot;
  snapshot.board = ['a', 'b', 'c', 'd', 'e']; snapshot.entries = {}; snapshot.zone_size = 3;
  snapshot.target = 'e';
  const rows = boardRows(snapshot);
  assert.deepEqual(rows.filter(row => row.inZone).map(row => row.rank), [1, 2, 3]);
  assert.equal(rows[4].target, true); assert.equal(rows[4].inZone, false);
  snapshot.board = ['a', 'b'];
  assert.ok(boardRows(snapshot).every(row => row.inZone));
});

test('LAN HTTP command IDs use cryptographic randomness without randomUUID', () => {
  let calls = 0;
  const id = commandId({ getRandomValues(bytes) { calls++; bytes.fill(255); return bytes; } });
  assert.equal(calls, 1);
  assert.equal(id, 'ffffffff-ffff-4fff-bfff-ffffffffffff');
  assert.equal(commandId({ randomUUID: () => 'native-id' }), 'native-id');
});

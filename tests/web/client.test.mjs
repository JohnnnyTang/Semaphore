import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { GameStore, clueLength, validateClue, resultText } from '../../web/store.mjs';
import { FixtureTransport, HttpTransport } from '../../web/transports.mjs';
const read = async name => JSON.parse(await readFile(new URL(`../../fixtures/protocol/${name}.json`, import.meta.url)));
const fixtureFetch = async url => ({ ok: true, json: () => read(url.split('/').at(-1).replace('.json', '')) });
test('Unicode hints count code points; blank and 121 emoji clues reject', () => {
  assert.equal(clueLength('🦊'), 1);
  assert.equal(validateClue('🦊'.repeat(120)), '');
  assert.match(validateClue('🦊'.repeat(121)), /120/);
  assert.match(validateClue('  '), /Type/);
});
test('pending admission, authoritative clear, stale receipt resolution and duplicate suppression', async () => {
  const { envelopes: [initial, pending, clear] } = await read('bottom-three-target-only');
  const store = new GameStore(); store.apply(initial);
  assert.deepEqual(store.command('ice', 'z1'), { command_id: 'z1', expected_revision: 0, clue: 'ice' });
  assert.equal(store.command('second', 'z2'), null);
  store.apply(pending); assert.equal(store.snapshot.score, 0);
  const newer = structuredClone(clear); newer.snapshot.revision = 4; newer.receipt = null;
  store.apply(newer); assert.equal(store.snapshot.score, 100);
  const result = store.apply(clear); assert.equal(store.snapshot.revision, 4);
  assert.equal(result.result.outcome, 'clear'); assert.equal(store.pending, null);
  assert.equal(store.apply(clear).result, null);
});
test('all frozen trace snapshots apply monotonically including terminal pending resolution', async () => {
  for (const name of ['inference-spawn-retry-and-reconnect', 'equal-time-overflow-beats-inference', 'event-player-clears']) {
    const { envelopes } = await read(name); const store = new GameStore();
    for (const envelope of envelopes) store.apply(envelope);
    const final = structuredClone(store.snapshot);
    for (const envelope of [...envelopes].reverse()) store.apply(envelope);
    assert.deepEqual(store.snapshot, final);
    assert.equal(store.snapshot.status, 'over'); assert.equal(store.pending, null);
  }
});
test('fixture adapter uses exact frozen score and maps transport command identity only', async () => {
  const transport = new FixtureTransport('bottom-three-target-only', fixtureFetch);
  const initial = await transport.create(); const waiting = await transport.snapshot();
  assert.deepEqual(initial, waiting);
  const pending = await transport.command(initial.snapshot.game_id, { command_id: 'browser-id', clue: 'arbitrary' });
  assert.equal(pending.receipt.command_id, 'browser-id'); assert.equal(pending.receipt.outcome, 'pending');
  const clear = await transport.snapshot();
  assert.equal(clear.receipt.command_id, 'browser-id'); assert.equal(clear.snapshot.score, 100);
  const duplicate = await transport.command(initial.snapshot.game_id, { command_id: 'browser-id' });
  assert.deepEqual(duplicate.receipt, clear.receipt);
});
test('HTTP adapter sends frozen payload exactly, never client score or target selection', async () => {
  const calls = []; const transport = new HttpTransport(async (url, options) => {
    calls.push({ url, options }); return { ok: true, json: async () => ({ protocol: 'experiment-v1' }) };
  });
  const command = { command_id: 'abc', expected_revision: 12, clue: 'Ice' };
  await transport.create({ artifact_id: 'default', mode: 'casual' });
  await transport.command('game/a', command); await transport.command('game/a', command);
  assert.equal(calls[1].url, '/experiment/v1/games/game%2Fa/commands');
  assert.equal(calls[1].options.body, JSON.stringify(command));
  assert.equal(calls[2].options.body, calls[1].options.body);
  assert.deepEqual(Object.keys(JSON.parse(calls[0].options.body)).sort(), ['artifact_id', 'mode']);
});
test('receipt_not_found stays structured and never displays internal messages', async () => {
  const transport = new HttpTransport(async () => ({ ok: false, json: async () => ({ code: 'receipt_not_found', message: 'private internal error' }) }));
  await assert.rejects(transport.receipt('id', 'command'), { code: 'receipt_not_found', message: 'receipt_not_found' });
  assert.match(resultText({ outcome: 'inference_failed' }), /Try again/);
});

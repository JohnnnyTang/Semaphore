import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { setImmediate } from 'node:timers/promises';

test('durable polling stays responsive without overlapping slow requests or polling hidden/private-ended views', async () => {
  // Execute the actual app event wiring with a minimal DOM and controllable service.
  // This isolates network scheduling; it is not real-browser or model evidence.
  const source = (await readFile(new URL('../../web/durable-app.mjs', import.meta.url), 'utf8'))
    .replace(/^import .*;\r?\n/gm, '');
  const elements = new Map();
  const document = { hidden: false, getElementById(id) {
    if (!elements.has(id)) elements.set(id, { value: '', options: [], checked: false,
      addEventListener() {}, replaceChildren() {}, append() {}, focus() {} });
    return elements.get(id);
  } };
  let client, tick, cadence, settle, reject, calls = 0, sends = 0;
  let outcome = 'stale_revision';
  class Client {
    constructor() { client = this; this.store = { snapshot: null }; }
    async request() { return { signup_enabled: true, clue_retention_days: 30, backup_retention_days: 30 }; }
    async restore() { this.session = { account: { display_name: 'Test player' } }; }
    async send() { sends++; return { result: { outcome } }; }
    async page() { return { items: [], next_cursor: null }; }
    async refresh() { calls++; return new Promise((resolve, fail) => { settle = resolve; reject = fail; }); }
  }
  const AsyncFunction = Object.getPrototypeOf(async function() {}).constructor;
  await new AsyncFunction('document', 'DurableClient', 'DurableTransport', 'boardRows', 'resultText', 'setInterval', source)(
    document, Client, class {}, () => [], () => '', (fn, milliseconds) => { tick = fn; cadence = milliseconds; });
  assert.ok(cadence > 0 && cadence <= 250, 'pending receipts checked within the 250ms UI budget');
  client.store.snapshot = { status: 'active', board: [], entries: {}, score: 0, level: 1 };
  tick(); assert.equal(calls, 1);
  // Multiple timer expirations while the same HTTP request is unresolved must coalesce.
  tick(); tick(); tick(); assert.equal(calls, 1);
  settle(); await setImmediate();
  tick(); assert.equal(calls, 2);
  reject(new Error('temporary network failure')); await setImmediate();
  document.hidden = true; tick(); assert.equal(calls, 2);
  document.hidden = false;
  const session = client.session;
  client.session = null; tick(); assert.equal(calls, 2);
  client.session = session;
  client.store.snapshot.status = 'over'; tick(); assert.equal(calls, 2);
  client.store.snapshot.status = 'active'; tick(); assert.equal(calls, 3, 'failed poll releases request guard');
  settle(); await setImmediate();
  const input = document.getElementById('clue');
  input.value = 'my association';
  document.getElementById('clue-form').onsubmit({ preventDefault() {} });
  await setImmediate();
  assert.equal(input.value, 'my association', 'stale rejection preserves the draft');
  assert.equal(sends, 1, 'no automatic resubmission after board changes');
  outcome = 'pending';
  document.getElementById('clue-form').onsubmit({ preventDefault() {} });
  await setImmediate();
  assert.equal(input.value, '', 'explicit accepted submission clears the draft');
  assert.equal(sends, 2);
});

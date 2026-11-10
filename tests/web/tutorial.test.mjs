import test from 'node:test';
import assert from 'node:assert/strict';
import { TutorialTransport } from '../../web/tutorial.mjs';

test('warm-up waits indefinitely, rejects incorrect examples, and progresses only on submitted input', async () => {
  const t = new TutorialTransport(); const initial = await t.create();
  for (let n=0; n<100; n++) assert.deepEqual(await t.snapshot(), initial);
  assert.match(t.note(true), /clock is paused/);
  const miss = await t.command('warm-up', {command_id:'bad', clue:'wrong'});
  assert.equal(miss.snapshot.target, 'moon'); assert.equal(t.step, 0);
  for (const [n, clue] of ['orbit','ocean','forest'].entries()) {
    const command = {command_id:String(n), clue};
    const result = await t.command('warm-up', command);
    assert.equal(t.step,n+1); assert.equal(result.snapshot.elapsed_ms,0);
    assert.equal(result.snapshot.status,'active'); assert.equal(result.snapshot.score,0);
    assert.deepEqual(await t.command('warm-up', command),result);
  }
  assert.equal(t.done,true); assert.equal((await t.snapshot()).snapshot.target,null);
  assert.match(t.note(), /Start the game/);
});

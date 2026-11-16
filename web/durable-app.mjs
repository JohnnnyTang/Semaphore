import { DurableClient, DurableTransport, boardRows } from './durable-client.mjs';
import { resultText } from './store.mjs';
const $ = id => document.getElementById(id);
const client = new DurableClient(new DurableTransport());
let composing = false;
$('clue').addEventListener('compositionstart', () => { composing = true; });
$('clue').addEventListener('compositionend', () => { composing = false; });
let config, packCursor, historyCursor, boardCursor, pageBusy = false, boardArtifact = null;
const say = text => { $('notice').textContent = text; };
const errorText = error => ({ unauthenticated: 'Your session expired. Sign in again.', invalid_credentials: 'Login name or password was not recognized.',
  signup_disabled: 'New accounts are disabled in this room.', creation_uncertain: 'The round may have started. Find your current round before choosing to start another.',
  unavailable: 'Connection interrupted. Reconnect to check what happened.', receipt_not_found: 'The clue receipt is not available. Retry the same clue to check admission.',
  not_found: 'Nothing was found. After an uncertain start, this does not prove the round never started.',
  game_expired: 'This game’s retry window has expired.', invalid_cursor: 'This page has expired or belongs to a different view. Refresh this view.',
  rate_limited: 'The room is busy. Wait before trying again.', csrf_invalid: 'Your session needs refreshing. Sign in again.',
}[error.code] || error.message || 'The request could not be completed.');
function render() {
  const signedIn = !!client.session;
  $('signed-in').hidden = !signedIn; $('signed-out').hidden = signedIn;
  if (!signedIn) { $('results').replaceChildren(); $('scores').replaceChildren(); $('packs').replaceChildren(); $('words').replaceChildren(); $('clue').value = ''; packCursor = historyCursor = boardCursor = null; boardArtifact = null; }
  $('identity').textContent = client.session?.account.display_name || '';
  $('new-confirm').hidden = !client.creationUncertain;
  $('start').disabled = pageBusy || client.creationUncertain || !$('consent').checked || !$('packs').value || client.store.snapshot?.status === 'active';
  $('new-confirm').disabled = pageBusy || !$('consent').checked || !$('packs').value;
  const snapshot = client.store.snapshot;
  $('play').hidden = !snapshot || !signedIn;
  if (!snapshot) return;
  $('score').textContent = `Score ${snapshot.score} · Level ${snapshot.level}`;
  $('target').textContent = snapshot.status === 'over' ? (['interrupted','quit'].includes(snapshot.end_reason) ? 'Round ended without a competitive result.' : `Round complete: ${snapshot.end_reason}. Check your results below.`) : `Target: ${snapshot.entries[snapshot.target]?.label || 'Waiting for a word'}`;
  $('words').replaceChildren(...boardRows(snapshot).map(row => {
    const li = document.createElement('li'); li.className = 'word' + (row.target ? ' target' : '') + (row.inZone ? ' zone' : '');
    li.textContent = `${row.rank}. ${row.label}${row.target ? ' — Target' : ''}${row.inZone ? ' — Clear zone' : ''}`; return li;
  }));
  const pending = !!client.store.pending || !!snapshot.pending;
  $('send').disabled = pageBusy || pending || snapshot.status !== 'active' || !snapshot.target;
  $('retry').hidden = !client.store.pending; $('retry').disabled = pageBusy;
  $('quit').disabled = pageBusy || snapshot.status !== 'active';
}
async function run(action) {
  if (pageBusy) return;
  pageBusy = true; render();
  try { await action(); } catch (error) { say(errorText(error)); }
  finally { pageBusy = false; render(); }
}
function appendRows(id, items, format, empty, append = false) {
  if (!append) $(id).replaceChildren();
  if (!items.length && !append) items = [null];
  for (const item of items) { const li = document.createElement('li'); li.textContent = item ? format(item) : empty; $(id).append(li); }
}
async function packs(append = false) {
  const data = await client.page('/packs', append ? packCursor : null);
  if (!append) $('packs').replaceChildren();
  for (const pack of data.items) for (const artifact of pack.artifacts) {
    const option = document.createElement('option'); option.value = artifact.artifact_id;
    option.textContent = `${pack.title} · v${pack.version} · ${artifact.artifact_id}`; $('packs').append(option);
  }
  packCursor = data.next_cursor; $('more-packs').hidden = !packCursor;
  if (!$('packs').options.length) say('No packs are installed yet. Ask the room operator to install one.');
}
async function history(append = false) {
  const data = await client.page('/history', append ? historyCursor : null);
  appendRows('results', data.items, row => `${row.cohort.pack_id} · ${row.competitive ? row.score + ' points' : 'No competitive result'} · ${row.end_reason}`, 'No completed rounds yet.', append);
  historyCursor = data.next_cursor; $('more-history').hidden = !historyCursor;
}
async function board(append = false) {
  const artifact = $('packs').value; if (!artifact) return;
  if (append && artifact !== boardArtifact) return;
  const data = await client.board(artifact, append ? boardCursor : null);
  appendRows('scores', data.items, row => `${row.display_name} · ${row.score} points`, 'No scores for this round yet.', append);
  boardCursor = data.next_cursor; boardArtifact = artifact; $('more-board').hidden = !boardCursor;
}
$('auth').addEventListener('submit', event => {
  event.preventDefault(); const kind = event.submitter?.value || 'login';
  const body = { login_name: $('login').value, password: $('password').value };
  if (kind === 'signup') body.display_name = $('display').value;
  $('password').value = '';
  run(async () => { await client.authenticate(kind, body); $('consent').checked = false; await packs(); await history(); say('Signed in. Choose an installed round.'); });
});
$('logout').onclick = () => run(async () => { await client.logout(); say('Signed out.'); });
$('consent').onchange = render;
$('packs').onchange = () => { boardCursor = null; boardArtifact = null; client.boardQuery = null; $('scores').replaceChildren(); $('more-board').hidden = true; render(); };
for (const [id, fn] of [['more-packs',()=>packs(true)],['history',()=>history()],['more-history',()=>history(true)],['board',()=>board()],['more-board',()=>board(true)]]) $(id).onclick = () => run(fn);
for (const [id, explicit] of [['start',false],['new-confirm',true]]) $(id).onclick = () => run(async () => {
  await client.create($('packs').value, explicit); say('Round started. Find an association for the target.'); $('clue').focus();
});
$('discover').onclick = () => run(async () => { await client.discover(); say('Current round recovered.'); });
$('refresh').onclick = () => run(async () => { const change = await client.refresh(); say(change?.result ? resultText(change.result) : 'Round synchronized.'); });
$('retry').onclick = () => run(async () => { const change = await client.retryCommand(); say(change?.result ? resultText(change.result) : 'Checking the same clue…'); });
$('quit').onclick = () => run(async () => { await client.quit(); await history(); say('Round ended.'); });
$('clue-form').onsubmit = event => { event.preventDefault(); if (composing) return; run(async () => {
  const change = await client.send($('clue').value); $('clue').value = ''; say(change?.result ? resultText(change.result) : 'Ranking your clue…');
}); };
// One request at a time; hidden tabs pause polling. Revisions and receipt IDs deduplicate results.
setInterval(() => {
  if (!document.hidden && !pageBusy && client.session && client.store.snapshot?.status === 'active') run(async () => {
    const change = await client.refresh(); if (change?.result) say(resultText(change.result));
    if (client.store.snapshot?.status === 'over') await history();
  });
}, 1500);
await run(async () => {
  config = await client.request('/config'); $('signup').hidden = !config.signup_enabled;
  $('privacy').textContent = `Your clues are saved privately for up to ${config.clue_retention_days} days. Encrypted backups may retain deleted clues for up to ${config.backup_retention_days} additional days. They do not appear on the public board.`;
  try { await client.restore(); await packs(); await history(); say('Welcome back. Find your current round or start a new one.'); }
  catch (error) { if (error.status !== 401) throw error; say('Sign in to your local room.'); }
});

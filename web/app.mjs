import { GameStore, clueLength, validateClue, resultText } from './store.mjs';
import { HttpTransport, FixtureTransport } from './transports.mjs';
const $ = id => document.getElementById(id);
let store = new GameStore(), transport, polling = false, connected = true, composing = false;
let epoch = 0, rows = new Map(), finished = false, renderToken = 0, settings;
const reduced = matchMedia('(prefers-reduced-motion: reduce)');
const params = new URLSearchParams(location.search);
$('transport').value = params.get('transport') === 'http' ? 'http' : 'fixture';
$('artifact').value = params.get('artifact') || 'default';
function options() {
  $('fixture-options').hidden = $('transport').value !== 'fixture';
  $('http-options').hidden = $('transport').value !== 'http';
}
options(); $('transport').addEventListener('change', options);
$('help-open').onclick = () => $('help').showModal();
function persist() {
  if (settings?.kind !== 'http') return;
  try { sessionStorage.setItem('semaphore-game', JSON.stringify({ settings, snapshot: store.snapshot,
    pending: store.pending, seen: [...store.seen], draft: $('clue').value })); } catch { /* Storage optional. */ }
}
function removeSaved() { try { sessionStorage.removeItem('semaphore-game'); } catch { /* Optional. */ } }
function drawWords(board, target, snapshot) {
  const positions = new Map([...rows].map(([id, row]) => [id, row.getBoundingClientRect().top]));
  const visible = new Set(board);
  for (const [id, row] of rows) if (!visible.has(id)) { row.remove(); rows.delete(id); }
  for (let index = board.length - 1; index >= 0; index--) {
    const id = board[index];
    let row = rows.get(id);
    if (!row) { row = document.createElement('li'); rows.set(id, row); }
    row.className = `word${index < snapshot.zone_size ? ' zone' : ''}${index === Math.min(snapshot.zone_size, board.length) - 1 ? ' zone-start' : ''}${id === target ? ' target' : ''}`;
    row.replaceChildren();
    const label = document.createElement('span'); label.className = 'label';
    if (index === Math.min(snapshot.zone_size, board.length) - 1) {
      const caption = document.createElement('span'); caption.className = 'zone-caption';
      caption.textContent = 'Clear zone'; label.append(caption);
    }
    label.append(document.createTextNode(snapshot.entries[id]?.label || id)); row.append(label);
    if (id === target) { const flag = document.createElement('span'); flag.className = 'flag'; flag.textContent = 'Target'; row.append(flag); }
    if (index < snapshot.zone_size) { const hint = document.createElement('span'); hint.className = 'sr-only'; hint.textContent = ', in clear zone'; row.append(hint); }
    $('words').append(row);
  }
  if (!reduced.matches) for (const [id, row] of rows) {
    row.getAnimations().forEach(animation => animation.cancel());
    const old = positions.get(id), now = row.getBoundingClientRect().top;
    if (old !== undefined && old !== now) row.animate([{ transform: `translateY(${old - now}px)` }, { transform: 'translateY(0)' }], { duration: 260, easing: 'ease-out' });
  }
}
function updateControls() {
  const s = store.snapshot; if (!s) return;
  const pending = !!store.pending || !!s.pending;
  $('clue').readOnly = pending;
  $('send').disabled = pending || !connected || !s.target || s.status !== 'active';
  $('send').firstChild.textContent = pending ? 'Ranking your clue… ' : 'Send clue ';
  $('reconnect').hidden = connected;
  $('connection').textContent = connected ? '' : 'Reconnecting. The game clock is still running. Your clue is kept in this tab.';
}
function render(result) {
  const s = store.snapshot; if (!s) return;
  const token = ++renderToken;
  $('welcome').hidden = true; $('game').hidden = false;
  $('source').textContent = settings.kind === 'fixture' ? 'Scripted practice / recorded outcomes' : `${s.mode === 'event' ? 'Event' : 'Casual'} / LAN game`;
  $('occupancy').textContent = `${s.board.length} of ${s.capacity} words`;
  $('next-spawn').textContent = s.status === 'over' ? 'Finished' : s.next_spawn_ms === null ? 'No more arrivals' : `Next word in ${Math.max(0, Math.ceil((s.next_spawn_ms - s.elapsed_ms) / 1000))} s`;
  $('score').textContent = s.score; $('level').textContent = s.level;
  const targetText = s.target ? s.entries[s.target]?.label || s.target : 'Next word arriving soon';
  if ($('target').textContent !== targetText) $('target').textContent = targetText;
  $('zone-note').textContent = s.board.length <= s.zone_size ? 'All remaining words are in the clear zone.' : `Bottom ${s.zone_size}: clear zone`;
  const details = { 'Pack version digest': s.identities.pack_digest, 'Challenge': s.identities.challenge_digest || 'No event challenge',
    'Rules': s.identities.ruleset_id, 'Model': s.identities.model_fingerprint, 'Revision': s.revision };
  $('details').replaceChildren();
  for (const [key, value] of Object.entries(details)) {
    const dt = document.createElement('dt'), dd = document.createElement('dd'); dt.textContent = key; dd.textContent = value; $('details').append(dt, dd);
  }
  if (result) {
    const success = ['clear', 'miss'].includes(result.outcome);
    $('result').textContent = resultText(result) + (success && s.target ? ` Next target: ${s.entries[s.target]?.label || s.target}.` : '');
    $('result').className = success ? '' : 'error';
    if (success) $('clue').value = '';
    else if (document.activeElement === $('clue') || document.activeElement === $('send')) { $('clue').focus({ preventScroll: true }); $('clue').select(); }
    const current = result.applied_revision === s.revision;
    if (current && success && !reduced.matches && s.status !== 'over') {
      drawWords(result.ranked_board, result.target, s);
      setTimeout(() => { if (token === renderToken) drawWords(store.snapshot.board, store.snapshot.target, store.snapshot); }, 280);
    } else drawWords(s.board, s.target, s);
  } else drawWords(s.board, s.target, s);
  const practiceDone = settings.kind === 'fixture' && transport.index === transport.frames.length - 1 && !store.pending;
  const over = s.status === 'over' || practiceDone;
  $('active-controls').hidden = over; $('ending').hidden = !over;
  if (over) {
    const reasons = { overflow: 'The stack filled up', pack_cleared: 'Pack complete', pack_exhausted: 'Pack complete', event_complete: 'Challenge complete', interrupted: 'Game interrupted' };
    $('end-title').textContent = practiceDone && s.status !== 'over' ? 'Practice sequence complete' : reasons[s.end_reason];
    $('end-detail').textContent = `${s.score} points. ${s.clears} target${s.clears === 1 ? '' : 's'} cleared.${s.end_reason === 'interrupted' ? ' This is not an official ranked result.' : ''}`;
    if (!finished) {
      $('end-title').focus({ preventScroll: true }); finished = true;
    }
  }
  updateControls(); updateCount(); persist();
}
function apply(envelope) {
  const change = store.apply(envelope);
  if (change.accepted || change.result) render(change.result);
  // Each HTTP envelope is a complete snapshot; no intermediate state is guessed at gaps.
}
function failure(error) {
  connected = false; updateControls();
  if (['game_expired', 'not_found'].includes(error.code)) {
    $('connection').textContent = 'This game is no longer available. Leave and play again.'; removeSaved();
  }
}
async function reconcile() {
  const id = store.snapshot.game_id, run = epoch;
  const snapshot = await transport.snapshot(id);
  if (run !== epoch) return;
  apply(snapshot);
  if (store.pending) {
    const command = store.pending;
    try { const receipt = await transport.receipt(id, command.command_id); if (run !== epoch) return; apply(receipt); }
    catch (error) {
      if (error.code !== 'receipt_not_found') throw error;
      // A lost POST is retried with exactly the original ID, revision and clue.
      const response = await transport.command(id, command); if (run !== epoch) return; apply(response);
    }
  }
  connected = true; updateControls();
}
async function poll() {
  if (polling || !store.snapshot || finished || document.hidden) return;
  polling = true;
  try { await reconcile(); } catch (error) { failure(error); }
  finally { polling = false; }
}
setInterval(poll, 250);
$('reconnect').onclick = poll;
document.addEventListener('visibilitychange', () => { if (!document.hidden) poll(); });
async function start() {
  epoch++; const run = epoch; finished = false; connected = true; rows.clear(); $('words').replaceChildren();
  store = new GameStore(); removeSaved(); $('result').textContent = ''; $('clue').value = '';
  settings = { kind: $('transport').value, scenario: $('scenario').value, artifact: $('artifact').value.trim(), mode: $('mode').value };
  transport = settings.kind === 'http' ? new HttpTransport() : new FixtureTransport(settings.scenario);
  $('play').disabled = true; $('start-error').textContent = '';
  try {
    const envelope = await transport.create({ mode: settings.mode, artifact_id: settings.artifact });
    if (run !== epoch) return; apply(envelope); $('clue').focus({ preventScroll: true });
  } catch { $('start-error').textContent = 'The game could not start. Check the server and artifact ID, then try again.'; }
  finally { $('play').disabled = false; }
}
$('start-form').onsubmit = event => { event.preventDefault(); start(); };
$('again').onclick = () => { $('game').hidden = true; $('welcome').hidden = false; start(); };
$('leave').onclick = async () => {
  if (settings.kind === 'http' && store.snapshot.status === 'active') {
    try { apply(await transport.quit(store.snapshot.game_id)); } catch (error) { failure(error); }
  }
  epoch++; finished = true; removeSaved(); store = new GameStore(); $('game').hidden = true; $('welcome').hidden = false; $('play').focus();
};
function updateCount() { $('clue-count').textContent = `${120 - clueLength($('clue').value)} characters available`; }
$('clue').oninput = () => { updateCount(); persist(); };
$('clue').addEventListener('compositionstart', () => { composing = true; });
$('clue').addEventListener('compositionend', () => { composing = false; });
$('clue').addEventListener('keydown', event => { if (event.key === 'Enter' && (event.isComposing || composing || event.keyCode === 229)) event.preventDefault(); });
$('clue-form').onsubmit = async event => {
  event.preventDefault(); if (composing || !connected) return;
  const message = validateClue($('clue').value);
  if (message) { $('result').textContent = message; $('result').className = 'error'; return; }
  const command = store.command($('clue').value, Array.from(crypto.getRandomValues(new Uint32Array(4)), n => n.toString(16).padStart(8, '0')).join('')); if (!command) return;
  const run = epoch;
  $('result').textContent = 'Ranking your clue…'; $('result').className = ''; updateControls(); persist();
  try { const envelope = await transport.command(store.snapshot.game_id, command); if (run === epoch) apply(envelope); }
  catch (error) { if (run === epoch) failure(error); }
};
// Reload resumes the same server game and preserves an uncertain command exactly.
try {
  const saved = JSON.parse(sessionStorage.getItem('semaphore-game') || 'null');
  if (saved?.settings?.kind === 'http' && saved.snapshot) {
    settings = saved.settings; transport = new HttpTransport(); store.snapshot = saved.snapshot;
    store.pending = saved.pending; store.seen = new Set(saved.seen); $('clue').value = saved.draft || '';
    connected = false; render(); poll();
  }
} catch { removeSaved(); }

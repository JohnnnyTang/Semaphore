import { TutorialTransport } from './tutorial.mjs';
import { GameStore, clueLength, validateClue, resultText } from './store.mjs';
import { HttpTransport, FixtureTransport } from './transports.mjs';
const $ = id => document.getElementById(id);
let store = new GameStore(), transport, polling = false, connected = true, composing = false;
let epoch = 0, rows = new Map(), finished = false, settings, boardSignature = '';
const reduced = matchMedia('(prefers-reduced-motion: reduce)');
function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  const next = theme === 'dark' ? 'light' : 'dark';
  $('theme-toggle').textContent = next === 'dark' ? 'Dark theme' : 'Light theme';
  $('theme-toggle').setAttribute('aria-label', 'Switch to ' + next + ' theme');
  try { localStorage.setItem('semaphore-theme', theme); } catch { /* Optional preference. */ }
}
let preferredTheme;
try { preferredTheme = localStorage.getItem('semaphore-theme'); } catch { /* Optional. */ }
setTheme(['light', 'dark'].includes(preferredTheme) ? preferredTheme : matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
$('theme-toggle').onclick = () => setTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark');
const params = new URLSearchParams(location.search);
$('transport').value = params.get('transport') === 'fixture' ? 'fixture' : 'http';
$('artifact').value = params.get('artifact') || 'default';
function options() {
  $('fixture-options').hidden = $('transport').value !== 'fixture';
  $('http-options').hidden = $('transport').value !== 'http';
}
options(); $('transport').addEventListener('change', options);
$('help-open').onclick = () => $('help').showModal();
function persist() {
  if (settings?.kind !== 'http' || transport instanceof TutorialTransport) return;
  try { sessionStorage.setItem('semaphore-game', JSON.stringify({ settings, snapshot: store.snapshot,
    pending: store.pending, seen: [...store.seen], draft: $('clue').value })); } catch { /* Storage optional. */ }
}
function removeSaved() { try { sessionStorage.removeItem('semaphore-game'); } catch { /* Optional. */ } }
function drawWords(board, target, snapshot) {
  const signature = JSON.stringify([board, target, snapshot.zone_size, board.map(id => snapshot.entries[id]?.label)]);
  if (signature === boardSignature) return;
  boardSignature = signature;
  // Read both the visible position and the resting layout before changing any rows.
  // An in-flight arrival keeps its animation unless its destination actually moves.
  const positions = new Map([...rows].map(([id, row]) => [id, {
    top: row.getBoundingClientRect().top, layout: row.offsetTop
  }]));
  const list = $('words');
  const visible = new Set(board);
  for (const [id, row] of rows) if (!visible.has(id)) {
    row.getAnimations().forEach(animation => animation.cancel());
    row.remove(); rows.delete(id);
  }
  let cursor = list.firstElementChild;
  for (let index = board.length - 1; index >= 0; index--) {
    const id = board[index];
    let row = rows.get(id);
    if (!row) { row = document.createElement('li'); rows.set(id, row); }
    row.className = `word${index < snapshot.zone_size ? ' zone' : ''}${index === Math.min(snapshot.zone_size, board.length) - 1 ? ' zone-start' : ''}${id === target ? ' target' : ''}`;
    const contentSignature = JSON.stringify([index, snapshot.zone_size, target === id, snapshot.entries[id]?.label]);
    if (row.dataset.contentSignature !== contentSignature) {
      row.dataset.contentSignature = contentSignature;
      row.replaceChildren();
      const rank = document.createElement('span'); rank.className = 'rank-number'; rank.textContent = String(index + 1).padStart(2, '0'); rank.setAttribute('aria-hidden', 'true'); row.append(rank);
      const label = document.createElement('span'); label.className = 'label';
      if (index === Math.min(snapshot.zone_size, board.length) - 1) {
        const caption = document.createElement('span'); caption.className = 'zone-caption';
        caption.textContent = 'Clear zone'; caption.className = 'sr-only'; label.append(caption);
      }
      label.append(document.createTextNode(snapshot.entries[id]?.label || id)); row.append(label);
      if (id === target) { const flag = document.createElement('span'); flag.className = 'flag'; flag.textContent = 'Target'; row.append(flag); }
      if (index < snapshot.zone_size) { const hint = document.createElement('span'); hint.className = 'sr-only'; hint.textContent = ', in clear zone'; row.append(hint); }
    }
    // Inserting at the cursor leaves every already-correct node attached and steady.
    if (row !== cursor) list.insertBefore(row, cursor);
    cursor = row.nextElementSibling;
  }
  if (reduced.matches) {
    for (const row of rows.values()) row.getAnimations().forEach(animation => animation.cancel());
    return;
  }
  const ceiling = document.querySelector('.stack').getBoundingClientRect().top;
  const destinations = [...rows].map(([id, row]) => ({ id, row,
    layout: row.offsetTop, height: row.offsetHeight }));
  for (const { id, row, layout, height } of destinations) {
    const old = positions.get(id);
    if (old && Math.abs(old.layout - layout) < 0.5) continue;
    row.getAnimations().forEach(animation => animation.cancel());
    const now = row.getBoundingClientRect().top;
    const delta = old ? old.top - now : ceiling - now - height;
    if (Math.abs(delta) < 0.5) continue;
    row.animate([
      { transform: `translateY(${delta}px)`, zIndex: 2 },
      { transform: 'translateY(0)', zIndex: 2 }
    ], {
      duration: old ? 650 : Math.max(850, 1500 - ((snapshot.level || 1) - 1) * 100),
      // Arrivals remain opaque and accelerate from the ceiling, easing into their slot.
      easing: old ? 'cubic-bezier(.2,.7,.2,1)' : 'cubic-bezier(.4,0,.65,1)',
      fill: 'backwards'
    });
  }
}
function clearEffects(result, snapshot) {
  if (result.outcome !== 'clear') return;
  const waves = result.clear_waves || [[result.target]];
  if (reduced.matches) return; // The persistent result describes every clear without motion.
  const stack = document.querySelector('.stack'), bounds = stack.getBoundingClientRect();
  waves.forEach((wave, index) => wave.forEach(id => {
    const row = rows.get(id);
    const rect = row?.getBoundingClientRect() || { top: bounds.bottom - 40, left: bounds.left + 60 };
    const ghost = row ? row.cloneNode(true) : document.createElement('li');
    if (!row) ghost.textContent = snapshot.entries[id]?.label || id;
    const label = row?.querySelector('.label');
    const origin = label?.getBoundingClientRect() || rect;
    const text = snapshot.entries[id]?.label || id;
    [...text].slice(0, 32).forEach((letter, n) => {
      const particle = document.createElement('span'); particle.className = 'clear-letter';
      particle.textContent = letter; particle.setAttribute('aria-hidden', 'true');
      Object.assign(particle.style, { left: `${origin.left - bounds.left + n * 10}px`, top: `${origin.top - bounds.top}px` });
      stack.append(particle);
      const direction = (n % 2 ? 1 : -1);
      particle.animate([{ opacity: 1, transform: 'translate(0,0) rotate(0)' },
        { opacity: 0, transform: `translate(${direction * (35 + n * 7)}px,${-70 - (n % 4) * 20}px) rotate(${direction * 110}deg)` }],
        { duration: 850, delay: Math.min(index * 140, 1800), fill: 'both', easing: 'ease-out' }).finished.catch(() => {}).finally(() => particle.remove());
    });
    const points = document.createElement('span'); points.className = 'clear-points'; points.textContent = '+100'; points.setAttribute('aria-hidden', 'true');
    Object.assign(points.style, { right: '24px', top: `${rect.top - bounds.top}px` }); stack.append(points);
    points.animate([{ opacity: 1, transform: 'translateY(0) scale(.8)' }, { opacity: 1, offset: .3, transform: 'translateY(-20px) scale(1.15)' }, { opacity: 0, transform: 'translateY(-65px) scale(1)' }], { duration: 1000, delay: Math.min(index * 140, 1800), fill: 'both' }).finished.catch(() => {}).finally(() => points.remove());
    ghost.className = 'word clear-echo'; ghost.setAttribute('aria-hidden', 'true');
    Object.assign(ghost.style, { top: `${rect.top - bounds.top}px`, left: '0', width: '100%' });
    stack.append(ghost);
    const animation = ghost.animate([
      { opacity: 0.95, transform: 'translateX(0)', filter: 'brightness(1)' },
      { opacity: 1, offset: 0.25, transform: 'translateX(8px)', filter: 'brightness(1.25)' },
      { opacity: 0, transform: 'translateX(65px)', filter: 'brightness(1)' }
    ], { duration: 480, delay: Math.min(index * 140, 1800), fill: 'both', easing: 'ease-out' });
    animation.finished.catch(() => {}).finally(() => ghost.remove());
  }));
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
let clockSample = performance.now();
function drawClock() {
  const s = store.snapshot; if (!s) return;
  const elapsed = s.elapsed_ms + Math.max(0, performance.now() - clockSample);
  $('next-spawn').textContent = transport instanceof TutorialTransport ? 'Paused for you' : s.status === 'over' ? 'Finished' : settings.kind === 'fixture' ? 'Replay clock · advances with clues' : s.next_spawn_ms === null ? 'No more arrivals' : `Next word in ${Math.max(0, Math.ceil((s.next_spawn_ms - elapsed) / 1000))} s`;
}
setInterval(drawClock, 100);
function render(result) {
  const s = store.snapshot; if (!s) return;
  $('welcome').hidden = true; $('game').hidden = false; document.body.classList.add('playing');
  const tutorial = transport instanceof TutorialTransport;
  $('source').textContent = tutorial ? 'Guided warm-up / clock paused' : settings.kind === 'fixture' ? 'Scripted practice / recorded outcomes' : `${s.mode === 'event' ? 'Event' : 'Casual'} / LAN game`;
  document.querySelector('.stack').style.setProperty('--capacity', s.capacity);
  document.querySelector('.headroom span').hidden = s.capacity - s.board.length < 2;
  $('capacity-warning').textContent = (s.capacity - s.board.length) + ' spaces left';
  $('occupancy').textContent = `${s.board.length} of ${s.capacity} words`;
  drawClock();
  $('score').textContent = s.score; $('level').textContent = s.level;
  const paced = s.identities.ruleset_id === 'experiment-arcade-paced-v1';
  $('pace-note').textContent = paced ? (s.score >= 3000 ? 'Maximum pace' : 'Next pace increase at ' + (Math.floor(s.score / 500) + 1) * 500 + ' points') : 'Fixed arrival schedule';
  const targetText = s.target ? s.entries[s.target]?.label || s.target : 'Next word arriving soon';
  if ($('target').textContent !== targetText) $('target').textContent = targetText;
  $('zone-note').textContent = `Clear zone · positions 1–${s.zone_size}`;
  $('instruction').hidden = !tutorial;
  $('streak').textContent = `${s.streak || 0} / 5`;
  $('streak-stat').hidden = tutorial || !paced;
  $('begin-game').hidden = !tutorial || !transport.done;
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
    if (tutorial) $('result').textContent = result.outcome === 'clear' ? 'Connection made.' : 'Use the example clue above to continue.';
    else if (document.activeElement === $('clue') || document.activeElement === $('send')) { $('clue').focus({ preventScroll: true }); $('clue').select(); }
    clearEffects(result, s);
    drawWords(s.board, s.target, s);
    if (result.outcome === 'clear' && !reduced.matches) {
      $('score').animate([{ transform: 'scale(1.25)' }, { transform: 'scale(1)' }], { duration: 400 });
      $('result').animate([{ opacity: 0 }, { opacity: 1 }], { duration: 300 });
    }
  } else drawWords(s.board, s.target, s);
  if (tutorial) {
    $('instruction').textContent = transport.note(!!$('clue').value);
    if (result && transport.done) $('begin-game').focus({ preventScroll: true });
  }
  const practiceDone = !tutorial && settings.kind === 'fixture' && transport.index === transport.frames.length - 1 && !store.pending;
  const over = s.status === 'over' || practiceDone;
  $('active-controls').hidden = over; $('ending').hidden = !over;
  if (over) {
    const reasons = { overflow: 'The stack filled up', pack_cleared: 'Pack complete', pack_exhausted: 'Pack complete', event_complete: 'Challenge complete', interrupted: 'Game interrupted' };
    $('end-title').textContent = practiceDone && s.status !== 'over' ? 'Practice sequence complete' : reasons[s.end_reason];
    $('end-detail').textContent = `${s.score} points. ${s.clears} word${s.clears === 1 ? '' : 's'} cleared.${s.end_reason === 'interrupted' ? ' This is not an official ranked result.' : ''}`;
    if (!finished) {
      $('end-title').focus({ preventScroll: true }); finished = true;
    }
  }
  updateControls(); updateCount(); persist();
}
function apply(envelope) {
  const change = store.apply(envelope);
  if (change.accepted) clockSample = performance.now();
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
async function start(skipTutorial = false) {
  if ($('play').disabled) return;
  const run = ++epoch;
  const nextSettings = { kind: $('transport').value, scenario: $('scenario').value, artifact: $('artifact').value.trim(), mode: $('mode').value };
  const nextTransport = !skipTutorial && !$('skip-tutorial').checked ? new TutorialTransport() : nextSettings.kind === 'http' ? new HttpTransport() : new FixtureTransport(nextSettings.scenario);
  const errorMessage = $(skipTutorial ? 'begin-error' : 'start-error');
  $('play').disabled = $('begin-game').disabled = true;
  $('start-error').textContent = $('begin-error').textContent = '';
  try {
    const envelope = await nextTransport.create({ mode: nextSettings.mode, artifact_id: nextSettings.artifact });
    if (run !== epoch) return;
    document.querySelectorAll('.clear-echo,.clear-letter,.clear-points').forEach(node => { node.getAnimations().forEach(a => a.cancel()); node.remove(); });
    finished = false; connected = true; boardSignature = ''; rows.clear(); $('words').replaceChildren();
    store = new GameStore(); removeSaved(); $('result').textContent = ''; $('clue').value = '';
    settings = nextSettings; transport = nextTransport;
    apply(envelope); $('clue').focus({ preventScroll: true });
  } catch {
    if (run === epoch) {
      errorMessage.textContent = 'The game could not start. Check the server and artifact ID, then try again.';
    }
  } finally {
    $('play').disabled = $('begin-game').disabled = false;
    if (run === epoch && errorMessage.textContent) $(skipTutorial ? 'begin-game' : 'play').focus();
  }
}
$('begin-game').onclick = () => start(true);
$('start-form').onsubmit = event => { event.preventDefault(); start(); };
$('again').onclick = () => { $('game').hidden = true; $('welcome').hidden = false; start(); };
$('leave').onclick = async () => {
  if (!(transport instanceof TutorialTransport) && settings.kind === 'http' && store.snapshot.status === 'active') {
    try { apply(await transport.quit(store.snapshot.game_id)); } catch (error) { failure(error); }
  }
  epoch++; finished = true; removeSaved(); store = new GameStore(); $('game').hidden = true; $('welcome').hidden = false; document.body.classList.remove('playing'); $('play').focus();
};
function updateCount() { $('clue-count').textContent = `${120 - clueLength($('clue').value)} characters available`; }
$('clue').oninput = () => { updateCount(); if (transport instanceof TutorialTransport) $('instruction').textContent = transport.note(!!$('clue').value); persist(); };
$('clue').addEventListener('compositionstart', () => { composing = true; });
$('clue').addEventListener('compositionend', () => { composing = false; });
$('clue').addEventListener('keydown', event => { if (event.key === 'Enter' && (event.isComposing || composing || event.keyCode === 229)) event.preventDefault(); });
$('clue-form').onsubmit = async event => {
  event.preventDefault(); if (composing || !connected) return;
  const message = validateClue($('clue').value);
  if (message) { $('result').textContent = message; $('result').className = 'error'; return; }
  if (transport instanceof TutorialTransport && transport.done) return;
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

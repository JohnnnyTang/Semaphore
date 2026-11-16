async (page) => {
  // Run only against a disposable W4 installation with an accepted short artifact.
  // No route interception: every account/game/receipt/result response is the service's.
  const assert = (condition, message) => { if (!condition) throw new Error(message); };
  const launch = new URL(page.url());
  const origin = launch.origin;
  const phase = launch.searchParams.get('w4') || 'complete';
  assert(['complete', 'restart-prepare', 'restart-verify'].includes(phase), 'known W4 phase');
  const evidenceKey = 'semaphore-w4-restart-evidence';
  const read = async path => {
    const response = await page.request.get(`${origin}/api/v1${path}`);
    assert(response.ok(), `real service GET failed: ${path} (${response.status()})`);
    return response.json();
  };
  if (phase === 'restart-verify') {
    const saved = await page.evaluate(key => sessionStorage.getItem(key), evidenceKey);
    assert(saved, 'restart-prepare must complete in this tab first');
    const expected = JSON.parse(saved);
    assert(expected.origin === origin, 'restart origin must match');
    await page.goto(`${origin}/web/durable.html`);
    await page.getByRole('heading', { name: 'W4 automated player', exact: true }).waitFor();
    const snapshot = (await read(`/games/${expected.game_id}`)).snapshot;
    assert(snapshot.status === 'over' && snapshot.score === expected.score && snapshot.end_reason === expected.end_reason,
      'terminal snapshot survives restart boundary');
    const receipt = (await read(`/games/${expected.game_id}/receipts/${encodeURIComponent(expected.command_id)}`)).receipt;
    assert(JSON.stringify(receipt) === JSON.stringify(expected.receipt), 'original final receipt survives restart boundary');
    const history = await read('/history');
    const result = history.items.find(item => item.game_id === expected.game_id);
    assert(result?.competitive && result.score === expected.score && result.completed_at === expected.completed_at &&
      JSON.stringify(result.cohort) === JSON.stringify(expected.cohort), 'durable history unchanged');
    const board = await read(`/boards/${encodeURIComponent(expected.artifact_id)}`);
    const scores = board.items.filter(item => item.game_id === expected.game_id);
    assert(scores.length === 1 && scores[0].score === expected.score, 'exact board contains one unchanged result');
    await page.getByRole('button', { name: 'Sign out', exact: true }).click();
    await page.getByRole('heading', { name: 'Sign in to play', exact: true }).waitFor();
    assert(await page.locator('#results li').count() === 0, 'logout clears private history');
    await page.evaluate(key => sessionStorage.removeItem(key), evidenceKey);
    return { kind: 'automated-restart-result-retrieval', game_id: expected.game_id,
      artifact_id: expected.artifact_id, score: expected.score, receipt_outcome: receipt.outcome,
      retrieval_verified: true, external_process_restart_evidence_required: true, human_acceptance: false };
  }
  const token = await page.evaluate(() => [...crypto.getRandomValues(new Uint8Array(12))].map(n => n.toString(16).padStart(2, '0')).join(''));
  const login = `w4_${token}`;
  const password = `W4 disposable ${token}`;
  await page.goto(`${origin}/web/durable.html`);
  await page.getByRole('button', { name: 'Create account', exact: true }).waitFor();
  await page.getByLabel('Login name').fill(login);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByLabel('Display name (new accounts)').fill('W4 automated player');
  await page.getByRole('button', { name: 'Create account', exact: true }).click();
  await page.getByRole('heading', { name: 'W4 automated player', exact: true }).waitFor();
  await page.waitForFunction(() => document.getElementById('packs').options.length > 0);
  if (launch.searchParams.has('artifact')) await page.locator('#packs').selectOption(launch.searchParams.get('artifact'));
  await page.getByLabel('I understand that my clues are saved privately.').check();
  const creation = page.waitForResponse(response => new URL(response.url()).pathname === '/api/v1/games' && response.request().method() === 'POST');
  await page.getByRole('button', { name: 'Start round', exact: true }).click();
  const creationResponse = await creation;
  assert(creationResponse.status() === 201, 'real game creation committed');
  const created = await creationResponse.json();
  assert(created.snapshot.status === 'active', 'real game created');
  const gameId = created.snapshot.game_id;
  await page.locator('#words .zone').first().waitFor();
  const zoneRanks = await page.locator('#words .zone').allTextContents();
  assert(zoneRanks.length === Math.min(created.snapshot.zone_size, created.snapshot.board.length) && zoneRanks.every((label, index) => label.startsWith(`${index + 1}.`)), 'authoritative clear-zone ranks');
  const submitted = page.waitForResponse(response => response.url().endsWith(`/games/${gameId}/commands`));
  await page.getByLabel('Your clue', { exact: true }).fill('association');
  await page.getByRole('button', { name: 'Send clue', exact: true }).click();
  const admissionResponse = await submitted;
  assert(admissionResponse.ok(), 'command admitted by real service');
  const admission = await admissionResponse.json();
  let receipt = admission.receipt;
  for (let i = 0; receipt.outcome === 'pending' && i < 40; i++) {
    await page.waitForTimeout(250);
    const response = await page.request.get(`${origin}/api/v1/games/${gameId}/receipts/${encodeURIComponent(receipt.command_id)}`);
    assert(response.ok(), 'owner can read admitted receipt');
    receipt = (await response.json()).receipt;
  }
  assert(['clear', 'miss'].includes(receipt.outcome), `clue ranked successfully: ${receipt.outcome}`);
  // This short acceptance artifact must naturally end within 60 seconds.
  await page.waitForFunction(() => document.getElementById('target').textContent.startsWith('Round complete:'), null, { timeout: 60000 });
  await page.getByRole('button', { name: 'Refresh results', exact: true }).click();
  await page.waitForFunction(() => document.querySelector('#results li')?.textContent.includes('points'));
  const history = await read('/history');
  const result = history.items.find(item => item.game_id === gameId);
  assert(result?.competitive, 'natural terminal result recorded');
  const artifact = await page.locator('#packs').inputValue();
  await page.getByRole('button', { name: 'Show board', exact: true }).click();
  const board = await read(`/boards/${encodeURIComponent(artifact)}`);
  assert(board.items.some(item => item.game_id === gameId && item.score === result.score), 'exact board agrees with private result');
  await page.reload();
  await page.getByRole('heading', { name: 'W4 automated player', exact: true }).waitFor();
  await page.waitForFunction(() => document.querySelector('#results li')?.textContent.includes('points'));
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.setViewportSize({ width: 320, height: 740 });
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), '320px layout');
  if (phase === 'restart-prepare') {
    await page.evaluate(({ key, evidence }) => sessionStorage.setItem(key, JSON.stringify(evidence)), {
      key: evidenceKey, evidence: { origin, game_id: gameId, artifact_id: artifact,
        command_id: receipt.command_id, receipt, score: result.score, end_reason: result.end_reason,
        completed_at: result.completed_at, cohort: result.cohort } });
    return { kind: 'automated-restart-prepared', game_id: gameId, artifact_id: artifact,
      score: result.score, receipt_outcome: receipt.outcome,
      next: 'Restart the actual host process, retain this browser tab, then invoke restart-verify.',
      human_acceptance: false, server_restart_tested: false };
  }
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await page.getByRole('heading', { name: 'Sign in to play', exact: true }).waitFor();
  assert(await page.locator('#results li').count() === 0, 'logout clears private history');
  return { kind: 'automated-real-service-browser', game_id: gameId,
    artifact_id: artifact, receipt_outcome: receipt.outcome, score: result.score,
    human_acceptance: false, server_restart_tested: false };
}

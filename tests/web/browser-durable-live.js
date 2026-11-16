async (page) => {
  // Run only against a disposable W4 installation with an accepted short artifact.
  // No route interception: every account/game/receipt/result response is the service's.
  const assert = (condition, message) => { if (!condition) throw new Error(message); };
  const origin = new URL(page.url()).origin;
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
  await page.getByLabel('I understand that my clues are saved privately.').check();
  const creation = page.waitForResponse(response => new URL(response.url()).pathname === '/api/v1/games' && response.request().method() === 'POST');
  await page.getByRole('button', { name: 'Start round', exact: true }).click();
  const created = await (await creation).json();
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
  assert(receipt.outcome !== 'pending', 'receipt settled');
  // This short acceptance artifact must naturally end within 60 seconds.
  await page.waitForFunction(() => document.getElementById('target').textContent.startsWith('Round complete:'), null, { timeout: 60000 });
  await page.getByRole('button', { name: 'Refresh results', exact: true }).click();
  await page.waitForFunction(() => document.querySelector('#results li')?.textContent.includes('points'));
  const history = await (await page.request.get(`${origin}/api/v1/history`)).json();
  const result = history.items.find(item => item.game_id === gameId);
  assert(result?.competitive, 'natural terminal result recorded');
  const artifact = await page.locator('#packs').inputValue();
  await page.getByRole('button', { name: 'Show board', exact: true }).click();
  const board = await (await page.request.get(`${origin}/api/v1/boards/${encodeURIComponent(artifact)}`)).json();
  assert(board.items.some(item => item.game_id === gameId && item.score === result.score), 'exact board agrees with private result');
  await page.reload();
  await page.getByRole('heading', { name: 'W4 automated player', exact: true }).waitFor();
  await page.waitForFunction(() => document.querySelector('#results li')?.textContent.includes('points'));
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.setViewportSize({ width: 320, height: 740 });
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), '320px layout');
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await page.getByRole('heading', { name: 'Sign in to play', exact: true }).waitFor();
  assert(await page.locator('#results li').count() === 0, 'logout clears private history');
  console.log(JSON.stringify({ kind: 'automated-real-service-browser', game_id: gameId,
    artifact_id: artifact, receipt_outcome: receipt.outcome, score: result.score,
    human_acceptance: false, server_restart_tested: false }));
}

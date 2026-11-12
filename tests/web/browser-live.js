async (page) => {
  const check = (ok, message) => { if (!ok) throw new Error(message); };
  const origin = new URL(page.url()).origin;
  const games = origin + '/experiment/v1/games';
  const input = page.getByRole('textbox', { name: 'Your clue' });
  const play = page.getByRole('button', { name: 'Play', exact: true });
  const begin = page.getByRole('button', { name: 'Start game', exact: true });
  const result = page.locator('#result');
  const score = () => page.locator('#score').textContent();
  const send = async clue => {
    await input.fill(clue);
    await input.press('Enter');
  };
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.unrouteAll();
  await page.goto(origin + '/web/?transport=http');
  await page.evaluate(() => sessionStorage.removeItem('semaphore-game'));
  await page.reload();

  let creates = 0;
  let game;
  await page.route(games, async route => {
    if (route.request().method() !== 'POST') return route.continue();
    if (++creates === 1) return route.abort('failed');
    const response = await route.fetch();
    const { snapshot } = await response.json();
    game = snapshot;
    await route.fulfill({ response });
  });

  await play.click();
  await input.waitFor();
  await send('planet');
  check(await page.locator('#target').textContent() === 'moon', 'Incorrect example leaves the target unchanged');
  await page.waitForTimeout(5100);
  check(creates === 0 && await page.locator('#target').textContent() === 'moon', 'Warm-up waits through a normal arrival interval');
  for (const clue of ['orbit', 'ocean', 'forest']) await send(clue);
  await begin.waitFor();
  check(creates === 0, 'Completed warm-up still waits for Start game');
  await begin.click();
  await page.locator('#begin-error').filter({ hasText: 'The game could not start' }).waitFor();
  check(await begin.isEnabled(), 'Start game can retry from the completed warm-up');
  await begin.click();
  await page.locator('#source').filter({ hasText: 'Casual / LAN game' }).waitFor();
  check(creates === 2 && game.score === 0 && await score() === '0', 'Fresh server game starts at zero');

  const commands = games + '/' + game.game_id + '/commands';
  const gameURL = games + '/' + game.game_id;
  await send('orange');
  await result.filter({ hasText: 'without the target word' }).waitFor();
  check(await input.inputValue() === 'orange' && await score() === '0', 'Illegal clue preserves draft and score');
  await page.locator('#occupancy').filter({ hasText: '8 of 20 words' }).waitFor({ timeout: 15000 });

  // Forward the first legal POST to the real HTTP server, then lose its response.
  let command;
  let posts = 0;
  await page.route(commands, async route => {
    if (posts++ > 0) {
      check(route.request().postData() === command.raw, 'Retry preserved the exact original command');
      return route.continue();
    }
    const raw = route.request().postData();
    command = { raw, id: JSON.parse(raw).command_id };
    const response = await route.fetch();
    check(response.ok(), 'Server accepted the command before response loss');
    await route.abort('failed');
  });
  const observedReceipt = page.waitForResponse(response =>
    command && response.url() === gameURL + '/receipts/' + command.id && response.ok());
  await send('vitamin C juice');
  await observedReceipt;
  await result.filter({ hasText: '+100' }).waitFor();
  check(await score() === '100' && await input.inputValue() === '', 'Lost response reconciles one clear');
  await page.unroute(commands);

  await input.fill('draft across reload');
  await page.reload();
  await input.waitFor();
  check(await input.inputValue() === 'draft across reload' && await score() === '100', 'Reload retains draft and score');
  check(await page.evaluate(() => JSON.parse(sessionStorage.getItem('semaphore-game')).snapshot.game_id) === game.game_id,
    'Reload retains the same server game');

  const ranks = [];
  for (const [index, clue] of ['sour yellow citrus', 'toast for breakfast', 'mashed side dish', 'red pasta sauce'].entries()) {
    const terminalReceipt = page.waitForResponse(async response => {
      if (!response.ok() || !response.url().startsWith(gameURL + '/receipts/')) return false;
      const { receipt } = await response.json();
      return receipt && receipt.outcome !== 'pending';
    });
    await send(clue);
    const { receipt } = await (await terminalReceipt).json();
    check(receipt.outcome === 'clear', 'Expected authored clue to clear; observed ' + receipt.outcome);
    ranks.push(receipt.target_rank);
    if (index < 3) {
      await page.locator('#streak').filter({ hasText: (index + 2) + ' / 5' }).waitFor();
    } else {
      await result.filter({ hasText: 'Five in a row! Zone sweep' }).waitFor();
      check(receipt.strike && receipt.clear_waves.length > 1, 'Fifth clear sweeps and cascades');
      check((await result.textContent()).includes('cascade'), 'Cascade feedback is visible');
    }
  }
  await page.locator('#end-title').waitFor({ timeout: 120000 });
  const { snapshot: ending } = await (await page.request.get(gameURL)).json();
  check(ending.status === 'over' && await score() === String(ending.score), 'Final score matches the server snapshot');
  check((await page.locator('#end-detail').textContent()).startsWith(ending.score + ' points. ' + ending.clears + ' words cleared.'),
    'Final count includes every word removed by the server');
  check(await page.locator('#end-title').evaluate(el => el === document.activeElement), 'End heading receives focus');

  await page.getByRole('button', { name: 'Leave game' }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.getByLabel('Skip guided warm-up').check();
  await play.click();
  await page.locator('#source').filter({ hasText: 'Casual / LAN game' }).waitFor();
  check(creates === 3 && await page.locator('#instruction').isHidden(), 'Skip starts a fresh server game directly');
  check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Mobile width has no horizontal overflow');
  await send('vitamin C juice');
  await result.filter({ hasText: '+100' }).waitFor();
  check(await page.locator('#words').evaluate(el => el.getAnimations({ subtree: true }).length) === 0 &&
    await page.locator('.clear-echo').count() === 0, 'Reduced motion preserves clear feedback without motion');
  await page.getByRole('button', { name: 'Leave game' }).click();
  check(errors.length === 0, errors.join('\n'));
  return { score: ending.score, clears: ending.clears, endReason: ending.end_reason, elapsedMs: ending.elapsed_ms,
    modelFingerprint: ending.identities.model_fingerprint, ranksAfterFirstClear: ranks, lostResponsePostAttempts: posts };
}

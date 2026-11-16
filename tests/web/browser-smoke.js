async (page) => {
  const assert = (value, message) => { if (!value) throw new Error(message); };
  await page.goto(new URL('/web/', page.url()).href);
  await page.evaluate(() => { sessionStorage.clear(); document.documentElement.style.zoom = ''; });
  await page.reload();
  const evidence = await (await page.request.get(new URL('/fixtures/protocol/bottom-three-target-only.json',page.url()).href)).json();
  let frame, longLabels = false;
  await page.unrouteAll();
  await page.route('**/experiment/v1/games**', async route => {
    if (route.request().method() === 'POST' && route.request().url().endsWith('/games')) {
      frame = structuredClone(evidence.envelopes[0]);
      if (longLabels) for (const entry of Object.values(frame.snapshot.entries)) entry.label = 'W'.repeat(64);
    } else if (route.request().method() === 'POST' && route.request().url().endsWith('/commands')) {
      frame = structuredClone(evidence.envelopes.at(-1));
      frame.receipt.command_id = route.request().postDataJSON().command_id;
      frame.snapshot.status = 'over'; frame.snapshot.end_reason = 'pack_cleared';
    }
    await route.fulfill({json:frame});
  });
  await page.getByLabel('Skip guided warm-up').check();
  await page.getByRole('button', {name: 'Play', exact: true}).focus();
  await page.keyboard.press('Enter');
  const input = page.getByRole('textbox', {name: 'Your clue'});
  await input.waitFor();
  assert(await input.evaluate(el => el === document.activeElement), 'Play must focus clue');
  await input.fill('ice');
  await input.dispatchEvent('compositionstart');
  await input.dispatchEvent('keydown', { key: 'Enter', isComposing: true });
  await input.evaluate(el => el.form.requestSubmit());
  assert(await page.locator('#score').textContent() === '0', 'IME must not submit');
  await input.dispatchEvent('compositionend');
  await page.keyboard.press('Enter');
  await page.getByRole('heading', { name: 'Pack complete' }).waitFor();
  assert(await page.locator('#score').textContent() === '100', 'Frozen clear score');
  assert(await page.locator('#end-title').evaluate(el => el === document.activeElement), 'Ending focus');
  await page.getByRole('button', { name: 'Play again' }).press('Enter');
  await input.waitFor();
  assert(await page.locator('#score').textContent() === '0', 'Retry creates a fresh game');
  await page.getByRole('button', {name: 'How to play'}).click();
  await page.keyboard.press('Escape');
  assert(!(await page.locator('#help').evaluate(el => el.open)), 'Escape closes help');
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.setViewportSize({width: 320, height: 780});
  longLabels = true;
  await page.getByRole('button', {name: 'Leave game'}).click();
  await page.getByRole('button', {name: 'Play', exact: true}).click();
  await input.waitFor();
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), '320px no horizontal overflow');
  await page.screenshot({path:'output/playwright/qa-long-labels.png', fullPage:true});
  await page.setViewportSize({width: 1280, height: 900});
  await page.evaluate(() => { document.documentElement.style.zoom = '2'; });
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), '200% zoom no horizontal overflow');
  await page.screenshot({path:'output/playwright/qa-zoom.png', fullPage:true});
  await page.evaluate(() => { document.documentElement.style.zoom = ''; });
  await page.getByRole('button', {name: 'Leave game'}).click();
  await page.unrouteAll();
  console.log('PASS: keyboard start/submit/retry/help, IME, authoritative score, final focus, reduced-motion, 320px 64-codepoint labels, 200% zoom');
}

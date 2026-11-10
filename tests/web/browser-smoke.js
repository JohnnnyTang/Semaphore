async (page) => {
  const assert = (value, message) => { if (!value) throw new Error(message); };
  await page.goto('http://127.0.0.1:18737/web/');
  await page.getByRole('combobox', {name: 'Practice sequence'}).selectOption('bottom-three-target-only');
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
  await page.getByRole('heading', { name: 'Practice sequence complete' }).waitFor();
  assert(await page.locator('#score').textContent() === '100', 'Frozen clear score');
  assert(await page.locator('#end-title').evaluate(el => el === document.activeElement), 'Ending focus');
  await page.getByRole('button', { name: 'Play again' }).press('Enter');
  await input.waitFor();
  assert(await page.locator('#score').textContent() === '0', 'Retry creates fresh fixture');
  await page.getByRole('button', {name: 'How to play'}).click();
  await page.keyboard.press('Escape');
  assert(!(await page.locator('#help').evaluate(el => el.open)), 'Escape closes help');
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.setViewportSize({width: 320, height: 780});
  // Mutate only display fixture labels through its network payload, never engine state.
  await page.route('**/fixtures/protocol/bottom-three-target-only.json', async route => {
    const response = await route.fetch(); const data = await response.json();
    for (const frame of data.envelopes) for (const entry of Object.values(frame.snapshot.entries)) entry.label = 'W'.repeat(64);
    await route.fulfill({ response, json: data });
  });
  await page.getByRole('button', {name: 'Leave game'}).click();
  await page.getByRole('button', {name: 'Play', exact: true}).click();
  await input.waitFor();
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), '320px no horizontal overflow');
  await page.screenshot({path:'web/qa-long-labels.png', fullPage:true});
  await page.setViewportSize({width: 1280, height: 900});
  await page.evaluate(() => { document.documentElement.style.zoom = '2'; });
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), '200% zoom no horizontal overflow');
  await page.screenshot({path:'web/qa-zoom.png', fullPage:true});
  console.log('PASS: keyboard start/submit/retry/help, IME, authoritative score, final focus, reduced-motion, 320px 64-codepoint labels, 200% zoom');
}

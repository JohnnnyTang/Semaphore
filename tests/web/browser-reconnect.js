async (page) => {
  const assert = (value, message) => { if (!value) throw new Error(message); };
  await page.unrouteAll();
  await page.emulateMedia({reducedMotion:'no-preference'});
  await page.setViewportSize({width:1280,height:900});
  await page.goto(new URL('/web/?transport=http', page.url()).href);
  await page.evaluate(() => sessionStorage.removeItem('semaphore-game'));
  await page.reload();
  const response = await page.request.get(new URL('/fixtures/protocol/bottom-three-target-only.json', page.url()).href);
  const {envelopes} = await response.json();
  const initial = envelopes[0], pending = envelopes[1], clear = envelopes[2];
  let command, posts = [], completed = false, receiptPolls = 0;
  function frame(source) {
    const value = structuredClone(source);
    if (value.receipt) value.receipt.command_id = command.command_id;
    if (value.snapshot.pending) value.snapshot.pending.command_id = command.command_id;
    return value;
  }
  await page.route('**/experiment/v1/games**', async route => {
    const request = route.request(), url = request.url();
    const json = async value => route.fulfill({ status:200, contentType:'application/json', json:value });
    if (url.endsWith('/commands')) {
      posts.push(request.postData()); command = request.postDataJSON();
      if (posts.length === 1) return route.abort('failed');
      return json(frame(pending));
    }
    if (url.includes('/receipts/')) {
      if (posts.length < 2) return route.fulfill({status:404,json:{code:'receipt_not_found',message:'Unknown'}});
      if (++receiptPolls > 1) completed = true;
      return json(frame(completed ? clear : pending));
    }
    if (request.method() === 'POST') return json(initial);
    return json(command && posts.length > 1 ? frame(completed ? clear : pending) : initial);
  });
  await page.getByLabel('Skip guided warm-up').check();
  await page.getByRole('button',{name:'Play',exact:true}).click();
  const input = page.getByRole('textbox',{name:'Your clue'});
  await input.fill('Ice'); await input.press('Enter');
  await page.waitForFunction(() => document.querySelector('#score').textContent === '100');
  assert(posts.length === 2 && posts[0] === posts[1], 'Uncertain POST must retry exact original payload');
  assert(await input.inputValue() === '', 'Resolved clear clears draft');
  assert(!(await input.evaluate(el => el.readOnly)), 'Resolved input unlocks');
  await input.fill('kept across reload'); await page.reload();
  await input.waitFor();
  assert(await input.inputValue() === 'kept across reload', 'Reload preserves tab draft');
  assert(await page.locator('#score').textContent() === '100', 'Reload reconciles authoritative score');
  await page.screenshot({path:'output/playwright/qa-reconnected.png',fullPage:true});
  console.log('PASS: lost POST, receipt lookup 404, exact-payload retry, pending polling, receipt resolution, reload same game/draft/score');
  await page.getByRole('button', { name: 'Leave game' }).click();
}

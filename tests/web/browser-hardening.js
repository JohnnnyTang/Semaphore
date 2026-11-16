async (page) => {
  const check = (ok, message) => { if (!ok) throw new Error(message); };
  await page.unrouteAll();
  await page.goto(new URL('/web/',page.url()).href);
  await page.evaluate(()=>sessionStorage.clear());
  await page.reload();
  const frame = await page.evaluate(async()=> (await (await fetch('/web/practice/spacious-arcade.json')).json()).envelopes[0]);
  let releasePoll, releaseQuit, pollStarted = false, quitStarted = false;
  const heldPoll = new Promise(resolve=>releasePoll=resolve);
  const heldQuit = new Promise(resolve=>releaseQuit=resolve);
  await page.route('**/experiment/v1/games**', async route => {
    if (route.request().method()==='GET') {
      pollStarted=true; await heldPoll; await route.abort();
    } else if (route.request().url().endsWith('/quit')) {
      quitStarted=true; await heldQuit; await route.fulfill({json:frame});
    } else await route.fulfill({status:201,json:frame});
  });
  await page.getByLabel('Skip guided warm-up').check();
  await page.getByRole('button',{name:'Play',exact:true}).click();
  await page.waitForTimeout(400);
  check(pollStarted,'Snapshot request is held');
  await page.getByRole('button',{name:'Leave game'}).click();
  await page.locator('#welcome').waitFor({state:'visible',timeout:1000});
  check(quitStarted,'Quit sent without blocking local navigation');
  await page.getByLabel('Skip guided warm-up').uncheck();
  await page.getByRole('button',{name:'Play',exact:true}).click();
  releasePoll(); releaseQuit();
  await page.waitForTimeout(500);
  check(await page.locator('#source').textContent()==='Guided warm-up / clock paused','New session survives late quit');
  check(await page.locator('#connection').textContent()==='','Old poll failure cannot disconnect new session');
  check(await page.locator('#send').isEnabled(),'New session stays playable');
  await page.getByRole('button',{name:'Leave game'}).click();
  await page.unrouteAll();
  for (const width of [320,390,768,1280]) {
    await page.setViewportSize({width,height:900});
    check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Welcome fits ${width}px`);
  }
  await page.getByRole('button',{name:'How to play'}).click();
  check(await page.getByRole('dialog',{name:'Follow the flag'}).isVisible(),'Named help dialog opens');
  await page.keyboard.press('Escape');
  check(await page.locator('#help-open').evaluate(el=>el===document.activeElement),'Help restores keyboard focus');
  return 'PASS: immediate leave, late quit/poll isolation, 320–1280px welcome, accessible help';
}

async (page) => {
  const check = (ok, message) => { if (!ok) throw new Error(message); };
  await page.unrouteAll();
  await page.goto(new URL('/web/', page.url()).href);
  await page.evaluate(() => sessionStorage.removeItem('semaphore-game'));
  await page.reload();
  // Recorded envelopes are test inputs behind HTTP interception, never a player mode.
  const fixture = await (await page.request.get(new URL('/web/practice/spacious-arcade.json',page.url()).href)).json();
  let frame, position;
  await page.route('**/experiment/v1/games**', async route => {
    const request = route.request();
    if (request.method() === 'POST' && request.url().endsWith('/games')) {
      position = 0; frame = structuredClone(fixture.envelopes[0]);
    } else if (request.method() === 'POST' && request.url().endsWith('/commands')) {
      do { position++; } while (position < fixture.envelopes.length && (!fixture.envelopes[position].receipt || fixture.envelopes[position].receipt.outcome === 'pending'));
      frame = structuredClone(fixture.envelopes[position]);
      frame.receipt.command_id = request.postDataJSON().command_id;
    }
    await route.fulfill({json:frame});
  });
  const errors=[]; page.on('pageerror', error => errors.push(error.message));
  let creates=0; page.on('request', req => {if(req.url().endsWith('/experiment/v1/games')) creates++;});
  await page.getByRole('button',{name:'Play',exact:true}).click();
  await page.getByRole('textbox',{name:'Your clue'}).waitFor();
  const initial = await page.locator('#words').textContent();
  await page.waitForTimeout(5500);
  check(await page.locator('#words').textContent() === initial,'Tutorial does not spawn during idle wait');
  check(creates===0,'No server game starts during tutorial');
  await page.locator('#clue').fill('orbit');
  await page.waitForTimeout(600);
  check((await page.locator('#instruction').textContent()).includes('Press Enter'),'Typing note stays visible across tutorial polls');
  await page.locator('#clue').press('Enter');
  await page.getByRole('heading',{name:'wave',exact:true}).waitFor();
  for (const clue of ['ocean','forest']) {await page.locator('#clue').fill(clue); await page.locator('#clue').press('Enter');}
  await page.getByRole('button',{name:'Start game',exact:true}).waitFor();
  check(creates===0,'Completion still waits for player readiness');
  await page.screenshot({path:'output/playwright/tutorial-ready.png',fullPage:true});
  await page.getByRole('button',{name:'Leave game'}).click();
  await page.getByRole('button',{name:'Play',exact:true}).click();
  for (const clue of ['orbit','ocean','forest']) {await page.locator('#clue').fill(clue); await page.locator('#clue').press('Enter');}
  await page.getByRole('button',{name:'Start game',exact:true}).click();
  await page.waitForFunction(() => document.querySelector('#source').textContent.includes('LAN game'));
  check(await page.locator('#instruction').isHidden(),'Normal play removes instructional note');
  for(let n=0;n<5;n++) {
    await page.locator('#clue').fill('a recorded association'); await page.locator('#clue').press('Enter');
    await page.waitForFunction(() => !document.querySelector('#clue').readOnly);
  }
  check((await page.locator('#result').textContent()).includes('Five in a row'),'Fifth clue announces sweep');
  await page.screenshot({path:'output/playwright/strike-clear.png',fullPage:true});
  await page.getByRole('button',{name:'Leave game'}).click();
  await page.getByLabel('Skip guided warm-up').check();
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.getByRole('button',{name:'Play',exact:true}).click();
  await page.waitForFunction(() => document.querySelector('#source').textContent.includes('LAN game'));
  check(await page.locator('#instruction').isHidden(),'Skip bypasses tutorial');
  check(await page.locator('#words').evaluate(el=>el.getAnimations({subtree:true}).length===0),'Reduced motion skips falling animations');
  await page.locator('#clue').fill('association'); await page.locator('#clue').press('Enter');
  await page.waitForFunction(() => !document.querySelector('#clue').readOnly);
  check(await page.locator('.clear-echo').count()===0,'Reduced motion skips clear trails');
  await page.setViewportSize({width:390,height:844});
  check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Mobile fits viewport');
  await page.screenshot({path:'output/playwright/refine2-mobile.png',fullPage:true});
  check(errors.length===0,errors.join('\n'));
  return 'PASS: tutorial idle pause, typing notes, guided progress, no server clock, transition, skip, fifth-clear sweep, reduced motion, mobile, no page errors';
}

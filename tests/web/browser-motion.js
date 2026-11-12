async (page) => {
  const check = (ok, message) => { if (!ok) throw new Error(message); };
  const origin = new URL(page.url()).origin;
  await page.unrouteAll();
  const fixture = await (await page.request.get(origin + '/web/practice/spacious-arcade.json')).json();
  const envelope = structuredClone(fixture.envelopes[0]);
  await page.route('**/experiment/v1/games**', route => route.fulfill({json: envelope}));
  await page.goto(origin + '/web/?transport=http');
  await page.evaluate(() => sessionStorage.clear());
  await page.reload();
  await page.emulateMedia({reducedMotion:'no-preference'});
  await page.setViewportSize({width:1920,height:1080});
  await page.getByLabel('Skip guided warm-up').check();
  await page.getByRole('button',{name:'Play',exact:true}).click();
  await page.locator('#words .word').first().waitFor();
  await page.waitForTimeout(1700);
  await page.evaluate(() => {
    window.settled = [...document.querySelectorAll('#words .word')].map(row => ({row, label:row.querySelector('.label'), y:row.getBoundingClientRect().top}));
  });
  envelope.snapshot.board.push('word-06'); envelope.snapshot.revision++;
  await page.waitForFunction(() => document.querySelectorAll('#words .word').length === 7);
  const first = await page.evaluate(() => {
    const row = document.querySelector('#words .word');
    window.arrival = row.getAnimations()[0];
    return {y:row.getBoundingClientRect().top, rest:row.offsetTop + document.querySelector('.stack').getBoundingClientRect().top,
      opacity:getComputedStyle(row).opacity, animation:!!window.arrival,
      stable:window.settled.every(({row,label,y}) => row.querySelector('.label') === label && Math.abs(row.getBoundingClientRect().top-y)<.5 && !row.getAnimations().length)};
  });
  check(first.animation && first.y < first.rest - 100 && first.opacity === '1', 'Arrival visibly falls from above, fully opaque');
  check(first.stable, 'Existing rows and labels remain attached, stationary, and unanimated');
  await page.waitForTimeout(250);
  const later = await page.locator('#words .word').first().boundingBox();
  check(later.y > first.y && later.y < first.rest, 'Arrival moves down through intermediate frames');
  envelope.snapshot.board.push('word-07'); envelope.snapshot.revision++;
  await page.waitForFunction(() => document.querySelectorAll('#words .word').length === 8);
  check(await page.evaluate(() => document.querySelectorAll('#words .word')[1].getAnimations()[0] === window.arrival), 'Rapid arrival preserves previous in-flight animation');
  check(await page.evaluate(() => window.settled.every(({row,y}) => Math.abs(row.getBoundingClientRect().top-y)<.5 && !row.getAnimations().length)), 'Bottom stack remains stationary across rapid arrivals');
  await page.waitForTimeout(1700);
  const sizes = [];
  for (const [width,height] of [[1920,1080],[2560,1440],[1280,900],[390,844],[320,780]]) {
    await page.setViewportSize({width,height});
    sizes.push(await page.locator('#words .word').first().evaluate(el => ({font:parseFloat(getComputedStyle(el).fontSize),height:el.offsetHeight})));
    check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'No horizontal overflow at '+width);
    await page.screenshot({path:`output/playwright/motion-${width}.png`,fullPage:true});
  }
  check(sizes[0].font >= 24 && sizes[0].height >= 35 && sizes[1].height >= 50, 'Large desktop rows scale up');
  await page.emulateMedia({reducedMotion:'reduce'});
  envelope.snapshot.board.push('word-08'); envelope.snapshot.revision++;
  await page.waitForFunction(() => document.querySelectorAll('#words .word').length === 9);
  check(await page.locator('#words').evaluate(el => !el.getAnimations({subtree:true}).length), 'Reduced motion skips falling animation');
  await page.getByRole('button',{name:'Leave game'}).click();
  await page.unrouteAll();
  return {result:'PASS: visible descent, stable settled rows, uninterrupted rapid arrivals, desktop scaling, mobile overflow, reduced motion', sizes};
}

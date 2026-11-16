async (page) => {
  const payloads = await (await page.request.get('http://127.0.0.1:18742/fixtures/durable/payloads.json')).json();
  const values = Object.fromEntries(payloads.cases.map(item=>[item.name,item.value]));
  const assert = (condition,message) => { if(!condition) throw new Error(message); };
  let signed = false, command = null, game = null;
  await page.route('**/api/v1/**', async route => {
    const path = new URL(route.request().url()).pathname.replace('/api/v1','');
    let body, status=200;
    if(path==='/config') body=values.config;
    else if(path==='/auth/session') {body=signed?values.session:values.unauthenticated; status=signed?200:401;}
    else if(path==='/auth/login') {signed=true;body=structuredClone(values.session);body.account.display_name='<img src=x onerror=alert(1)>';}
    else if(path==='/auth/logout') {signed=false; return route.fulfill({status:204});}
    else if(path==='/packs') body=values.packs;
    else if(path==='/history') body=values.history;
    else if(path.startsWith('/boards/')) body=values.board;
    else if(path==='/games') {game=structuredClone(values['envelope-snapshot']); body=game;}
    else if(path.endsWith('/commands')) {command=route.request().postDataJSON();game=structuredClone(values['envelope-pending']);game.receipt.command_id=command.command_id;game.snapshot.pending.command_id=command.command_id;body=game;status=202;}
    else if(path.includes('/receipts/')) {game=structuredClone(values['envelope-clear']);game.receipt.command_id=command.command_id;body=game;}
    else if(path.endsWith('/quit')) {game=structuredClone(values['envelope-terminal']);body=game;}
    else body=game;
    await route.fulfill({status,json:body});
  });
  await page.reload();
  await page.getByLabel('Login name').fill('fixture_player');
  await page.getByLabel('Password',{exact:true}).fill('not-a-real-secret');
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await page.getByRole('heading',{name:'<img src=x onerror=alert(1)>'}).waitFor();
  assert(await page.locator('#identity img').count()===0,'name escaped');
  await page.getByLabel('I understand that my clues are saved privately.').check();
  await page.getByRole('button',{name:'Start round',exact:true}).focus();await page.keyboard.press('Enter');
  await page.getByLabel('Your clue',{exact:true}).waitFor();
  await page.getByLabel('Your clue',{exact:true}).fill('ice');await page.keyboard.press('Enter');
  await page.waitForFunction(()=>document.getElementById('score').textContent.includes('100'));
  await page.getByRole('button',{name:'Show board'}).click();
  await page.getByText('Deleted player · 0 points',{exact:true}).waitFor();
  await page.emulateMedia({reducedMotion:'reduce'});await page.setViewportSize({width:320,height:740});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'mobile no overflow');
  await page.screenshot({path:'output/playwright/durable-mobile.png',fullPage:true});
  await page.setViewportSize({width:1280,height:900});
  await page.screenshot({path:'output/playwright/durable-desktop.png',fullPage:true});
  await page.getByRole('button',{name:'Sign out',exact:true}).click();
  await page.getByRole('heading',{name:'Sign in to play'}).waitFor();
  assert(await page.locator('#results li').count()===0,'private history cleared');
  console.log('PASS durable fixture sign in, escaped names, keyboard play, pending receipt, board, 320px, reduced motion, logout');
}

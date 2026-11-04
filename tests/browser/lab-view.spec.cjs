const {test,expect}=require('@playwright/test');
const {spawn}=require('node:child_process');
let child,url,stderr='';
test.beforeAll(async()=>{
 child=spawn(process.env.R2_PYTHON||'python',['-u','scripts/lab_view_test_server.py'],{env:{...process.env,PYTHONPATH:'.'},windowsHide:true,stdio:['pipe','pipe','pipe']});
 child.stderr.on('data',b=>stderr+=b);
 url=await new Promise((resolve,reject)=>{let s='';const t=setTimeout(()=>reject(Error('SERVER_TIMEOUT '+stderr)),10000);child.once('error',reject);child.once('exit',()=>{clearTimeout(t);reject(Error('SERVER_EXIT '+stderr))});child.stdout.on('data',b=>{s+=b;if(s.includes('\n')){clearTimeout(t);resolve(JSON.parse(s.split('\n')[0]).url)}})});
});
test.afterAll(async()=>{if(child&&child.exitCode===null){const done=new Promise(r=>child.once('exit',r));child.stdin.end('stop\n');await done}});
async function setSnapshot(command){
 let buffer='',timer;const applied=new Promise((resolve,reject)=>{
  const onData=b=>{buffer+=b;for(const line of buffer.split('\n').slice(0,-1)){const value=JSON.parse(line);if(value.applied===command){clearTimeout(timer);child.stdout.off('data',onData);resolve();return;}}};
  timer=setTimeout(()=>{child.stdout.off('data',onData);reject(Error('SNAPSHOT_APPLY_TIMEOUT'));},10000);
  child.stdout.on('data',onData);child.stdin.write(command+'\n');
 });await applied;
}
async function refresh(page){await page.evaluate(()=>refresh())}
test('SYNTHETIC_TEST_INPUT: quotes, XSS safety, freshness, timeout and recovery',async({page},info)=>{
 await page.goto(url+'/lab');await expect(page.locator('#state')).toHaveText('AVAILABLE');
 await expect(page.locator('section').first().locator('tr')).toHaveCount(11);
 await expect(page.locator('#meta')).toContainText('SYNTHETIC_TEST_INPUT');
 const payload='<img src=x onerror="window.labXss=true">';
 await page.route('**/api/lab/overview',async route=>{const r=await route.fetch();const d=await r.json();d.strategies[0].id=payload;await route.fulfill({response:r,json:d})});
 await refresh(page);await expect(page.locator('section').nth(2)).toContainText(payload);await expect(page.locator('section img')).toHaveCount(0);expect(await page.evaluate(()=>window.labXss)).toBeUndefined();await page.unroute('**/api/lab/overview');
 await setSnapshot('stale');await expect.poll(async()=>{await refresh(page);return page.locator('#state').textContent()}).toContain('STALE');
 await setSnapshot('fresh');await expect.poll(async()=>{await refresh(page);return page.locator('#state').textContent()}).toBe('AVAILABLE');
 await page.route('**/api/lab/overview',route=>route.abort());await refresh(page);await expect(page.locator('#state')).toContainText('UNAVAILABLE');await expect(page.locator('section')).toHaveCount(0);await page.unroute('**/api/lab/overview');
 await setSnapshot('fresh');await refresh(page);await expect(page.locator('#state')).toHaveText('AVAILABLE');
 let requests=0;await page.route('**/api/lab/overview',()=>{requests++});
 // A hung request cannot retain the previous available state, and repeated
 // refresh calls cannot create concurrent requests.
 await page.evaluate(()=>{refresh();refresh();refresh()});
 await expect(page.locator('#state')).toContainText('UNAVAILABLE',{timeout:4000});expect(requests).toBe(1);
 await page.unrouteAll({behavior:'ignoreErrors'});await setSnapshot('fresh');await refresh(page);await expect(page.locator('#state')).toHaveText('AVAILABLE');
 // Browser wall time freshness runs independently from network completion.
 await page.clock.install();await page.clock.setSystemTime(new Date(Date.now()+16000));await page.clock.runFor(600);await expect(page.locator('#state')).toContainText('STALE');
 await info.attach('synthetic-test-input-lab',{body:await page.screenshot({fullPage:true}),contentType:'image/png'});
});

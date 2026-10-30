const {test,expect}=require('@playwright/test');
const {spawn}=require('node:child_process');
let child,url,stderr=0;
test.beforeAll(async()=>{
 if(process.env.UNIFIED_URL){url=process.env.UNIFIED_URL;return;}
 child=spawn(process.env.R2_PYTHON||'python',['-m','terminan.unified_runner','--demo','--port','0'],{stdio:['pipe','pipe','pipe']});child.stderr.on('data',b=>stderr+=b.length);
 url=await new Promise((resolve,reject)=>{let out='';const t=setTimeout(()=>reject(Error('START_TIMEOUT')),15000);child.once('error',()=>{clearTimeout(t);reject(Error('START_FAILED'));});child.stdout.on('data',b=>{out+=b;if(out.includes('\n')){clearTimeout(t);resolve(JSON.parse(out.split('\n')[0]).url);}});});
});
test.afterAll(async()=>{if(!child)return;const exit=await new Promise(resolve=>{const t=setTimeout(()=>{child.kill();resolve('TIMEOUT');},15000);child.once('exit',c=>{clearTimeout(t);resolve(c);});child.stdin.end('\n');});expect(exit).toBe(0);expect(stderr).toBe(0);});
test('six workspaces preserve chart state and fail closed without engines',async({page},info)=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.name));await page.goto(url);
 const terminal=page.frameLocator('iframe[data-workspace="terminal"]');
 await expect(terminal.locator('body')).toHaveAttribute('data-loading','false');await expect(terminal.locator('#session-state')).toContainText('ACTIVE');
 const metric=()=>terminal.locator('body').evaluate(()=>window.r2.metrics());const initial=await metric();await terminal.locator('#zoom-in').click();await expect.poll(async()=>(await metric()).spanMs).toBeLessThan(initial.spanMs);const zoom=(await metric()).spanMs;expect((await metric()).bookRows).toBeLessThanOrEqual(100);const ladder=await terminal.locator('#book-body tr').evaluateAll(rows=>rows.map(r=>r.className));const split=ladder.findIndex(c=>c.includes('ladder-bid'));expect(split).toBeGreaterThan(0);expect(ladder.slice(0,split).every(c=>c.includes('ladder-ask'))).toBe(true);expect(ladder.slice(split).every(c=>c.includes('ladder-bid'))).toBe(true);
 const sz=await terminal.locator('#chart').evaluate(c=>({width:c.width,css:c.clientWidth,dpr:devicePixelRatio}));expect(Math.abs(sz.width-sz.css*sz.dpr)).toBeLessThanOrEqual(2);
 await page.locator('#workspaces a[href="/saved"]').click();const saved=page.frameLocator('iframe[data-workspace="saved"]');await expect(saved.locator('body')).toHaveAttribute('data-loading','false');await expect(saved.locator('#mode')).toContainText('SYNTHETIC FIXTURES');await expect(saved.locator('#saved-body tr')).toHaveCount(48);
 const span=await saved.locator('body').evaluate(()=>saved.metrics().span);await saved.locator('#zoom-in').click();await expect.poll(()=>saved.locator('body').evaluate(()=>window.saved.metrics().span)).toBeLessThan(span);const savedSpan=await saved.locator('body').evaluate(()=>window.saved.metrics().span);
 await saved.locator('#saved-seek').fill('3');await saved.locator('#saved-step').click();await expect(saved.locator('#saved-body tr')).toHaveCount(4);
 for(const route of ['/math','/history-overlay','/monitor','/cache']){await page.locator(`#workspaces a[href="${route}"]`).click();await expect(page.locator(`iframe[data-workspace="${route.slice(1)}"]`)).toBeVisible();}
 const monitor=page.frameLocator('iframe[data-workspace="monitor"]');await page.locator('#workspaces a[href="/monitor"]').click();await expect(monitor.locator('#status')).toContainText('UNAVAILABLE');
 await page.locator('#workspaces a[href="/cache"]').click();await expect(page.frameLocator('iframe[data-workspace="cache"]').locator('#state')).toContainText('DISABLED');
 const math=await page.request.get(url+'/api/math/health');const health=await math.json();expect(health.state).toBe('NOT_CONNECTED');expect(health.research_enabled).toBe(false);expect(health.trading_authorized).toBe(false);
 await page.locator('#workspaces a[href="/"]').click();expect((await metric()).spanMs).toBe(zoom);
 await page.setViewportSize({width:1100,height:900});await expect.poll(()=>terminal.locator('#chart').evaluate(c=>Math.abs(c.width-c.clientWidth*devicePixelRatio))).toBeLessThanOrEqual(2);
 await page.locator('#workspaces a[href="/saved"]').click();expect(await saved.locator('body').evaluate(()=>window.saved.metrics().span)).toBe(savedSpan);await expect(saved.locator('#saved-body tr')).toHaveCount(4);
 await saved.locator('#from-utc').fill('2026-01-01T00:46');await saved.locator('#from-utc').press('Tab');await expect(saved.locator('#saved-body tr')).toHaveCount(2);await saved.locator('#zoom-in').click();expect(await saved.locator('body').evaluate(()=>window.saved.metrics().span)).toBeLessThanOrEqual(2);expect(await saved.locator('body').evaluate(()=>window.saved.metrics().span)).toBeGreaterThanOrEqual(1);
 expect(await page.evaluate(()=>unified.count())).toBe(6);expect(errors).toEqual([]);
 await page.screenshot({path:info.outputPath('unified.png'),fullPage:true});
});

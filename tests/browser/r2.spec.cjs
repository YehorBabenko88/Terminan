const {test:base,expect}=require('@playwright/test');
const {spawn}=require('node:child_process');
const fs=require('node:fs');
const path=require('node:path');
const test=base.extend({
  labURL:[async({},use)=>{
    const child=spawn(process.env.R2_PYTHON||'python',['-m','terminan.r2_runner'],{stdio:['pipe','pipe','pipe']});
    let info;
    try {
      info=await new Promise((resolve,reject)=>{
        const timeout=setTimeout(()=>reject(Error('R2 startup timeout')),15000);
        let line='';
        child.once('error',()=>{clearTimeout(timeout);reject(Error('R2 child unavailable'));});
        child.stdout.on('data',data=>{line+=data.toString();if(line.includes('\n')){clearTimeout(timeout);resolve(JSON.parse(line.split('\n')[0]));}});
        child.once('exit',()=>{clearTimeout(timeout);reject(Error('R2 child exited before readiness'));});
      });
      await use('http://127.0.0.1:'+info.port);
    } finally {
      if(child.exitCode===null){
        const exited=new Promise(resolve=>child.once('exit',resolve));
        child.stdin.end('quit\n');
        const timer=setTimeout(()=>child.kill(),10000);
        await exited;clearTimeout(timer);
      }
    }
  },{scope:'worker'}]
});
async function ready(page,url){
  await page.goto(url);
  await expect(page.locator('body')).toHaveAttribute('data-loading','false');
  await expect(page.locator('#mode')).toHaveText('SYNTHETIC · OFFLINE');
}
async function seek(page,step){
  await page.evaluate(step=>window.r2.seek(step),step);
  await expect(page.locator('body')).toHaveAttribute('data-step',String(step));
}
test('zoom pan resize DPR and complete synthetic identity',async({page,labURL},info)=>{
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await ready(page,labURL);
  const first=await page.evaluate(()=>window.r2.metrics());
  const size=await page.locator('#chart').evaluate(c=>({w:c.width,css:c.clientWidth,dpr:devicePixelRatio}));
  expect(Math.abs(size.w-size.css*size.dpr)).toBeLessThanOrEqual(2);
  await page.locator('#zoom-in').click();
  await expect.poll(()=>page.evaluate(()=>window.r2.metrics().spanMs)).toBeLessThan(first.spanMs);
  const box=await page.locator('#chart').boundingBox();
  await page.mouse.move(box.x+box.width*.4,box.y+100);
  await expect(page.locator('#chart-inspect')).toContainText('O ');
  const before=await page.evaluate(()=>window.r2.metrics().windowEnd);
  await page.mouse.move(box.x+box.width*.7,box.y+100);await page.mouse.down();
  await page.mouse.move(box.x+box.width*.85,box.y+100);await page.mouse.up();
  await expect.poll(()=>page.evaluate(()=>window.r2.metrics().windowEnd)).not.toBe(before);
  await page.locator('#reset-view').click();
  await page.setViewportSize({width:960,height:1100});
  await expect.poll(()=>page.locator('#chart').evaluate(c=>c.width)).toBeLessThan(size.w);
  await page.screenshot({path:info.outputPath('synthetic-preview.png'),fullPage:true});
  await page.selectOption('#symbol','ETHUSDT');await page.selectOption('#timeframe','5m');
  await expect(page.locator('body')).toHaveAttribute('data-identity','ETHUSDT|5m');
  await expect(page.locator('#footprint-title')).toContainText('1m');
  expect(errors).toEqual([]);
});
test('fault recovery contracts and bounded replay',async({page,labURL})=>{
  await ready(page,labURL);
  for(const [scenario,step,status] of [['gap',24,'GAP'],['gap',32,'COHERENT'],['stale',48,'STALE'],['stale',56,'COHERENT'],['reconnect',72,'DISCONNECTED'],['reconnect',80,'COHERENT']]){
    await page.selectOption('#scenario',scenario);await seek(page,step);
    await expect(page.locator('#book-state')).toHaveText(status);
  }
  await page.selectOption('#scenario','future');
  await expect(page.locator('#source-state')).toHaveText('FUTURE_LEAKAGE');
  await expect(page.locator('#contracts')).toContainText('FUTURE_LEAKAGE');
  await page.selectOption('#scenario','unavailable');
  await expect(page.locator('#source-state')).toHaveText('UNAVAILABLE');
  await expect(page.locator('#book-body tr')).toHaveCount(0);
});
test('superseded requests cannot keep another symbol visible',async({page,labURL})=>{
  await ready(page,labURL);
  let delay=true;
  await page.route('**/api/synthetic/frame*',async route=>{
    if(delay&&route.request().url().includes('BTCUSDT')){await new Promise(r=>setTimeout(r,400));}
    await route.continue().catch(()=>{});
  });
  await page.locator('#step-once').click();
  await page.selectOption('#symbol','SOLUSDT');
  await expect(page.locator('body')).toHaveAttribute('data-identity','SOLUSDT|1m');
  delay=false;
  await page.waitForTimeout(500);
  await expect(page.locator('body')).toHaveAttribute('data-identity','SOLUSDT|1m');
  expect(await page.evaluate(()=>window.r2.metrics().aborted)).toBeGreaterThan(0);
});
test('stress frame pipeline memory CPU and lifecycle evidence',async({page,labURL,browserName},info)=>{
  await ready(page,labURL);
  let cdp=null,before=null;
  if(browserName==='chromium'){
    cdp=await page.context().newCDPSession(page);
    await cdp.send('Performance.enable');await cdp.send('HeapProfiler.collectGarbage');
    before=await cdp.send('Performance.getMetrics');
  }
  await page.selectOption('#scenario','mixed');
  const pipelineBefore=await page.evaluate(()=>window.r2.metrics());
  await page.evaluate(()=>{for(let i=0;i<1000;i++)window.dispatchEvent(new Event('resize'));});
  expect((await page.evaluate(()=>window.r2.metrics())).rafPending).toBeLessThanOrEqual(1);
  const started=Date.now();
  for(let i=0;i<40;i++)await seek(page,(i*17)%601);
  const playStart=await page.locator('body').getAttribute('data-step'),playClock=Date.now();
  await page.locator('#play').click();await page.waitForTimeout(2200);await page.locator('#play').click();
  const playWallMs=Date.now()-playClock;
  const playUpdates=Number(await page.locator('body').getAttribute('data-step'))-Number(playStart);
  await expect.poll(()=>page.evaluate(()=>window.r2.metrics().activeRequests)).toBe(0);
  await expect.poll(()=>page.evaluate(()=>window.r2.metrics().rafPending)).toBe(0);
  const idleStart=await page.evaluate(()=>window.r2.metrics().renders);await page.waitForTimeout(300);
  const metrics=await page.evaluate(()=>window.r2.metrics());
  metrics.playRateHz=playUpdates/(playWallMs/1000);metrics.idleExtraRenders=metrics.renders-idleStart;
  expect(metrics.playRateHz).toBeGreaterThanOrEqual(1.2);expect(metrics.playRateHz).toBeLessThanOrEqual(5.5);expect(metrics.idleExtraRenders).toBe(0);
  expect(metrics.listeners).toBe(pipelineBefore.listeners);
  expect(metrics.retainedCandles).toBeLessThanOrEqual(240);
  expect(metrics.retainedEvents).toBeLessThanOrEqual(20);
  expect(metrics.renderSamples).toBeLessThanOrEqual(240);
  expect(metrics.activeRequests).toBe(0);expect(metrics.peakRequests).toBeLessThanOrEqual(4);
  expect(metrics.rafPending).toBeLessThanOrEqual(1);expect(metrics.avgRenderMs).toBeLessThan(20);expect(metrics.p95RenderMs).toBeLessThan(50);
  let enginePerformance={available:false,reason:'CDP heap/TaskDuration unavailable in Firefox'};
  if(cdp){
    await cdp.send('HeapProfiler.collectGarbage');const after=await cdp.send('Performance.getMetrics');
    const m=(v,name)=>v.metrics.find(m=>m.name===name)?.value||0;
    const growth=m(after,'JSHeapUsedSize')-m(before,'JSHeapUsedSize');
    expect(growth).toBeLessThan(12*1024*1024);
    enginePerformance={available:true,heapGrowthBytes:growth,mainThreadCpuMs:1000*(m(after,'TaskDuration')-m(before,'TaskDuration'))};
    expect(enginePerformance.mainThreadCpuMs/(Date.now()-started)).toBeLessThan(.75);
  }
  await page.screenshot({path:info.outputPath('stress-preview.png'),fullPage:true});
  await page.evaluate(()=>window.r2.dispose());
  const disposed=await page.evaluate(()=>window.r2.metrics());
  expect(disposed.listeners).toBe(0);expect(disposed.rafPending).toBe(0);expect(disposed.timerPending).toBe(0);
  expect(disposed.bookRows).toBe(0);
  const status=await (await page.request.get(labURL+'/api/status')).json();
  const evidence={candidate_sha:status.candidate_sha,source_clean:status.source_clean,mode:'SYNTHETIC',physical:'PENDING',project:info.project.name,wallMs:Date.now()-started,metrics,disposed,enginePerformance};
  const file=info.outputPath('performance.json');fs.writeFileSync(file,JSON.stringify(evidence,null,2));await info.attach('performance',{path:file,contentType:'application/json'});
});

test('partial HTTP failure and in-flight disposal abort all requests',async({page,labURL})=>{
  await ready(page,labURL);
  await page.route('**/api/synthetic/contracts*',async route=>{
    await new Promise(r=>setTimeout(r,1400));
    await route.fulfill({json:{mode:'SYNTHETIC',sources:[]}}).catch(()=>{});
  });
  await page.route('**/api/synthetic/frame*',route=>route.fulfill({status:500,json:{error:'Synthetic test failure'}}));
  await page.locator('#step-once').click();
  await expect(page.locator('#error')).toHaveText('Synthetic test failure');
  await expect.poll(()=>page.evaluate(()=>window.r2.metrics().activeRequests),{timeout:700}).toBe(0);
  await page.unrouteAll({behavior:'ignoreErrors'});
  await ready(page,labURL);
  await page.route('**/api/synthetic/frame*',async route=>{
    await new Promise(r=>setTimeout(r,1400));await route.continue().catch(()=>{});
  });
  await page.locator('#step-once').click();
  await expect.poll(()=>page.evaluate(()=>window.r2.metrics().activeRequests)).toBeGreaterThan(0);
  await page.evaluate(()=>window.r2.dispose());
  await expect.poll(()=>page.evaluate(()=>window.r2.metrics().activeRequests),{timeout:700}).toBe(0);
  const disposed=await page.evaluate(()=>window.r2.metrics());
  expect(disposed.listeners).toBe(0);expect(disposed.rafPending).toBe(0);expect(disposed.timerPending).toBe(0);
});

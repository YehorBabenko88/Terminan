const {test,expect}=require('@playwright/test');
const {spawn,spawnSync}=require('node:child_process');const fs=require('node:fs');
let child,url,stderrBytes=0;
function launch(){const p=spawn(process.env.R2_PYTHON||'python',['-m','terminan.r4_runner'],{stdio:['pipe','pipe','pipe']});p.stderr.on('data',b=>{stderrBytes+=b.length;});return p;}
async function ready(p){return new Promise((resolve,reject)=>{let line='';const t=setTimeout(()=>reject(Error('STARTUP_TIMEOUT')),15000);p.once('error',()=>{clearTimeout(t);reject(Error('STARTUP_FAILED'));});p.stdout.on('data',b=>{line+=b;if(line.includes('\n')){clearTimeout(t);resolve('http://127.0.0.1:'+JSON.parse(line.split('\n')[0]).port);}});});}
test.beforeAll(async()=>{
 child=launch();
 url=await new Promise((resolve,reject)=>{let text='';const timer=setTimeout(()=>reject(Error('startup timeout')),15000);child.on('error',reject);child.stdout.on('data',b=>{text+=b;if(text.includes('\n')){clearTimeout(timer);resolve('http://127.0.0.1:'+JSON.parse(text.split('\n')[0]).port);}});});
});
test.afterAll(async()=>{if(child&&child.exitCode===null){await new Promise(resolve=>{const t=setTimeout(()=>child.kill(),10000);child.once('exit',()=>{clearTimeout(t);resolve();});child.stdin.end('quit\n');});}});
test('R4 bounded workloads contracts and session lifecycle',async({page,browserName},info)=>{
 let pageErrors=0,consoleErrors=0;page.on('pageerror',()=>pageErrors++);page.on('console',m=>{if(m.type()==='error')consoleErrors++;});
 expect(process.env.R4_INVOCATION).toMatch(/^[0-9a-f]{32}$/);test.setTimeout(180000);await page.goto(url);await expect(page.locator('body')).toHaveAttribute('data-loading','false');
 const size=await page.locator('#chart').evaluate(c=>({width:c.width,css:c.clientWidth,dpr:devicePixelRatio}));expect(Math.abs(size.width-size.css*size.dpr)).toBeLessThanOrEqual(2);
 const span=(await page.evaluate(()=>window.r2.metrics())).spanMs;await page.locator('#zoom-in').click();await expect.poll(()=>page.evaluate(()=>window.r2.metrics().spanMs)).toBeLessThan(span);
 const box=await page.locator('#chart').boundingBox();const beforePan=(await page.evaluate(()=>window.r2.metrics())).windowEnd;await page.mouse.move(box.x+box.width*.6,box.y+80);await page.mouse.down();await page.mouse.move(box.x+box.width*.8,box.y+80);await page.mouse.up();await expect.poll(()=>page.evaluate(()=>window.r2.metrics().windowEnd)).not.toBe(beforePan);
 await page.locator('#reset-view').click();await page.setViewportSize({width:960,height:1100});await expect.poll(()=>page.locator('#chart').evaluate(c=>c.width)).toBeLessThan(size.width);await page.setViewportSize({width:1440,height:1100});
 let resumeOld,oldSeen=false;const oldPayload=await(await page.request.get(url+'/api/synthetic/frame?step=10')).json();
 await page.route('**/api/synthetic/frame?*',async route=>{if(new URL(route.request().url()).searchParams.get('step')==='10'){oldSeen=true;await new Promise(resolve=>resumeOld=resolve);await route.fulfill({json:oldPayload}).catch(()=>{});}else await route.continue();});
 await page.evaluate(()=>{window.r2.seek(10);});await expect.poll(()=>oldSeen).toBe(true);await page.selectOption('#symbol','ETHUSDT');await page.selectOption('#timeframe','5m');await expect(page.locator('body')).toHaveAttribute('data-identity','ETHUSDT|5m');resumeOld();await page.waitForTimeout(100);await expect(page.locator('body')).toHaveAttribute('data-identity','ETHUSDT|5m');expect((await page.evaluate(()=>window.r2.metrics())).aborted).toBeGreaterThan(0);await page.unroute('**/api/synthetic/frame?*');
 await page.selectOption('#symbol','BTCUSDT');await page.selectOption('#timeframe','1m');await expect(page.locator('body')).toHaveAttribute('data-identity','BTCUSDT|1m');
 const status=await (await page.request.get(url+'/api/status')).json();
 const rawContracts=await (await page.request.get(url+'/api/synthetic/contracts?symbol=ETHUSDT&timeframe=5m')).json();
 expect(rawContracts.symbol).toBe('ETHUSDT');expect(rawContracts.timeframe).toBe('5m');
 const contractStates=rawContracts.sources.map(x=>x.state);expect(contractStates).toEqual(['UNSUPPORTED_TIMEFRAME','UNSUPPORTED_TIMEFRAME','HISTORICAL_ONLY','HISTORICAL_ONLY']);
 expect(rawContracts.sources.every(x=>x.symbol==='ETHUSDT'&&x.runtime_source==='NONE'&&x.authority!=='LIVE_SOURCE_VERIFIED')).toBe(true);
 const cdp=browserName==='chromium'?await page.context().newCDPSession(page):null;
 if(cdp)await cdp.send('Performance.enable');
 const sample=async()=>{if(!cdp)return null;await cdp.send('HeapProfiler.collectGarbage');const {metrics}=await cdp.send('Performance.getMetrics');return Object.fromEntries(metrics.map(x=>[x.name,x.value]));};
 const browserCDP=cdp?await page.context().browser().newBrowserCDPSession():null;
 const rss=async()=>{if(!browserCDP)return {state:'UNAVAILABLE',reason:'FIREFOX_CDP_UNSUPPORTED'};const {processInfo}=await browserCDP.send('SystemInfo.getProcessInfo');const result=spawnSync(process.env.R2_PYTHON||'python',['-m','terminan.process_metrics',...processInfo.map(p=>String(p.id))],{encoding:'utf8'});if(result.status!==0)throw Error('Resource sampler failed');return JSON.parse(result.stdout);};
 const rssBefore=await rss();const before=await sample(),results=[];
 for(const updates of [10000,100000]){
  await page.evaluate(()=>window.r2.seek(100));
  const result=await page.evaluate(updates=>window.r2.benchmark({updates,batch:100,seed:17}),updates);
  let checksum=17;for(let i=0;i<updates;i++)checksum=(Math.imul(checksum,1664525)+1013904223)>>>0;
  expect(result.checksum).toBe(checksum);expect(result.updates).toBe(updates);expect(result.frames).toBe(updates/100);
  expect(result.latencyMs.p99).toBeLessThan(100);expect(result.drawMs.p95).toBeLessThan(50);
  expect(result.renderCadenceFps).toBeGreaterThan(10);expect(result.metrics.retainedCandles).toBeLessThanOrEqual(240);
  expect(result.metrics.retainedEvents).toBeLessThanOrEqual(20);expect(result.metrics.bookRows).toBeLessThanOrEqual(40);
  results.push(result);
 }
 const rssAfter=await rss();const after=await sample();const wall=results.reduce((s,r)=>s+r.elapsedMs/1000,0);
 const resources=cdp?{state:'AVAILABLE',scope:'CHROMIUM_MAIN_THREAD_CPU_AND_GC_JS_HEAP_NOT_TOTAL_PROCESS_RAM',cpuDuty:(after.TaskDuration-before.TaskDuration)/wall,heapGrowthBytes:after.JSHeapUsedSize-before.JSHeapUsedSize,heapBefore:before.JSHeapUsedSize,heapAfter:after.JSHeapUsedSize}:{state:'UNAVAILABLE',reason:'FIREFOX_CDP_UNSUPPORTED'};
 resources.processMemory={before:rssBefore,after:rssAfter};
 if(cdp){expect(rssBefore.state).toBe('AVAILABLE');expect(rssAfter.state).toBe('AVAILABLE');expect(rssAfter.rss_bytes).toBeLessThan(2*1024**3);expect(rssAfter.rss_bytes-rssBefore.rss_bytes).toBeLessThan(256*1024**2);expect(resources.cpuDuty).toBeLessThan(.75);expect(resources.heapGrowthBytes).toBeLessThan(12*1024*1024);}
 const fetchMetrics=await page.evaluate(()=>window.r2.metrics());expect(fetchMetrics.fetchSamples).toBeGreaterThanOrEqual(4);expect(fetchMetrics.fetchLatencyMs.p95).toBeLessThan(2000);expect(fetchMetrics.fetchLatencyMs.p99).toBeLessThan(5000);
 await page.route('**/api/synthetic/frame?*',()=>{});
 await page.evaluate(()=>window.r2.seek(101));await expect(page.locator('#source-state')).toHaveText('ERROR');
 await page.unroute('**/api/synthetic/frame?*');await page.evaluate(()=>window.r2.seek(100));
 const exclusive=await page.evaluate(async()=>{const first=window.r2.benchmark({updates:10000});const second=await window.r2.benchmark({updates:10000}).then(()=>false,()=>true);await window.r2.seek(110);await first.catch(()=>{});return second;});expect(exclusive).toBe(true);
 const cancelled=await page.evaluate(async()=>{const pending=window.r2.benchmark({updates:100000}).then(()=>false,()=>true);await window.r2.seek(120);return pending;});expect(cancelled).toBe(true);
 // Unplanned loss is bounded DISCONNECTED, never inferred SESSION_ENDED.
 const other=launch();let otherPage,unexpectedStop;
 try{
  const otherURL=await ready(other);otherPage=await page.context().newPage();await otherPage.goto(otherURL);await expect(otherPage.locator('body')).toHaveAttribute('data-loading','false');
  other.kill();await expect.poll(()=>otherPage.evaluate(()=>window.r4.metrics().session.closed),{timeout:18000}).toBe(true);
  await expect(otherPage.locator('#session-state')).toHaveText('DISCONNECTED');
  const m=await otherPage.evaluate(()=>window.r4.metrics().session);expect(m.retries).toBeLessThanOrEqual(5);expect(m.requests).toBeLessThanOrEqual(8);
  await otherPage.waitForTimeout(1100);expect((await otherPage.evaluate(()=>window.r4.metrics().session)).requests).toBe(m.requests);unexpectedStop={state:m.state,bounded:true,requests:m.requests,retries:m.retries,noRevival:true};
 }finally{if(other.exitCode===null)other.kill();await otherPage?.close();}
 await page.screenshot({path:info.outputPath('r4-preview.png')});
 child.stdin.end('quit\n');await expect(page.locator('#session-state')).toHaveText('SESSION_ENDED',{timeout:8000});
 await expect.poll(()=>child.exitCode,{timeout:10000}).toBe(0);
 const end=await page.evaluate(()=>window.r4.metrics().session);await page.waitForTimeout(200);const consoleAtEnd=consoleErrors;await page.waitForTimeout(1100);expect(consoleErrors).toBe(consoleAtEnd);expect(pageErrors).toBe(0);expect((await page.evaluate(()=>window.r4.metrics().session)).requests).toBe(end.requests);expect(stderrBytes).toBe(0);
 await page.waitForTimeout(100);
 const disposed=await page.evaluate(()=>window.r2.metrics());expect(disposed.listeners).toBe(0);expect(disposed.rafPending).toBe(0);expect(disposed.activeRequests).toBe(0);
 fs.writeFileSync(info.outputPath('r4-performance.json'),JSON.stringify({version:1,invocation:process.env.R4_INVOCATION,run_id:process.env.GITHUB_RUN_ID||'LOCAL',attempt:process.env.GITHUB_RUN_ATTEMPT||'1',candidate_sha:status.candidate_sha,source_clean:status.source_clean,project:info.project.name,results,resources,disposed,r4:{version:1,contractStates,fetch:{quantiles:fetchMetrics.fetchLatencyMs,samples:fetchMetrics.fetchSamples,clock:fetchMetrics.fetchClock},normalStop:{state:end.state,closed:end.closed,requestsStable:true,childExit:child.exitCode,consoleErrorsAfterEnd:0},unexpectedStop,limitations:['RENDER_CADENCE_NOT_PRESENTATION_FPS','MAIN_THREAD_CPU_NOT_HOST_TOTAL','RSS_SUM_MAY_COUNT_SHARED_PAGES','OFFLINE_FIXTURES_NO_RUNTIME_AUTHORITY']} },null,2));
});

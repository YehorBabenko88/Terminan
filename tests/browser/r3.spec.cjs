const {test,expect}=require('@playwright/test');
const {spawn,spawnSync}=require('node:child_process');const fs=require('node:fs');
let child,url;
test.beforeAll(async()=>{
 child=spawn(process.env.R2_PYTHON||'python',['-m','terminan.r2_runner'],{stdio:['pipe','pipe','pipe']});
 url=await new Promise((resolve,reject)=>{let text='';const timer=setTimeout(()=>reject(Error('startup timeout')),15000);child.on('error',reject);child.stdout.on('data',b=>{text+=b;if(text.includes('\n')){clearTimeout(timer);resolve('http://127.0.0.1:'+JSON.parse(text.split('\n')[0]).port);}});});
});
test.afterAll(async()=>{if(child&&child.exitCode===null){await new Promise(resolve=>{const t=setTimeout(()=>child.kill(),10000);child.once('exit',()=>{clearTimeout(t);resolve();});child.stdin.end('quit\n');});}});
test('R3 bounded 10k 100k renderer workloads and cancellation',async({page,browserName},info)=>{
 expect(process.env.R3_INVOCATION).toMatch(/^[0-9a-f]{32}$/);test.setTimeout(120000);await page.goto(url);await expect(page.locator('body')).toHaveAttribute('data-loading','false');
 const status=await (await page.request.get(url+'/api/status')).json();
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
 await page.route('**/api/synthetic/frame?*',()=>{});
 await page.evaluate(()=>window.r2.seek(101));await expect(page.locator('#source-state')).toHaveText('ERROR');
 await page.unroute('**/api/synthetic/frame?*');await page.evaluate(()=>window.r2.seek(100));
 const exclusive=await page.evaluate(async()=>{const first=window.r2.benchmark({updates:10000});const second=await window.r2.benchmark({updates:10000}).then(()=>false,()=>true);await window.r2.seek(110);await first.catch(()=>{});return second;});expect(exclusive).toBe(true);
 const cancelled=await page.evaluate(async()=>{const pending=window.r2.benchmark({updates:100000}).then(()=>false,()=>true);await window.r2.seek(120);return pending;});expect(cancelled).toBe(true);
 await page.screenshot({path:info.outputPath('r3-preview.png')});
 await page.evaluate(()=>window.r2.dispose());await page.waitForTimeout(100);
 const disposed=await page.evaluate(()=>window.r2.metrics());expect(disposed.listeners).toBe(0);expect(disposed.rafPending).toBe(0);expect(disposed.activeRequests).toBe(0);
 fs.writeFileSync(info.outputPath('r3-performance.json'),JSON.stringify({version:1,invocation:process.env.R3_INVOCATION,run_id:process.env.GITHUB_RUN_ID||'LOCAL',attempt:process.env.GITHUB_RUN_ATTEMPT||'1',candidate_sha:status.candidate_sha,source_clean:status.source_clean,project:info.project.name,results,resources,disposed},null,2));
});

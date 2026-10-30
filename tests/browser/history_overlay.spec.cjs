const {test,expect}=require('@playwright/test');
const {spawn,execFileSync}=require('node:child_process');
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(process.env.HISTORY_EVIDENCE||'reports/history-evidence');
const files=['history-0.json','history-1.json','scientific.json'].map(f=>path.join(root,f));
let child,url;
test.beforeAll(async()=>{
 for(const f of files)if(!fs.existsSync(f))throw Error('REAL_PRODUCER_EVIDENCE_REQUIRED: '+f);
 const env={...process.env,PYTHONPATH:'.'};
 for(const k of Object.keys(env))if(k.startsWith('TERMINAN_'))delete env[k];
 child=spawn(process.env.R2_PYTHON||'python',['scripts/math_lab_test_server.py'],{env,windowsHide:true,stdio:['pipe','pipe','pipe']});
 url=await new Promise((resolve,reject)=>{let s='',err='';const t=setTimeout(()=>reject(Error('SERVER_TIMEOUT '+err)),10000);
  child.stderr.on('data',b=>err+=b);child.once('error',reject);child.once('exit',()=>{clearTimeout(t);reject(Error('SERVER_EXIT '+err))});
  child.stdout.on('data',b=>{s+=b;if(s.includes('\n')){clearTimeout(t);resolve(JSON.parse(s.split('\n')[0]).url.replace('/math','/history-overlay'))}})});
});
test.afterAll(async()=>{if(child&&child.exitCode===null){const done=new Promise(r=>child.once('exit',r));child.stdin.end('\n');await done}});
test.beforeEach(async({page})=>{await page.goto(url)});
async function load(page,which=files){await page.setInputFiles('#upload',which);await expect(page.locator('#status')).toContainText('READ_ONLY')}
function reseal(p){
 // Use the real producer's Python canonicalization, including float spelling.
 return execFileSync(process.env.R2_PYTHON||'python',['-c',"import sys,json,hashlib;p=json.load(sys.stdin);k='handoff_sha256' if 'handoff_sha256' in p else 'packet_sha256';p.pop(k);p[k]=hashlib.sha256(json.dumps(p,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest();print(json.dumps(p))"],{input:JSON.stringify(p)});
}
async function uploadBuffer(page,buffer){await page.setInputFiles('#upload',{name:'packet.json',mimeType:'application/json',buffer})}

test('real producer exports compose independent forecast and scientific layers',async({page},info)=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await load(page);
 await expect(page.locator('.layer-toggle')).toHaveCount(5);
 await expect(page.locator('.forecast-past')).toHaveCount(120);
 await expect(page.locator('.forecast-future')).toHaveCount(0);
 await expect(page.locator('.scientific-line')).toHaveCount(3);
 await expect(page.locator('#identity')).toContainText('BTCUSDT');
 await expect(page.locator('#provenance')).toContainText('grid-frozen-analog-v1');
 await expect(page.locator('#provenance')).toContainText('1f97e567');
 await expect(page.locator('#provenance')).toContainText('SHA256_MATCH');
 await expect(page.locator('#oos')).toContainText('PRODUCER_REPORTED_OOS_UNATTESTED');
 await expect(page.locator('#oos')).toContainText('net_pnl');
 // Real fixture range is [101,109.989]; 8% axis padding gives
 // [100.28088,110.70812]. Tick labels must describe the plotted scale.
 await expect(page.locator('#chart text').filter({hasText:/^110\.708$/})).toHaveCount(1);
 await expect(page.locator('#chart text').filter({hasText:/^100\.281$/})).toHaveCount(1);
 const colors=await page.locator('.layer-toggle').evaluateAll(ns=>ns.map(n=>n.dataset.color));expect(new Set(colors).size).toBe(5);
 expect(errors).toEqual([]);await info.attach('research-overlay',{body:await page.screenshot({fullPage:true}),contentType:'image/png'});
});

test('asOf separates past predictions, future targets, observations and published OOS',async({page})=>{
 await load(page,[files[0]]);
 await page.fill('#asof','3000000');await page.locator('#asof').dispatchEvent('change');
 await expect(page.locator('.observation-point')).toHaveCount(50);
 await expect(page.locator('.forecast-past')).toHaveCount(30);
 await expect(page.locator('.forecast-future')).toHaveCount(1);
 await expect(page.locator('#oos')).toContainText('NOT_AVAILABLE_ASOF');
 await page.selectOption('#mode','forward');
 await expect(page.locator('.forecast-past')).toHaveCount(0);
 await expect(page.locator('.forecast-future')).toHaveCount(1);
 await expect(page.locator('.observation-point')).toHaveCount(50);
 await page.fill('#asof','0');await page.locator('#asof').dispatchEvent('change');
 await expect(page.locator('.forecast-future')).toHaveCount(0);await expect(page.locator('.observation-point')).toHaveCount(0);
});

test('zoom, drag and keyboard pan, timeline, tooltip and receipt-scoped persistence',async({page})=>{
 await load(page);const before=await page.inputValue('#from');await page.click('#zoomIn');
 expect(await page.inputValue('#from')).not.toBe(before);
 const zoomed=await page.inputValue('#from');const box=await page.locator('#chart').boundingBox();
 await page.mouse.move(box.x+box.width*.5,box.y+100);await page.mouse.down();await page.mouse.move(box.x+box.width*.6,box.y+100);await page.mouse.up();
 expect(await page.inputValue('#from')).not.toBe(zoomed);
 await page.locator('#chart').focus();const pan=await page.inputValue('#from');await page.keyboard.press('ArrowRight');expect(await page.inputValue('#from')).not.toBe(pan);
 await page.locator('#chart').scrollIntoViewIfNeeded();const wheelBox=await page.locator('#chart').boundingBox();
 await page.mouse.move(wheelBox.x+wheelBox.width*.5,wheelBox.y+wheelBox.height*.5);
 await expect(page.locator('#crossX')).toHaveAttribute('visibility','visible');
 const wheelBefore=await page.inputValue('#to');await page.mouse.wheel(0,-200);
 await expect(page.locator('#to')).not.toHaveValue(wheelBefore);
 await page.click('#fit');await page.locator('.forecast-past').first().focus();
 await expect(page.locator('#tooltip')).toContainText('decision');await expect(page.locator('#tooltip')).toContainText('target');
 await page.locator('#asofSlider').fill('3000000');await page.locator('#asofSlider').dispatchEvent('input');
 await expect(page.locator('#asof')).toHaveValue('3000000');
 await page.locator('.layer-toggle').first().uncheck();await page.click('#zoomIn');
 const savedFrom=await page.inputValue('#from');await page.reload();await load(page);
 await expect(page.locator('#from')).toHaveValue(savedFrom);await expect(page.locator('#asof')).toHaveValue('3000000');
 await expect(page.locator('.layer-toggle').first()).not.toBeChecked();
 await page.fill('#to','0');await page.locator('#to').dispatchEvent('change');
 await expect(page.locator('#status')).toContainText('INVALID_TIME_RANGE');await expect(page.locator('.forecast-past')).toHaveCount(0);
 await page.click('#fit');await expect(page.locator('#status')).toContainText('READ_ONLY');
});

test('tampered, forged trust, clock inversions and incompatible units fail without partial imports',async({page})=>{
 await load(page,[files[0]]);const original=JSON.parse(fs.readFileSync(files[0]));
 const corrupt=structuredClone(original);corrupt.forecast_points[0].value=999;
 await uploadBuffer(page,Buffer.from(JSON.stringify(corrupt)));await expect(page.locator('#status')).toContainText('DIGEST_MISMATCH');
 await expect(page.locator('.layer-toggle')).toHaveCount(1);
 for(const mutate of [p=>p.trading_authorized=true,p=>p.source_authenticity='VERIFIED',
   p=>p.forecast_points[0].decision_ms=p.forecast_points[0].target_event_end_ms,
   p=>p.units.price='USD/BTC',p=>p.observed_prices[0].watermark_ms=0]){
  const p=structuredClone(original);mutate(p);await uploadBuffer(page,reseal(p));await expect(page.locator('#status')).toContainText('IMPORT_REJECTED');
  await expect(page.locator('.layer-toggle')).toHaveCount(1);
 }
 const other=structuredClone(original);other.market.symbol='ETHUSDT';
 await uploadBuffer(page,reseal(other));await expect(page.locator('#status')).toContainText('INCOMPATIBLE_DATASET');
 await uploadBuffer(page,Buffer.from('{bad'));await expect(page.locator('#status')).toContainText('IMPORT_REJECTED');
 await uploadBuffer(page,Buffer.alloc(2*1024*1024+1,32));await expect(page.locator('#status')).toContainText('FILE_LIMIT');
 await load(page,[files[1]]);await expect(page.locator('.layer-toggle')).toHaveCount(2);
 await load(page,[files[1]]);await expect(page.locator('.layer-toggle')).toHaveCount(2);
});

test('scientific results keep event axes and reject rehashed request or output substitutions',async({page})=>{
 await load(page,[files[0],files[2]]);await expect(page.locator('.layer-toggle')).toHaveCount(4);
 const p=JSON.parse(fs.readFileSync(files[2]));p.request.nodes[1].window=7;
 await uploadBuffer(page,reseal(p));await expect(page.locator('#status')).toContainText('SCIENTIFIC_REQUEST_DIGEST');
 const q=JSON.parse(fs.readFileSync(files[2]));q.result.outputs[0].values[0]=999;
 await uploadBuffer(page,reseal(q));await expect(page.locator('#status')).toContainText('SCIENTIFIC_OUTPUT_DIGEST');
 await expect(page.locator('.layer-toggle')).toHaveCount(4);
});

test('real Scientific lag is historical even when Math reports earlier availability',async({page})=>{
 await load(page);await page.fill('#asof','3000000');await page.locator('#asof').dispatchEvent('change');
 // Engine lag shifts known values to later timestamps: it is not a frozen forecast.
 // mean=48, affine=50, lag=49 event timestamps no later than asOf.
 await expect(page.locator('.scientific-point')).toHaveCount(147);
});

test('clear and a newer import cannot be overwritten by an older asynchronous validation',async({page})=>{
 let release,started;const gate=new Promise(r=>release=r),seen=new Promise(r=>started=r);
 await page.route('**/api/history-overlay/validate',async route=>{const response=await route.fetch();started();await gate;await route.fulfill({response})},{times:1});
 await page.setInputFiles('#upload',files[0]);await seen;await page.click('#clear');
 await load(page,[files[1]]);const done=page.waitForResponse(r=>r.url().endsWith('/api/history-overlay/validate'));release();await done;
 await expect(page.locator('.layer-toggle')).toHaveCount(1);
 const p=JSON.parse(fs.readFileSync(files[1]));await expect(page.locator('#provenance')).toContainText(p.handoff_sha256);
});

test('unavailable validator, invalid asOf and corrupt storage recover without false data',async({page})=>{
 await page.route('**/api/history-overlay/validate',r=>r.fulfill({status:503,body:'offline'}),{times:1});
 await page.setInputFiles('#upload',files[0]);await expect(page.locator('#status')).toContainText('VALIDATOR_UNAVAILABLE');
 await expect(page.locator('.layer-toggle')).toHaveCount(0);await load(page,[files[0]]);
 await page.fill('#asof','-1');await page.locator('#asof').dispatchEvent('change');
 await expect(page.locator('#status')).toContainText('INVALID_ASOF');await expect(page.locator('.observation-point')).toHaveCount(0);
 await page.evaluate(()=>{for(const k of Object.keys(localStorage))if(k.startsWith('terminan.overlay.view'))localStorage.setItem(k,'{bad')});
 await page.reload();await load(page,[files[0]]);await expect(page.locator('.observation-point')).toHaveCount(80);
 await page.locator('#provenance details').first().click();
 await expect(page.locator('#provenance')).not.toContainText('987654321');
});

test('max safe singleton time remains viewable and provenance cannot leak future OOS',async({page})=>{
 const p=JSON.parse(fs.readFileSync(files[0]));p.observed_prices=[{event_end_ms:Number.MAX_SAFE_INTEGER,
  available_at_ms:Number.MAX_SAFE_INTEGER,watermark_ms:Number.MAX_SAFE_INTEGER,value:101}];
 p.forecast_points=[];delete p.oos_available_at_ms;p.source.oos_metrics={net_pnl:987654321};
 await uploadBuffer(page,reseal(p));await expect(page.locator('#status')).toContainText('READ_ONLY');
 await expect(page.locator('.observation-point')).toHaveCount(1);
 await page.fill('#asof','0');await page.locator('#asof').dispatchEvent('change');
 await page.locator('#provenance details').first().click();await expect(page.locator('#provenance')).not.toContainText('987654321');
 await expect(page.locator('.observation-point')).toHaveCount(0);
});

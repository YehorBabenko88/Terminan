const {test,expect}=require('@playwright/test');
const {spawn}=require('node:child_process');
let child,url,engine;
test.beforeAll(async()=>{
 const env={...process.env,PYTHONPATH:'.'};for(const k of ['TERMINAN_GRID_DSN','TERMINAN_STRATTESTER_DB','TERMINAN_RESULTS_DB'])delete env[k];
 if(process.env.MATH_REPO){
  const path=require('node:path');
  engine=spawn('node',[path.resolve(process.env.MATH_REPO,'src/math-engine-server.mjs')],{env:{...env,MATH_ENGINE_PORT:'8788'},stdio:['pipe','pipe','pipe']});
  await new Promise((resolve,reject)=>{const t=setTimeout(()=>reject(Error('ENGINE_TIMEOUT')),10000);engine.stdout.once('data',()=>{clearTimeout(t);resolve()});engine.once('exit',()=>{clearTimeout(t);reject(Error('ENGINE_EXIT'))});engine.once('error',reject)});
  env.TERMINAN_MATH_OFFLINE_BRIDGE='1';
 }else delete env.TERMINAN_MATH_OFFLINE_BRIDGE;
 child=spawn(process.env.R2_PYTHON||'python',['scripts/math_lab_test_server.py'],{env,stdio:['pipe','pipe','pipe']});
 url=await new Promise((resolve,reject)=>{let s='';const t=setTimeout(()=>reject(Error('SERVER_TIMEOUT')),10000);child.stdout.on('data',b=>{s+=b;if(s.includes('\n')){clearTimeout(t);resolve(JSON.parse(s.split('\n')[0]).url)}});child.on('error',reject)});
});
test.afterAll(async()=>{if(child&&child.exitCode===null){const exited=new Promise(r=>child.once('exit',r));child.stdin.end('\n');await exited;}if(engine&&engine.exitCode===null)engine.kill();});
async function add(page,kind){await page.selectOption('#nodeKind',kind);await page.click('#addNode');}
async function port(page,id,direction,p=0){return page.locator(`[data-node="${id}"][data-direction="${direction}"][data-port="${p}"]`);}
async function link(page,a,b,p=0){await (await port(page,a,'out')).click();await (await port(page,b,'in',p)).click();}
function requestHash(d){const {createHash}=require('node:crypto');const canonical=x=>JSON.stringify(Array.isArray(x)?x.map(v=>JSON.parse(canonical(v))):x&&typeof x==='object'?Object.fromEntries(Object.keys(x).sort().map(k=>[k,JSON.parse(canonical(x[k]))])):x);const hash=x=>createHash('sha256').update(canonical(x)).digest('hex');return hash({...d,nodes:[...d.nodes].sort((a,b)=>a.id<b.id?-1:a.id>b.id?1:0),edges:[...d.edges].sort((a,b)=>hash(a)<hash(b)?-1:hash(a)>hash(b)?1:0)});}
test.beforeEach(async({page})=>{await page.goto(url);await expect(page.locator('#workspace')).toBeVisible()});
test('free nodes connect by mouse and keyboard, move, relink, delete, zoom and pan',async({page},info)=>{
 await add(page,'source');await add(page,'formula');await add(page,'formula');
 await link(page,'n1','n2');await (await port(page,'n2','out')).focus();await page.keyboard.press('Enter');await (await port(page,'n3','in')).focus();await page.keyboard.press('Enter');
 await expect(page.locator('.edge')).toHaveCount(2);
 const line=await page.locator('.edge').first().getAttribute('d');
 const handle=page.locator('[data-handle="n2"]');const b=await handle.boundingBox();await page.mouse.move(b.x+50,b.y+12);await page.mouse.down();await page.mouse.move(b.x+90,b.y+90);await page.mouse.up();
 expect(await page.locator('.edge').first().getAttribute('d')).not.toBe(line);
 await page.selectOption('#edgeSelect','e-n1-n2-0');await page.selectOption('#edgeFrom','n3');await page.click('#relinkEdge');await expect(page.locator('#status')).toContainText('CYCLE');
 await page.selectOption('#edgeFrom','n1');await page.click('#relinkEdge');await page.click('#deleteEdge');await expect(page.locator('.edge')).toHaveCount(1);
 await page.click('#zoomIn');await expect(page.locator('#zoomLabel')).toContainText('120');await page.click('#resetView');await expect(page.locator('#zoomLabel')).toContainText('100');
 const before=await page.locator('#world').getAttribute('transform');await page.locator('#workspace').focus();await page.keyboard.press('ArrowRight');expect(await page.locator('#world').getAttribute('transform')).not.toBe(before);
 await page.locator('[data-handle="n3"]').focus();await page.keyboard.press('Delete');await expect(page.locator('.node')).toHaveCount(2);await expect(page.locator('.edge')).toHaveCount(0);
 await info.attach('freeform-editor',{body:await page.screenshot({fullPage:true}),contentType:'image/png'});
});
test('type errors, transactional import/export, recovery and unavailable engine',async({page})=>{
 await add(page,'hypothesis');await add(page,'formula');await link(page,'n1','n2');await expect(page.locator('#status')).toContainText('TYPE');await expect(page.locator('.edge')).toHaveCount(0);
 await page.locator('[data-handle="n1"]').focus();await page.keyboard.press('Delete');await add(page,'source');await link(page,'n3','n2');
 const download=page.waitForEvent('download');await page.click('#exportGraph');const file=await download;const stream=await file.createReadStream();let text='';for await(const b of stream)text+=b;const doc=JSON.parse(text);expect(doc.edges).toHaveLength(1);
 await page.setInputFiles('#importGraph',{name:'bad.json',mimeType:'application/json',buffer:Buffer.from('{!')});await expect(page.locator('#status')).toContainText('IMPORT_REJECTED');await expect(page.locator('.node')).toHaveCount(2);
 await page.click('#clearGraph');await page.setInputFiles('#importGraph',{name:'graph.json',mimeType:'application/json',buffer:Buffer.from(text)});await expect(page.locator('.edge')).toHaveCount(1);
 await page.route('**/api/math/scientific',r=>r.fulfill({status:422,json:{error:'MATH_ENGINE_UNAVAILABLE',trading_authorized:false}}));
 await page.click('#execute');await expect(page.locator('#status')).toContainText(/BRIDGE_DISABLED|UNAVAILABLE/);await expect(page.locator('#experiments article')).toHaveCount(0);
});
test('parameter validation, stale responses, authority refusal and legacy formula delegation',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await add(page,'source');await add(page,'formula');await link(page,'n1','n2');
 await page.fill('#editFormula','x+2');await page.click('#applyNode');
 let release;await page.route('**/api/math/scientific',async route=>{await new Promise(r=>release=r);await route.fulfill({json:{schema:'math.scientific.result.v2',status:'RESEARCH_ONLY',requestSHA256:'a'.repeat(64),source:'CALLER_SUPPLIED_UNATTESTED',execution_authority:false,trading_authorized:false,training_authorized:false,mathematicallyVerified:false,outputs:[{node:'n2',port:'value',type:'series',unit:'dimensionless',values:[3,4,5],timestamps:[0,60000,120000],availableAt:[0,60000,120000]}],trace:[],order:['n1','n2']}}).catch(()=>{});});
 await page.click('#execute');await expect.poll(()=>!!release).toBe(true);await page.fill('#editFormula','x+3');await page.click('#applyNode');release();await page.unroute('**/api/math/scientific');await expect(page.locator('#experiments article')).toHaveCount(0);
 await page.route('**/api/math/scientific',r=>r.fulfill({json:{schema:'math.scientific.result.v2',trading_authorized:true}}));await page.click('#execute');await expect(page.locator('#status')).toContainText('UNTRUSTED');
 await page.locator('details').last().locator('summary').click();let sent;
 await page.route('**/api/math/formula',async r=>{sent=r.request().postDataJSON();await r.fulfill({json:{schema:'math.formula.result.v1',execution_authority:false,trading_authorized:false,values:[1,2]}})});
 await page.fill('#formulaText','x+1');await page.click('#runFormula');await expect(page.locator('#formulaResult')).toContainText('values');expect(sent.formula).toBe('x+1');expect(sent.execution_authority).toBe(false);expect(errors).toEqual([]);
 await add(page,'method');await page.fill('#editParameter','');await page.click('#applyNode');await expect(page.locator('#status')).toContainText('INVALID_NUMERIC_PARAMETER');
 await page.fill('#editParameter','NaN');await page.click('#applyNode');await expect(page.locator('#status')).toContainText('INVALID_NUMERIC_PARAMETER');
});
test('real pinned Math executes two formulas, overlays models and rejects invalid AST',async({page},info)=>{
 test.skip(!process.env.MATH_REPO,'Set MATH_REPO to independently pinned Math checkout');
 await add(page,'source');await add(page,'formula');await add(page,'model');await add(page,'method');await link(page,'n1','n2');await link(page,'n2','n3');await link(page,'n1','n4');
 await page.click('#execute');await expect(page.locator('#experiments article')).toHaveCount(1);await expect(page.locator('#experiments article').first()).toContainText('n3');
 await page.locator('#experiments article').first().locator('details').first().locator('summary').click();await expect(page.locator('#experiments article').first().locator('table').first()).toContainText('5');
 await page.locator('[data-handle="n3"]').click();await page.fill('#editFormula','x^2');await page.click('#applyNode');await page.click('#execute');await expect(page.locator('#experiments article')).toHaveCount(2);await expect(page.locator('#chart polyline')).toHaveCount(4);
 await page.fill('#editFormula','globalThis.process.exit()');await page.click('#applyNode');await page.click('#execute');await expect(page.locator('#status')).toContainText('INVALID_SCIENTIFIC_REQUEST');await expect(page.locator('#experiments article')).toHaveCount(2);
 await page.fill('#editFormula','x*2');await page.click('#applyNode');await page.click('#execute');await expect(page.locator('#experiments article')).toHaveCount(3);
 await info.attach('real-math-overlay',{body:await page.screenshot({fullPage:true}),contentType:'image/png'});
});
test('imported IDs do not prevent new nodes and result charts use timestamps',async({page})=>{
 await add(page,'source');const download=page.waitForEvent('download');await page.click('#exportGraph');let text='';for await(const b of await(await download).createReadStream())text+=b;const d=JSON.parse(text);d.nodes[0].id='n1000';
 await page.setInputFiles('#importGraph',{name:'large-id.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(d))});await add(page,'formula');await expect(page.locator('.node')).toHaveCount(2);
 await page.click('#clearGraph');await add(page,'source');await add(page,'formula');await add(page,'result');await link(page,'n1','n2');await link(page,'n1','n3');
 await page.route('**/api/math/scientific',r=>r.fulfill({json:{schema:'math.scientific.result.v2',status:'RESEARCH_ONLY',requestSHA256:requestHash(r.request().postDataJSON()),source:'CALLER_SUPPLIED_UNATTESTED',execution_authority:false,trading_authorized:false,training_authorized:false,mathematicallyVerified:false,outputs:[{node:'n2',port:'value',type:'series',unit:'dimensionless',values:[1,2],timestamps:[60000,120000],availableAt:[0,60000]},{node:'n1',port:'value',type:'series',unit:'dimensionless',values:[1,2,3],timestamps:[0,60000,120000],availableAt:[0,60000,120000]}],trace:[{node:'n1'},{node:'n2'}],order:['n1','n2']}}));
 await page.click('#execute');await expect(page.locator('#chart polyline')).toHaveCount(2);const lines=await page.locator('#chart polyline').evaluateAll(xs=>xs.map(x=>x.getAttribute('points')));expect(Number(lines[0].split(',')[0])).toBeGreaterThan(Number(lines[1].split(',')[0]));
});

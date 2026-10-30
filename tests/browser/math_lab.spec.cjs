const {test,expect}=require('@playwright/test');
const {spawn}=require('node:child_process');
let child,url,engine;
test.beforeAll(async()=>{
 const env={...process.env,PYTHONPATH:'.'};for(const k of ['TERMINAN_GRID_DSN','TERMINAN_STRATTESTER_DB','TERMINAN_RESULTS_DB'])delete env[k];
 if(process.env.MATH_REPO){
  const path=require('node:path');
  const serverPath=require('node:url').pathToFileURL(path.resolve(process.env.MATH_REPO,'src/math-engine-server.mjs')).href;
  const code=`import {startMathEngine} from ${JSON.stringify(serverPath)};const s=startMathEngine({port:0});s.on('listening',()=>console.log(JSON.stringify({port:s.address().port})));`;
  engine=spawn('node',['--input-type=module','-e',code],{env,windowsHide:true,stdio:['pipe','pipe','pipe']});
  const port=await new Promise((resolve,reject)=>{let out='';const t=setTimeout(()=>reject(Error('ENGINE_TIMEOUT')),10000);engine.stdout.on('data',b=>{out+=b;if(out.includes('\n')){clearTimeout(t);resolve(JSON.parse(out.split('\n')[0]).port)}});engine.once('exit',()=>{clearTimeout(t);reject(Error('ENGINE_EXIT'))});engine.once('error',reject)});
  env.TERMINAN_MATH_PORT=String(port);
  env.TERMINAN_MATH_OFFLINE_BRIDGE='1';
 }else delete env.TERMINAN_MATH_OFFLINE_BRIDGE;
 child=spawn(process.env.R2_PYTHON||'python',['scripts/math_lab_test_server.py'],{env,windowsHide:true,stdio:['pipe','pipe','pipe']});
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
 test.skip(!process.env.MATH_REPO,'Requires real timestamp/trace output');
 await add(page,'source');const download=page.waitForEvent('download');await page.click('#exportGraph');let text='';for await(const b of await(await download).createReadStream())text+=b;const d=JSON.parse(text);d.nodes[0].id='n1000';
 await page.setInputFiles('#importGraph',{name:'large-id.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(d))});await add(page,'formula');await expect(page.locator('.node')).toHaveCount(2);
 await page.click('#clearGraph');await add(page,'source');await add(page,'formula');await add(page,'result');await link(page,'n1','n2');await link(page,'n1','n3');
 await page.locator('[data-handle="n2"]').click();
 // Actual Math lag provides a shorter timestamp-aligned result; no fabricated trace.
 const download2=page.waitForEvent('download');await page.click('#exportGraph');let text2='';for await(const b of await(await download2).createReadStream())text2+=b;const short=JSON.parse(text2);short.nodes.find(n=>n.id==='n2').kind='lag';short.nodes.find(n=>n.id==='n2').parameters={steps:1};await page.setInputFiles('#importGraph',{name:'lag.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(short))});

 await page.click('#execute');await expect(page.locator('#chart polyline')).toHaveCount(2);const lines=await page.locator('#chart polyline').evaluateAll(xs=>xs.map(x=>x.getAttribute('points')));expect(Number(lines[0].split(',')[0])).toBeGreaterThan(Number(lines[1].split(',')[0]));
});
test('searchable library, history, explicit ports and fit improve editing',async({page})=>{
 await page.fill('#blockSearch','формула');await expect(page.locator('#blockLibrary button')).toHaveCount(1);await page.locator('#blockLibrary button').click();await expect(page.locator('.node')).toHaveCount(1);
 await page.click('#duplicateNode');await expect(page.locator('.node')).toHaveCount(2);await page.click('#undoGraph');await expect(page.locator('.node')).toHaveCount(1);await page.click('#redoGraph');await expect(page.locator('.node')).toHaveCount(2);
 await add(page,'source');await page.selectOption('#connectFrom','n3');await page.selectOption('#connectTo','n1');await page.click('#connectNodes');await expect(page.locator('.edge')).toHaveCount(1);
 await page.click('#fitGraph');await expect(page.locator('#status')).toContainText('FIT');await page.click('#saveGraph');await page.click('#clearGraph');await page.click('#restoreGraph');await expect(page.locator('.node')).toHaveCount(3);await expect(page.locator('.edge')).toHaveCount(1);
});
test('Math catalogue methods and pinned knowledge appear without fabricated sources',async({page})=>{
 await page.route('**/api/math/catalog',r=>r.fulfill({json:{schema:'math.scientific.capabilities.v2',execution_authority:false,trading_authorized:false,training_authorized:false,mathematicallyVerified:false,units:['dimensionless'],unitMetadata:[],dimensionBasis:[],ports:{method:{inputs:['x'],outputs:['value']},knowledge:{inputs:['x'],outputs:['value']}},methods:['sine'],knowledge:[{id:'reviewed-book',sha256:'a'.repeat(64),expression:'x*2',inputUnit:'dimensionless',outputUnit:'dimensionless',confidence:'NOT_VERIFIED',hypothesis:'Synthetic fixture only',source:{page:7,edition:'1',sourceHash:'b'.repeat(64)}}]}}));
 await page.reload();await page.fill('#blockSearch','reviewed-book');await expect(page.locator('#blockLibrary button')).toHaveCount(1);await page.locator('#blockLibrary button').click();await expect(page.locator('#inspector')).toContainText('NOT_VERIFIED');await expect(page.locator('#knowledgeReference')).toContainText('a'.repeat(64));
 await page.fill('#blockSearch','sine');await page.locator('#blockLibrary button').click();await expect(page.locator('#editMethod')).toHaveValue('sine');expect(await page.locator('#editMethod option').allTextContents()).toEqual(['sine']);
});
test('result viewport supports time zoom, pan, visibility and trace inspection',async({page})=>{
 test.skip(!process.env.MATH_REPO,'Requires real pinned engine');await add(page,'source');await add(page,'formula');await link(page,'n1','n2');await page.click('#execute');await expect(page.locator('#experiments article')).toHaveCount(1);
 const points=await page.locator('#chart polyline').getAttribute('points');await page.click('#chartZoomIn');expect(await page.locator('#chart polyline').getAttribute('points')).not.toBe(points);await page.click('#chartPanRight');await page.click('#chartReset');expect(await page.locator('#chart polyline').getAttribute('points')).toBe(points);
 await page.locator('#seriesLegend input').first().uncheck();await expect(page.locator('#chart polyline')).toHaveCount(0);await page.locator('#seriesLegend input').first().check();await expect(page.locator('#chart polyline')).toHaveCount(1);
 await page.locator('#experiments article details.trace summary').click();await expect(page.locator('.trace table')).toContainText('n2');await expect(page.locator('#chart .time-tick')).not.toHaveCount(0);
 await page.click('#chartZoomIn');await page.locator('[data-handle="n1"]').click();await page.fill('#edit_values','[1,2]');await page.fill('#edit_timestamps','[0,1000]');await page.fill('#edit_availableAt','[0,1000]');await page.click('#applyNode');for(let i=0;i<5;i++){const response=page.waitForResponse(r=>r.url().endsWith('/api/math/scientific'));await page.click('#execute');await response;await expect(page.locator('#status')).toContainText('RESEARCH_ONLY');}await expect(page.locator('#chartWindow')).toHaveText('00:00:00Z → 00:00:01Z');
});
test('drag ports creates branches and relinking can change target input',async({page})=>{
 await add(page,'source');await add(page,'formula');await add(page,'average');
 const a=await(await port(page,'n1','out')).boundingBox(),b=await(await port(page,'n2','in')).boundingBox();await page.mouse.move(a.x+a.width/2,a.y+a.height/2);await page.mouse.down();await page.mouse.move(b.x+b.width/2,b.y+b.height/2,{steps:8});await page.mouse.up();await expect(page.locator('.edge')).toHaveCount(1);
 await page.selectOption('#edgeSelect','e-n1-n2-0');await page.selectOption('#edgeTo','n3');await page.selectOption('#edgePort','1');await page.click('#relinkEdge');await expect(page.locator('.edge')).toHaveAttribute('data-edge','e-n1-n3-1');
});
test('ADMINIT reported chain is reproduced with literal results on isolated real Math',async({page},info)=>{
 test.skip(!process.env.MATH_REPO,'Requires pinned real Math');await add(page,'source');await add(page,'formula');await page.fill('#editFormula','x*2');await page.click('#applyNode');await add(page,'formula');await page.fill('#editFormula','x^2+1');await page.click('#applyNode');await link(page,'n1','n2');await link(page,'n2','n3');
 const response=page.waitForResponse(r=>r.url().endsWith('/api/math/scientific'));await page.click('#execute');const r=await(await response).json();expect(r.outputs[0].values).toEqual([5,17,37]);expect(r.execution_authority).toBe(false);expect(r.trading_authorized).toBe(false);await expect(page.locator('#experiments article')).toHaveCount(1);
 await info.attach('isolated-host-chain',{body:Buffer.from(JSON.stringify({scope:'ISOLATED_AUTOMATED_WINDOWS_HOST_REPRODUCTION',reported_physical:'USER_REPORTED_NOT_INDEPENDENTLY_ATTESTED',result:r},null,2)),contentType:'application/json'});await info.attach('physical-chain-preview',{body:await page.screenshot({fullPage:true}),contentType:'image/png'});
});
test('failed catalogue insertion preserves nodes and Escape cancels a port drag',async({page})=>{
 for(let i=0;i<12;i++)await add(page,'method');await page.fill('#blockSearch','sine');await page.locator('#blockLibrary button').click();await expect(page.locator('#editMethod')).toHaveValue('polynomial');await expect(page.locator('.node')).toHaveCount(12);
 await page.click('#clearGraph');await add(page,'source');await add(page,'formula');const a=await(await port(page,'n1','out')).boundingBox(),b=await(await port(page,'n2','in')).boundingBox();await page.mouse.move(a.x+8,a.y+8);await page.mouse.down();await page.mouse.move(b.x+8,b.y+8);await page.keyboard.press('Escape');await page.mouse.up();await expect(page.locator('.edge')).toHaveCount(0);await link(page,'n1','n2');await expect(page.locator('.edge')).toHaveCount(1);
});

test('v2.1 control experiment exposes named outputs, final-time scalars and independent visibility',async({page},info)=>{
 test.skip(!process.env.MATH_REPO,'Requires pinned v2.1');await expect(page.locator('#catalogState')).toContainText('2.1');await page.click('#loadV21Example');await expect(page.locator('.node')).toHaveCount(7);await expect(page.locator('[data-node="overlay"][data-output-port="reference"]')).toHaveCount(1);
 const response=page.waitForResponse(r=>r.url().endsWith('/api/math/scientific'));await page.click('#execute');const result=await(await response).json();await expect(page.locator('#experiments article')).toHaveCount(1);expect(result.outputs.find(o=>o.node==='comparison'&&o.port==='mae').values).toEqual([8]);expect(result.outputs.find(o=>o.node==='comparison'&&o.port==='mae').timestamps).toEqual([2000]);await expect(page.locator('[data-scalar="comparison:mae"]')).toHaveAttribute('data-timestamp','2000');await expect(page.locator('[data-scalar="comparison:mae"]')).toHaveAttribute('cx','980');
 const legends=page.locator('#seriesLegend label');const mae=legends.filter({hasText:'comparison:mae'});await mae.locator('input').uncheck();await expect(page.locator('[data-scalar="comparison:mae"]')).toHaveCount(0);await expect(page.locator('[data-scalar="comparison:rmse"]')).toHaveCount(1);await mae.locator('input').check();await expect(page.locator('[data-scalar="comparison:mae"]')).toHaveCount(1);
 await info.attach('v21-control-request',{body:Buffer.from(JSON.stringify((await response).request().postDataJSON(),null,2)),contentType:'application/json'});await info.attach('v21-verification',{body:Buffer.from(await page.locator('#experiments article pre').first().textContent()),contentType:'application/json'});await info.attach('v21-control-result',{body:Buffer.from(JSON.stringify(result,null,2)),contentType:'application/json'});await info.attach('v21-preview',{body:await page.screenshot({fullPage:true}),contentType:'image/png'});
});
test('downgrade hides new blocks and blocks imported v2.1 graph without local fallback',async({page})=>{
 test.skip(!process.env.MATH_REPO,'Requires v2.1 control fixture');await page.click('#loadV21Example');await page.route('**/api/math/catalog',async route=>{const r=await route.fetch();const c=await r.json();delete c.apiRevision;delete c.features;for(const k of ['sum','rolling-mean','derivative','integral','overlay','compare','model'])delete c.ports[k];delete c.models;await route.fulfill({json:c})});await page.click('#reloadCatalog');await expect(page.locator('#catalogState')).toContainText('2.0');await page.fill('#blockSearch','compare');await expect(page.locator('#blockLibrary button')).toHaveCount(0);let posted=0;await page.route('**/api/math/scientific',r=>{posted++;return r.abort()});await page.click('#execute');await expect(page.locator('#status')).toContainText('UNSUPPORTED_OPERATION');expect(posted).toBe(0);await expect(page.locator('.node')).toHaveCount(7);
});
test('compound units are described by Math; incompatible formula units fail and recover',async({page})=>{
 test.skip(!process.env.MATH_REPO,'Requires pinned v2.1');await expect(page.locator('#catalogState')).toContainText('2.1');await add(page,'source');await page.fill('#editUnit','m');await page.click('#applyNode');await add(page,'formula');await page.fill('#editUnit','m^2');await page.fill('#editFormula','x^2');await page.click('#applyNode');await page.click('#describeUnit');await expect(page.locator('#unitDimensions')).toContainText('dimensions');await link(page,'n1','n2');await page.click('#execute');await expect(page.locator('#experiments article')).toHaveCount(1);await expect(page.locator('#experiments article')).toContainText('m^2');await page.fill('#editUnit','s');await page.click('#applyNode');await page.click('#execute');await expect(page.locator('#status')).toContainText('INVALID_SCIENTIFIC_REQUEST');await expect(page.locator('#experiments article')).toHaveCount(1);await page.fill('#editUnit','m^2');await page.click('#applyNode');await page.click('#execute');await expect(page.locator('#experiments article')).toHaveCount(2);
});
test('corrupted dependency digest and availability never enter experiment history',async({page})=>{
 test.skip(!process.env.MATH_REPO,'Requires pinned real Math');await add(page,'source');await add(page,'formula');await link(page,'n1','n2');await page.route('**/api/math/scientific',async route=>{const response=await route.fetch(),r=await response.json();r.trace.find(t=>t.node==='n2').dependencies[0].sha256='0'.repeat(64);await route.fulfill({json:r})});await page.click('#execute');await expect(page.locator('#status')).toContainText('DEPENDENCY_DIGEST_MISMATCH');await expect(page.locator('#experiments article')).toHaveCount(0);await page.unroute('**/api/math/scientific');await page.route('**/api/math/scientific',async route=>{const response=await route.fetch(),r=await response.json();r.outputs[0].availableAt[0]=120000;await route.fulfill({json:r})});await page.click('#execute');await expect(page.locator('#status')).toContainText('AVAILABILITY');await expect(page.locator('#experiments article')).toHaveCount(0);
});

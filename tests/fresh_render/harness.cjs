'use strict';
// Test tooling only. Explicit run is reserved for Root's separately admitted lane.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),http=require('node:http'),{execFileSync}=require('node:child_process');
const PINS=Object.freeze({renderer:'574dbf0882577708ab1e4c0ed73d6401eb6fabce3b3dc1b1375fc5952689241f',node:'d702daa815eabbff763c7d3808e235cf031cf2ca70211b56847bc72f51e240e5',lock:'ee92d25c969232c2b8190384efcbc0d07c56dc8ce42647ccb60dab27a0aa3132',packages:'3a122fd6006e045283967ee2c27f1122d77649db838162810ca746a416f9df3a',browsers:'1387ec667390e31e49040aa2c81d27720b38d32c7892d1a50c7f85b187e926c1',chromium:'ed19d88b4486c39c0265b0c07cbf1d6835d06069e600bede1adb09db0df46c8e'});
const LIMITS=Object.freeze({input:16384,renderer:65536,screenshot:4194304,json:65536,total_output:8519680,duration_ms:45000,close_ms:5000});
const rendererPath=path.resolve(__dirname,'../../terminan/target_adapter_result.js');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
function need(v,code){if(!v)throw Error(code);}
function inside(root,p){const r=path.relative(root,p);return r!==''&&!r.startsWith('..'+path.sep)&&r!=='..'&&!path.isAbsolute(r);}
function cleanAbsolute(p){need(typeof p==='string'&&path.isAbsolute(p)&&path.resolve(p)===p&&!p.includes('\0'),'PATH_ABSOLUTE_CANONICAL');if(process.platform==='win32')need(/^[A-Za-z]:\\/.test(p)&&!p.slice(2).includes(':'),'PATH_NO_UNC_OR_STREAM');return p;}
function ancestors(p){const out=[];for(let x=p;;x=path.dirname(x)){out.push(x);if(path.dirname(x)===x)return out;}}
function checkPaths(paths){
 const all=[...new Set(paths.flatMap(p=>ancestors(cleanAbsolute(p))))];
 for(const p of all){const s=fs.lstatSync(p);need(!s.isSymbolicLink(),'LINK_PATH');need(fs.realpathSync.native(p).toLowerCase()===p.toLowerCase(),'PATH_REALPATH');}
 if(process.platform==='win32'){
  const script='$ErrorActionPreference="Stop"; $paths=ConvertFrom-Json ([Console]::In.ReadToEnd()); foreach($p in $paths){if((Get-Item -LiteralPath $p -Force).Attributes -band [IO.FileAttributes]::ReparsePoint){exit 23}}';
  try{execFileSync(path.join(process.env.SystemRoot||'C:\\Windows','System32/WindowsPowerShell/v1.0/powershell.exe'),['-NoProfile','-NonInteractive','-EncodedCommand',Buffer.from(script,'utf16le').toString('base64')],{input:JSON.stringify(all),stdio:['pipe','pipe','pipe'],timeout:10000,maxBuffer:4096,env:{SystemRoot:process.env.SystemRoot||'C:\\Windows'}});}catch{throw Error('REPARSE_CHECK_FAILED');}
 }
 return all.map(p=>{const s=fs.lstatSync(p,{bigint:true});return [p,String(s.dev),String(s.ino)];});
}
function readBound(root,p,cap){
 cleanAbsolute(root);cleanAbsolute(p);need(inside(root,p),'PATH_OUTSIDE_ROOT');const before=checkPaths([root,p]);let fd;
 try{fd=fs.openSync(p,fs.constants.O_RDONLY|(fs.constants.O_NOFOLLOW||0));const a=fs.fstatSync(fd,{bigint:true});need(a.isFile(),'FILE_REQUIRED');need(a.nlink===1n,'LINK_COUNT');need(a.size>0n&&a.size<=BigInt(cap),'SIZE_LIMIT');const b=Buffer.alloc(Number(a.size));let n=0;while(n<b.length){const k=fs.readSync(fd,b,n,b.length-n,null);need(k>0,'FILE_SHORT_READ');n+=k;}const extra=Buffer.alloc(1);need(fs.readSync(fd,extra,0,1,null)===0,'SIZE_CHANGED');const z=fs.fstatSync(fd,{bigint:true}),actual=fs.lstatSync(p,{bigint:true});for(const k of ['dev','ino','size','mtimeNs','ctimeNs','nlink'])need(a[k]===z[k]&&a[k]===actual[k],'FILE_CHANGED');need(JSON.stringify(before)===JSON.stringify(checkPaths([root,p])),'PATH_CHANGED');return b;}finally{if(fd!==undefined)fs.closeSync(fd);}
}
function readPinned(p,cap,expected){const b=readBound(path.parse(p).root,p,cap);need(sha(b)===expected,'PIN_DIGEST');return b;}
async function prepare(spec){
 need(spec&&typeof spec==='object'&&spec.digests,'SPEC_REQUIRED');cleanAbsolute(spec.testRoot);need(fs.lstatSync(spec.testRoot).isDirectory(),'PATH_ROOT_DIRECTORY');
 const repo=path.resolve(__dirname,'../..');need(spec.testRoot!==repo&&!inside(repo,spec.testRoot),'PATH_TESTROOT_INSIDE_SOURCE');
 const raw={},digests={};for(const k of ['request','envelope','artifact']){need(/^[a-f0-9]{64}$/.test(spec.digests[k]),'DIGEST_FORMAT');raw[k]=readBound(spec.testRoot,spec[k],LIMITS.input);digests[k]=sha(raw[k]);need(digests[k]===spec.digests[k],'INPUT_DIGEST');}
 need(new Set(['request','envelope','artifact'].map(k=>spec[k])).size===3,'PATH_INPUT_ALIAS');
 const source=readPinned(rendererPath,LIMITS.renderer,PINS.renderer);const parsed=await require(rendererPath).parseTargetResult(raw.request.toString('utf8'),raw.envelope.toString('utf8'));
 need(parsed.status==='LOCAL_UNATTESTED'&&parsed.model,'RENDER_PREFLIGHT_'+parsed.error_code);
 const artifact=Buffer.from(canonical(parsed.model.envelope.result));need(raw.artifact.equals(artifact)&&digests.artifact===parsed.model.envelope.result_artifact_ref.sha256,'ARTIFACT_BYTES_MISMATCH');
 return Object.freeze({request:raw.request.toString('utf8'),envelope:raw.envelope.toString('utf8'),digests:Object.freeze(digests),model:parsed.model,source,scope:'LOCAL_UNATTESTED_FRESH_FILE_RENDER_NOT_PRODUCER_AUTH_OR_MARKET_VERIFICATION'});
}
function canonical(v){return v===null||typeof v!=='object'?JSON.stringify(v):Array.isArray(v)?'['+v.map(canonical).join(',')+']':'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}';}
function confirmInputs(spec,p){for(const k of ['request','envelope','artifact'])need(sha(readBound(spec.testRoot,spec[k],LIMITS.input))===p.digests[k],'FRESH_INPUT_CHANGED');}
const CSP="default-src 'none'; script-src 'self'; style-src 'unsafe-inline'; connect-src 'none'; img-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'";
function routeFor(p,method,url){
 const headers={'Content-Security-Policy':CSP,'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer'};let status=200,body,type;
 if(method!=='GET'){status=405;body='';}else if(url==='/'){type='text/html';body='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Disposable LOCAL_UNATTESTED fresh-file render</title><style>body{background:#101923;color:#deebf7;font:16px system-ui;margin:24px}main{max-width:1000px;margin:auto}</style><main></main><script src="/renderer.js"></script><script src="/packet.js"></script></html>';}else if(url==='/renderer.js'){type='text/javascript';body=p.source;}else if(url==='/packet.js'){type='text/javascript';body='"use strict";window.__freshDone=null;TerminanTargetResult.renderTargetResult(document.querySelector("main"),'+JSON.stringify(p.request).replaceAll('<','\\u003c')+','+JSON.stringify(p.envelope).replaceAll('<','\\u003c')+').then(r=>{window.__freshDone=r;},()=>{window.__freshDone={status:"UNAVAILABLE"};});';}else{status=404;body='';}
 headers['Content-Type']=(type||'text/plain')+'; charset=utf-8';return {status,headers,body:Buffer.isBuffer(body)?body:Buffer.from(body)};
}
function allowRequest(base,url,method){return method==='GET'&&['/','/renderer.js','/packet.js'].some(p=>url===base+p);}
const disabledFeatures='--disable-features=AcceptCHFrame,AvoidUnnecessaryBeforeUnloadCheckSync,DestroyProfileOnBrowserClose,DialMediaRouteProvider,GlobalMediaControls,HttpsUpgrades,LensOverlay,MediaRouter,PaintHolding,ThirdPartyStoragePartitioning,Translate,AutoDeElevate,RenderDocument';
function launchOptions(tmp,executablePath){
 return {headless:true,chromiumSandbox:true,host:'127.0.0.1',port:0,timeout:15000,executablePath,downloadsPath:tmp,tracesDir:tmp,
  ignoreDefaultArgs:['--disable-client-side-phishing-detection','--disable-ipc-flooding-protection','--disable-popup-blocking','--unsafely-disable-devtools-self-xss-warnings',disabledFeatures],
  args:['--disk-cache-dir='+path.join(tmp,'cache'),'--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE localhost'],
  env:{SystemRoot:process.env.SystemRoot||'C:\\Windows',WINDIR:process.env.WINDIR||'C:\\Windows',TEMP:tmp,TMP:tmp,TMPDIR:tmp,HOME:tmp,USERPROFILE:tmp,LOCALAPPDATA:tmp}};
}
function checkSpawn(args,tmp){
 need(Array.isArray(args)&&!args.some(a=>/^--(?:no-sandbox|disable-setuid-sandbox|disable-web-security|ignore-certificate-errors|allow-running-insecure-content|unsafely-|disable-(?:features|client-side-phishing-detection|ipc-flooding-protection|popup-blocking))/.test(a)),'SECURITY_SWITCH');
 const profile=args.filter(a=>a.startsWith('--user-data-dir='));need(profile.length===1&&inside(tmp,path.resolve(profile[0].slice('--user-data-dir='.length))),'PROFILE_OUTSIDE_TEMP');
 for(const prefix of ['--disk-cache-dir=','--crash-dumps-dir='])for(const a of args.filter(x=>x.startsWith(prefix)))need(inside(tmp,path.resolve(a.slice(prefix.length))),'PROFILE_OUTSIDE_TEMP');
}
function writeBound(root,name,bytes,cap){need(/^[a-z][a-z0-9.-]*$/.test(name),'OUTPUT_NAME');need(Buffer.isBuffer(bytes)&&bytes.length<=cap,'OUTPUT_SIZE');checkPaths([root]);fs.writeFileSync(path.join(root,name),bytes,{flag:'wx',mode:0o600});}
async function limited(p,ms){let timer;try{return await Promise.race([p,new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('DEADLINE')),ms);})]);}finally{clearTimeout(timer);}}
async function closeOwned(server){
 const child=server.process();need(child&&Number.isSafeInteger(child.pid)&&child.pid>0,'OWNED_PROCESS_REQUIRED');let fallback=false;
 try{await limited(server.close(),LIMITS.close_ms);}catch{fallback=true;await limited(server.kill(),LIMITS.close_ms);}
 return {pid:child.pid,confirmed:child.exitCode!==null||child.signalCode!==null,fallback_sdk_kill:fallback};
}
function dependencyTree(base){
 const rows=[];let total=0;for(const pkg of ['@playwright/test','playwright','playwright-core']){function visit(d){for(const e of fs.readdirSync(d,{withFileTypes:true})){const p=path.join(d,e.name),s=fs.lstatSync(p);need(!s.isSymbolicLink(),'DEPENDENCY_LINK');if(s.isDirectory())visit(p);else{need(s.isFile()&&s.nlink===1,'DEPENDENCY_FILE');total+=s.size;need(total<=268435456&&rows.length<2048,'DEPENDENCY_SIZE');rows.push([path.relative(base,p).split(path.sep).join('/'),sha(fs.readFileSync(p))]);}}}visit(path.join(base,pkg));}
 rows.sort((a,b)=>a[0]<b[0]?-1:a[0]>b[0]?1:0);need(rows.length===521&&sha(JSON.stringify(rows))===PINS.packages,'DEPENDENCY_TREE_DIGEST');return rows.length;
}
function moduleRoot(modulePath){cleanAbsolute(modulePath);const modules=path.resolve(modulePath,'../..');need(path.basename(modulePath)==='test'&&path.basename(path.dirname(modulePath))==='@playwright'&&path.basename(modules)==='node_modules','DEPENDENCY_PATH');return modules;}
function verifyTooling(modulePath,executable){
 need(process.version==='v24.22.1'&&process.execArgv.length===1&&process.execArgv[0]==='--no-addons','NODE_RUNTIME');
 for(const [k,v]of Object.entries(process.env))need(!v||!(/^(NODE_OPTIONS|NODE_PATH|NODE_COMPILE_CACHE|NODE_V8_COVERAGE|ELECTRON_RUN_AS_NODE|PW_|PLAYWRIGHT_|SELENIUM_|DEBUG$)/i.test(k)),'AMBIENT_RUNTIME_CONFIG');
 readPinned(process.execPath,134217728,PINS.node);cleanAbsolute(modulePath);cleanAbsolute(executable);checkPaths([modulePath,executable]);
 const modules=moduleRoot(modulePath);
 readPinned(path.resolve(modules,'../package-lock.json'),1048576,PINS.lock);readPinned(path.join(modules,'playwright-core/browsers.json'),65536,PINS.browsers);readPinned(executable,268435456,PINS.chromium);dependencyTree(modules);
 need(require(path.join(modulePath,'package.json')).version==='1.56.1','PLAYWRIGHT_VERSION');return modules;
}
async function run(spec,modulePath,executable){
 const p=await prepare(spec);verifyTooling(modulePath,executable);
 const runRoot=fs.mkdtempSync(path.join(spec.testRoot,'fresh-render-'));checkPaths([runRoot]);const tmp=path.join(runRoot,'temp');fs.mkdirSync(tmp);const prior={};for(const k of ['TEMP','TMP','TMPDIR']){prior[k]=process.env[k];process.env[k]=tmp;}
 let httpServer,browserServer,browser,cleanup=null,exitCode=1;const receipt={schema:'terminan.disposable.fresh-file-render.v1',scope:p.scope,input_sha256:p.digests,renderer_sha256:PINS.renderer,node:process.version,playwright:'1.56.1',chromium_revision:'1194',authenticated_gateway:false,verified_market_data:false,production_admission:false,hard_resource_containment:'NOT_QUALIFIED',browser_run:'STARTED',render:'NOT_RUN',cleanup:'PENDING',page_requests:0,blocked_page_requests:0};
 const deadline=Date.now()+LIMITS.duration_ms;
 const remaining=(cap=10000)=>{const ms=deadline-Date.now();need(ms>0,'DEADLINE');return Math.min(cap,ms);};
 try{
   httpServer=http.createServer({maxHeaderSize:4096},(req,res)=>{const r=routeFor(p,req.method,req.url);res.writeHead(r.status,r.headers);res.end(r.body);});httpServer.maxConnections=4;httpServer.requestTimeout=5000;httpServer.headersTimeout=5000;
   await new Promise((resolve,reject)=>{httpServer.once('error',reject);httpServer.listen(0,'127.0.0.1',resolve);});const base='http://127.0.0.1:'+httpServer.address().port;
   const {chromium}=require(modulePath);browserServer=await chromium.launchServer({...launchOptions(tmp,executable),timeout:remaining(15000)});const child=browserServer.process();
   writeBound(runRoot,'owned-browser.json',Buffer.from(JSON.stringify({schema:'terminan.owned-browser-process.v1',pid:child.pid,parent_pid:process.pid,ownership:'BrowserServer.process() issued by this launch only',run_root:runRoot})),LIMITS.json);checkSpawn(child.spawnargs,tmp);
   remaining();browser=await chromium.connect(browserServer.wsEndpoint(),{timeout:remaining()});const context=await limited(browser.newContext({viewport:{width:1280,height:900},serviceWorkers:'block',acceptDownloads:false}),remaining());
   await context.route('**/*',route=>{receipt.page_requests++;if(receipt.page_requests>32||!allowRequest(base,route.request().url(),route.request().method())){receipt.blocked_page_requests++;return route.abort('blockedbyclient');}return route.continue();});
   const page=await limited(context.newPage(),remaining());page.setDefaultTimeout(remaining());await page.goto(base+'/',{waitUntil:'load',timeout:remaining()});await page.waitForFunction(()=>window.__freshDone!==null,null,{timeout:remaining()});
   const observed=await limited(page.evaluate(()=>({status:window.__freshDone.status,model:window.__freshDone.model,banner:document.querySelector('[role="status"]')?.textContent,tables:[...document.querySelectorAll('table tbody')].map(x=>x.rows.length),cells:[...document.querySelectorAll('table tbody')].map(x=>[...x.rows].map(r=>[...r.cells].map(c=>c.textContent))),forbidden:document.querySelectorAll('a,img,iframe,button,input,svg,canvas').length})),remaining());
   need(observed.status==='LOCAL_UNATTESTED'&&canonical(observed.model)===canonical(p.model),'RENDER_MODEL_MISMATCH');need(observed.banner==='LOCAL_UNATTESTED · BYTE AGREEMENT ONLY'&&JSON.stringify(observed.tables)==='[4,3]'&&observed.forbidden===0,'RENDER_DOM_MISMATCH');need(receipt.blocked_page_requests===0,'UNEXPECTED_BROWSER_REQUEST');
   const r=p.model.envelope.result,expectedCells=[r.levels.map(x=>[x.kind,x.price,String(x.source_start_ms)]),r.rows.map(x=>[x.event_start_ms,x.open,x.high,x.low,x.close,x.volume].map(String))];need(JSON.stringify(observed.cells)===JSON.stringify(expectedCells),'RENDER_CELLS_MISMATCH');
   const screenshot=await page.screenshot({type:'png',fullPage:false,timeout:remaining()});writeBound(runRoot,'fresh-render.png',screenshot,LIMITS.screenshot);
   confirmInputs(spec,p);remaining();receipt.screenshot_sha256=sha(screenshot);receipt.rendered_model_sha256=sha(canonical(observed.model));receipt.render='LOCAL_UNATTESTED_MODEL_AND_DOM_AGREEMENT';receipt.levels=4;receipt.input_rows=3;await limited(context.close(),remaining());exitCode=0;
 }catch(e){receipt.failure_code=/^[A-Z][A-Z0-9_]{0,95}$/.test(e.message)?e.message:'HARNESS_FAILED_DETAILS_WITHHELD';}
 finally{
  // BrowserServer.close/kill are the only process-termination capabilities used.
  if(browserServer){try{cleanup=await closeOwned(browserServer);}catch{cleanup={confirmed:false};}}else cleanup={confirmed:false,reason:'NO_ISSUED_BROWSER_HANDLE'};
  if(httpServer){httpServer.closeAllConnections();await limited(new Promise(resolve=>httpServer.close(resolve)),5000).catch(()=>{exitCode=1;});}
  receipt.cleanup=cleanup;receipt.browser_run='FINISHED';if(!cleanup.confirmed)exitCode=1;receipt.result=exitCode===0?'LOCAL_RENDER_PASS_NOT_AUTH_OR_PHYSICAL_ACCEPTANCE':'FAIL_OR_UNCONFIRMED';
  for(const k of ['TEMP','TMP','TMPDIR']){if(prior[k]===undefined)delete process.env[k];else process.env[k]=prior[k];}
  writeBound(runRoot,'render-receipt.json',Buffer.from(JSON.stringify(receipt,null,2)+'\n'),LIMITS.json);
 }
 return {runRoot,exitCode,receipt};
}
async function cli(args){
 if(args[0]==='tooling'){need(args.length===3,'USAGE');const modules=verifyTooling(args[1],args[2]);need(!require.cache[require.resolve(args[1])],'SDK_ALREADY_IMPORTED');console.log(JSON.stringify({modules,browser_run:'NOT_RUN'}));return;}
 need(args.length===9||args.length===11,'USAGE');const [mode,testRoot,request,envelope,artifact,r,e,a,...extra]=args;
 // Eight input arguments, plus mode; expected digests are Root-selected facts.
 need(mode==='preflight'||mode==='run','USAGE');const spec={testRoot,request,envelope,artifact,digests:{request:r,envelope:e,artifact:a}};
 if(mode==='preflight'){need(extra.length===1&&extra[0]==='NO_BROWSER','USAGE');const p=await prepare(spec);console.log(JSON.stringify({scope:p.scope,input_sha256:p.digests,browser_run:'NOT_RUN'}));return;}
 need(extra.length===3&&extra[0]==='ROOT_SERIAL_LANE','USAGE');const result=await run(spec,extra[1],extra[2]);console.log(JSON.stringify({run_root:result.runRoot,result:result.receipt.result}));process.exitCode=result.exitCode;
}
module.exports={PINS,LIMITS,prepare,readBound,routeFor,allowRequest,launchOptions,checkSpawn,writeBound,closeOwned,moduleRoot,confirmInputs,verifyTooling};
if(require.main===module)cli(process.argv.slice(2)).catch(e=>{console.error('FRESH_RENDER_REFUSED:'+(/^[A-Z][A-Z0-9_]{0,95}$/.test(e.message)?e.message:'DETAILS_WITHHELD'));process.exitCode=1;});

'use strict';
// SOURCE PREPARATION ONLY until Root approves this exact unit manifest.
// Actual renderer/protocol text; inert DOM/RAF/timers and SYNTHETIC response DATA.
// Not a browser, TLS/session/native identity, scientific READ or workload benchmark.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const ROOT=path.resolve(__dirname,'..');
const IDS=Object.freeze([
  'r2_metrics_count_held_benchmark_raf',
  'r2_dispose_settles_held_benchmark_without_frame',
  'r2_seek_settles_superseded_benchmark_without_frame',
  'r4_metrics_count_held_benchmark_raf',
  'r4_dispose_settles_held_benchmark_without_frame',
  'r4_seek_settles_superseded_benchmark_without_frame',
]);
const SHA='a'.repeat(40),SESSION='b'.repeat(32);
const clone=value=>JSON.parse(JSON.stringify(value));
async function microtasks(){for(let i=0;i<32;i++)await Promise.resolve();}
class Element{
  constructor(id=''){this.id=id;this.value='';this.dataset={};this.children=[];this.listeners=new Map();this.width=0;this.height=0;this.clientWidth=0;this.clientHeight=0;this.scrollHeight=0;this.scrollTop=0;this.offsetTop=0;this.className='';this._text='';this.classList={add:()=>{}};}
  addEventListener(name,fn){if(!this.listeners.has(name))this.listeners.set(name,new Set());this.listeners.get(name).add(fn);}
  removeEventListener(name,fn){this.listeners.get(name)?.delete(fn);}
  append(...nodes){this.children.push(...nodes);}
  replaceChildren(...nodes){this.children=[...nodes];this._text='';}
  set textContent(value){this._text=String(value);this.children=[];}
  get textContent(){return this._text+this.children.map(x=>x.textContent||'').join('');}
  set innerHTML(_){throw Error('UNIT_HTML_FORBIDDEN');}
  closest(){return this;}
  querySelector(){return null;}
  getBoundingClientRect(){return {left:0,top:0,width:0,height:0};}
  setPointerCapture(){throw Error('UNIT_POINTER_INPUT_NOT_ALLOCATED');}
  getContext(){return {clearRect(){}};} // Hidden layout: no drawing API is exercised.
}
function fixture(step){
  return {mode:'SYNTHETIC',authority:'SYNTHETIC_ONLY',symbol:'BTCUSDT',timeframe:'1m',step,
    candidate_sha:SHA,frame_sha256:'c'.repeat(64),dataset_id:'UNIT_SYNTHETIC',period_ms:60000,as_of_ms:60000,
    candles:[{t:0,o:100,h:101,l:99,c:100,v:1,complete:true}],events:[],
    source_state:'SYNTHETIC',dom:{status:'COHERENT',bids:[],asks:[],tick_size:1,epoch:1,sequence:1},
    footprint:{rows:[],poc:null},session:receipt()};
}
function receipt(){return {version:1,mode:'SYNTHETIC',session_id:SESSION,candidate_sha:SHA,epoch:1,revision:1,
  state:'ACTIVE',lease_ms:5000,poll_ms:500,end_grace_ms:3000,authority:'SYNTHETIC_ONLY',sources:'DISABLED'};}
async function harness(kind){
  const elements=new Map(),element=id=>{if(!elements.has(id))elements.set(id,new Element(id));return elements.get(id);};
  for(const [id,value] of Object.entries({symbol:'BTCUSDT',timeframe:'1m',seed:'17',seek:'0',scenario:'normal'}))element(id).value=value;
  const document={body:new Element('body'),getElementById:element,createElement:tag=>new Element(tag),createDocumentFragment:()=>new Element('fragment'),querySelectorAll:()=>[]};
  document.body.dataset.runtime='unified';
  const raf=new Map(),timers=new Map(),requests=[];let serial=0,now=0;
  const window=new Element('window');
  function later(fn,delay){assert.equal(typeof fn,'function');assert.ok(Number.isFinite(delay)&&delay>=0);const id=++serial;timers.set(id,fn);return id;}
  async function fetchData(route,options={}){
    assert.equal(typeof route,'string');assert.ok(requests.length<8,'UNIT_REQUEST_CAP');
    assert.ok(options.signal instanceof AbortSignal);requests.push(route);
    // Closed string parsing only; no URL/HTTP/socket/Response implementation.
    const [name,query='']=route.split('?');const params=new URLSearchParams(query);
    let data;
    if(name==='/api/synthetic/status'&&kind==='r4')data={mode:'SYNTHETIC',sources:'DISABLED',execution:'DISABLED',source_clean:true,candidate_sha:SHA};
    else if(name==='/api/session'&&kind==='r4'&&!query)data=receipt();
    else if(name==='/api/synthetic/frame'||name==='/api/synthetic/contracts'){
      assert.deepEqual([...params.keys()].sort(),['scenario','seed','step','symbol','timeframe']);
      assert.equal(params.get('symbol'),'BTCUSDT');assert.equal(params.get('timeframe'),'1m');
      assert.equal(params.get('seed'),'17');assert.equal(params.get('scenario'),'normal');
      assert.ok(['0','1'].includes(params.get('step')));
      data=name.endsWith('/frame')?fixture(Number(params.get('step'))):{sources:[],candidate_sha:SHA,symbol:'BTCUSDT',timeframe:'1m',session:receipt()};
    }else throw Error('UNIT_ROUTE_NOT_ALLOCATED');
    return {ok:true,json:async()=>clone(data),text:async()=>JSON.stringify(data)};
  }
  const sandbox={window,document,devicePixelRatio:1,AbortController,AbortSignal,URLSearchParams,
    performance:{now:()=>now},fetch:fetchData,
    requestAnimationFrame:fn=>{assert.equal(typeof fn,'function');assert.ok(raf.size<4,'UNIT_RAF_CAP');const id=++serial;raf.set(id,fn);return id;},
    cancelAnimationFrame:id=>raf.delete(id),setTimeout:later,clearTimeout:id=>timers.delete(id),
    ResizeObserver:class{observe(){}disconnect(){}},
    console:new Proxy({}, {get(){throw Error('UNIT_LOG_FORBIDDEN');}})};
  // A VM realm is an execution seam for trusted exact project text, not a hostile-code sandbox.
  vm.createContext(sandbox);
  if(kind==='r4'){
    vm.runInContext(fs.readFileSync(path.join(ROOT,'terminan/r4_protocol.js'),'utf8'),sandbox,{filename:'terminan/r4_protocol.js',timeout:1000});
    sandbox.R4SessionClient=window.R4SessionClient;
  }
  vm.runInContext(fs.readFileSync(path.join(ROOT,`terminan/${kind}_preview.js`),'utf8'),sandbox,{filename:`terminan/${kind}_preview.js`,timeout:1000});
  await microtasks();
  assert.equal(window.r2.metrics().activeRequests,0,'UNIT_BOOTSTRAP_NOT_SETTLED');
  assert.equal(window.r2.metrics().retainedCandles,1,'UNIT_MODEL_NOT_LOADED');
  assert.equal(raf.size,1,'UNIT_EXPECTED_ONE_INITIAL_RENDER');
  function frame(){const batch=[...raf];raf.clear();now+=16;for(const [,fn] of batch)fn(now);}
  frame();await microtasks();assert.equal(raf.size,0);
  assert.equal(window.r2.metrics().renders,1);
  return {api:window.r2,raf,timers,requests,
    watch(){let result=null;const before=raf.size,promise=window.r2.benchmark({updates:10000,batch:100,seed:17});
      promise.then(value=>{result={kind:'resolved',value};},error=>{result={kind:'rejected',message:error.message};});
      assert.equal(raf.size,before+1,'UNIT_BENCHMARK_NOT_HELD');return {result:()=>result};},
    async cleanup(){
      window.r2.dispose();
      // Test-only teardown AFTER assertions: deliver obsolete callbacks so old-source
      // failures do not retain a promise. Never used as proof of prompt cancellation.
      const obsolete=[...raf.values()];raf.clear();for(const fn of obsolete)fn(now);
      await microtasks();timers.clear();
    }};
}
for(const [offset,kind] of [[0,'r2'],[3,'r4']]){
  test(IDS[offset],{timeout:2000},async t=>{
    const h=await harness(kind);t.after(()=>h.cleanup());h.watch();
    assert.equal(h.api.metrics().rafPending,h.raf.size,'METRICS_OMIT_BENCHMARK_RAF');
  });
  test(IDS[offset+1],{timeout:2000},async t=>{
    const h=await harness(kind);t.after(()=>h.cleanup());const pending=h.watch();
    h.api.dispose();await microtasks();
    assert.deepEqual(pending.result(),{kind:'rejected',message:'Benchmark cancelled'},'DISPOSE_MUST_SETTLE_WITHOUT_DELIVERING_FRAME');
    assert.equal(h.raf.size,0,'DISPOSE_LEFT_SCHEDULER_ENTRY');
    assert.equal(h.api.metrics().rafPending,0);assert.equal(h.api.metrics().listeners,0);
    assert.equal(h.api.metrics().activeRequests,0);
  });
  test(IDS[offset+2],{timeout:2000},async t=>{
    const h=await harness(kind);t.after(()=>h.cleanup());const pending=h.watch();
    await h.api.seek(1);await microtasks();
    assert.deepEqual(pending.result(),{kind:'rejected',message:'Benchmark cancelled'},'SEEK_MUST_SETTLE_WITHOUT_DELIVERING_OLD_FRAME');
    assert.equal(h.raf.size,1,'ONLY_NEW_GENERATION_RENDER_MAY_REMAIN');
    assert.equal(h.api.metrics().rafPending,1);assert.equal(h.api.metrics().renders,1);
    const recovery=h.watch();h.api.dispose();await microtasks();
    assert.deepEqual(recovery.result(),{kind:'rejected',message:'Benchmark cancelled'},'RECOVERY_LOCK_MUST_BE_RELEASED');
    assert.equal(h.raf.size,0);
  });
}

/* Synthetic-only demand-driven rendering. No live/DB/order routes. */
'use strict';
(()=>{
const $=id=>document.getElementById(id), canvas=$('chart'), ctx=canvas.getContext('2d');
let sessionClient=null,terminalState='';
const s={startupController:null,fetchSamples:[],retry:0,retryTimer:0,data:null,contracts:null,generation:0,controller:null,playing:false,timer:0,raf:0,disposed:false,
  start:0,end:0,identity:'',modelDirty:true,drag:null,active:0,peak:0,aborted:0,renders:0,samples:[],renderTimes:[],listeners:[],firstRender:performance.now()};
function on(target,event,fn,opts){target.addEventListener(event,fn,opts);s.listeners.push(()=>target.removeEventListener(event,fn,opts));}
function schedule(){if(!s.disposed&&!s.raf)s.raf=requestAnimationFrame(render);}
function text(id,value){$(id).textContent=value;}
function row(values,classes=[]){const tr=document.createElement('tr');values.forEach((value,i)=>{const td=document.createElement('td');td.textContent=value;if(classes[i])td.className=classes[i];tr.append(td);});return tr;}
function clearPanels(){
  s.data=null;s.contracts=null;s.modelDirty=true;
  for(const id of ['book-body','footprint-body','contracts'])$(id).replaceChildren();
  text('book-state','AWAITING');text('source-state','LOADING');text('chart-empty','Loading selected synthetic identity…');
  text('book-meta','Previous data cleared');text('footprint-time','Waiting for selected data');
  text('chart-inspect','Wheel to zoom · drag to pan · double-click to reset');
  ctx.clearRect(0,0,canvas.width,canvas.height);
}
function resetView(){
  if(!s.data?.candles.length)return;
  const rows=s.data.candles,period=s.data.period_ms;
  s.end=rows.at(-1).t+period;s.start=Math.max(rows[0].t,s.end-80*period);schedule();
}
function clampView(){
  if(!s.data?.candles.length)return;
  const rows=s.data.candles,period=s.data.period_ms,min=rows[0].t,max=rows.at(-1).t+period;
  const span=Math.min(max-min,Math.max(10*period,s.end-s.start));
  s.end=Math.max(min+span,Math.min(max,s.end));s.start=s.end-span;
}
function zoom(factor,anchor=.5){
  if(!s.data?.candles.length)return;
  const center=s.start+(s.end-s.start)*anchor,span=(s.end-s.start)*factor;
  s.start=center-span*anchor;s.end=center+span*(1-anchor);clampView();schedule();
}
function drawChart(){
  const w=canvas.clientWidth,h=canvas.clientHeight,dpr=Math.min(3,devicePixelRatio||1);
  if(canvas.width!==Math.round(w*dpr)||canvas.height!==Math.round(h*dpr)){canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);}
  ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);
  const rows=s.data?.candles.filter(r=>r.t+s.data.period_ms>s.start&&r.t<s.end)||[];
  if(!rows.length){text('chart-empty',document.body.dataset.loading==='true'?'Loading selected synthetic identity…':'No synthetic rows · see source state');return;}
  text('chart-empty','');
  const left=8,right=w-62,top=14,bottom=h-26;
  const hi=Math.max(...rows.map(r=>r.h)),lo=Math.min(...rows.map(r=>r.l)),pad=Math.max((hi-lo)*.08,.01);
  const y=value=>top+(hi+pad-value)/(hi-lo+2*pad)*(bottom-top);
  const x=t=>left+(t-s.start)/(s.end-s.start)*(right-left);
  ctx.font='10px Segoe UI';ctx.strokeStyle='#263449';ctx.fillStyle='#879bb7';
  for(let i=0;i<=4;i++){
    const py=top+(bottom-top)*i/4,price=hi+pad-(hi-lo+2*pad)*i/4;
    ctx.beginPath();ctx.moveTo(left,py);ctx.lineTo(right,py);ctx.stroke();ctx.fillText(price.toFixed(2),right+7,py+3);
    const stamp=s.start+(s.end-s.start)*i/4;
    ctx.fillText(new Date(stamp).toISOString().slice(11,16),left+(right-left)*i/4-10,h-8);
  }
  const width=Math.max(1,Math.min(16,(right-left)*s.data.period_ms/(s.end-s.start)*.65));
  ctx.save();ctx.beginPath();ctx.rect(left,top,right-left,bottom-top);ctx.clip();
  for(const r of rows){
    const px=x(r.t+s.data.period_ms/2);ctx.strokeStyle=ctx.fillStyle=r.c>=r.o?'#47c5a6':'#ed8495';
    ctx.globalAlpha=r.complete?1:.55;ctx.beginPath();ctx.moveTo(px,y(r.h));ctx.lineTo(px,y(r.l));ctx.stroke();
    ctx.fillRect(px-width/2,Math.min(y(r.o),y(r.c)),width,Math.max(1,Math.abs(y(r.o)-y(r.c))));
  }
  ctx.restore();ctx.globalAlpha=1;
}
function drawPanels(){
  if(!s.data)return;
  const d=s.data;
  text('chart-title',d.symbol+' · '+d.timeframe);text('clock',new Date(d.as_of_ms).toISOString().replace('T',' ').replace('.000Z',' UTC'));
  text('identity',d.dataset_id+' · step '+d.step);
  text('book-state',d.dom.status);$('book-state').dataset.fault=String(d.dom.status!=='COHERENT');
  text('source-state',d.source_state);$('source-state').dataset.fault=String(d.source_state!=='SYNTHETIC');
  const bids=new Map(d.dom.bids),asks=new Map(d.dom.asks);
  const prices=[...new Set([...bids.keys(),...asks.keys()])].sort((a,b)=>b-a);
  const book=document.createDocumentFragment();
  prices.forEach(price=>book.append(row([bids.get(price)||'',(price*d.dom.tick_size).toFixed(2),asks.get(price)||''],['bid','','ask'])));
  $('book-body').replaceChildren(book);
  const scroll=$('book-body').closest('.book-scroll');
  scroll.scrollTop=Math.max(0,(scroll.scrollHeight-scroll.clientHeight)/2);
  text('book-meta','epoch '+d.dom.epoch+' · sequence '+d.dom.sequence+' · '+prices.length+' bounded rows');
  const footprint=document.createDocumentFragment();
  d.footprint.rows.forEach(r=>{const tr=row([r.price.toFixed(2),r.buy,r.sell,r.delta,r.volume]);if(r.price===d.footprint.poc)tr.className='poc';footprint.append(tr);});
  $('footprint-body').replaceChildren(footprint);
  text('footprint-time',d.footprint.rows.length?new Date(d.footprint.rows[0].t).toISOString()+' · closed minute · SYNTHETIC · POC '+d.footprint.poc.toFixed(2):'No available synthetic footprint');
  const contracts=document.createDocumentFragment();
  for(const c of s.contracts?.sources||[]){
    const div=document.createElement('div');div.className='contract';
    const label=document.createElement('div'),title=document.createElement('strong'),sub=document.createElement('small'),state=document.createElement('span');
    title.textContent=(c.source||'Source')+' / '+(c.kind||'contract');
    sub.textContent='SYNTHETIC fixture '+(c.symbol||'REJECTED_IDENTITY')+' '+(c.timeframe||'research')+' · '+(c.provenance?.source_sha?.slice(0,10)||'rejected')+' · runtime NONE';
    label.append(title,sub);state.textContent=c.state;state.className='pill';div.append(label,state);contracts.append(div);
  }
  $('contracts').replaceChildren(contracts);
  text('events',d.events.length?d.events.map(e=>'['+e.step+'] '+e.event).join('  ·  '):'Bounded deterministic replay · no fault events at this position.');
  $('seek').value=d.step;text('position',d.step+' / 600');
  text('source-sha','Candidate '+(d.candidate_sha||'UNVERIFIED').slice(0,12)+' · frame '+d.frame_sha256.slice(0,10));
  document.body.dataset.identity=d.symbol+'|'+d.timeframe;document.body.dataset.step=String(d.step);
}
function render(now){
  s.raf=0;if(s.disposed)return;
  const start=performance.now();drawChart();if(s.modelDirty){drawPanels();s.modelDirty=false;}
  s.renders++;s.samples.push(performance.now()-start);if(s.samples.length>240)s.samples.shift();
  s.renderTimes.push(now);if(s.renderTimes.length>240)s.renderTimes.shift();
  const avg=s.samples.reduce((a,b)=>a+b,0)/s.samples.length;
  text('performance','Demand-driven frames '+s.renders+' · avg draw '+avg.toFixed(2)+' ms · requests '+s.active+' / peak '+s.peak+' · replay target 4 updates/s');
  if(s.data)document.body.dataset.loading='false';
}
async function load(step=Number($('seek').value)){
  if(s.disposed||sessionClient?.state!=='ACTIVE')return;
  if(s.retryTimer){clearTimeout(s.retryTimer);s.retryTimer=0;}
  if(s.timer){clearTimeout(s.timer);s.timer=0;}
  if(s.controller){if(s.active)s.aborted++;s.controller.abort();}
  const generation=++s.generation,controller=new AbortController();s.controller=controller;
  const identity=$('symbol').value+'|'+$('timeframe').value;
  const previous=s.data?.candles,follow=previous?.length&&s.end>=previous.at(-1).t+s.data.period_ms;
  document.body.dataset.loading='true';document.body.dataset.identity='';text('error','');clearPanels();schedule();
  const query=new URLSearchParams({seed:$('seed').value,step:String(step),symbol:$('symbol').value,timeframe:$('timeframe').value,scenario:$('scenario').value});
  const timeout=setTimeout(()=>controller.abort(),10000);
  async function request(route){
    s.active++;s.peak=Math.max(s.peak,s.active);
    const began=performance.now();try{const response=await fetch(route+'?'+query,{signal:controller.signal});const data=await response.json();if(generation!==s.generation||s.disposed)throw Error('SUPERSEDED');if(data.session&&!sessionClient.accept(data.session))throw Error('SESSION_ENDED');if(!response.ok)throw Error(data.error||'Synthetic request failed');return data;}
    finally{s.fetchSamples.push(performance.now()-began);if(s.fetchSamples.length>240)s.fetchSamples.shift();s.active--;}
  }
  try{
    const [data,contracts]=await Promise.all([request('/api/synthetic/frame'),request('/api/synthetic/contracts')]);
    if(generation!==s.generation||s.disposed)return;
    if(data.mode!=='SYNTHETIC'||data.authority!=='SYNTHETIC_ONLY'||data.step!==step||data.candidate_sha!==sessionClient.sha||!data.session||!contracts.session||contracts.candidate_sha!==sessionClient.sha||contracts.symbol+'|'+contracts.timeframe!==identity||data.symbol+'|'+data.timeframe!==identity)throw Error('Synthetic identity mismatch');
    s.retry=0;s.data=data;s.contracts=contracts;s.modelDirty=true;
    if(s.identity!==identity||!s.start){s.identity=identity;resetView();}else{
      if(follow&&data.candles.length){const span=s.end-s.start;s.end=data.candles.at(-1).t+data.period_ms;s.start=s.end-span;}
      clampView();
    }
    schedule();
  }catch(error){
    if(generation!==s.generation||s.disposed)return;
    controller.abort(); // Promise.all failure must also cancel its sibling.
    if(error.message?.startsWith('RECEIPT_')||error.message==='Synthetic identity mismatch'){terminal('UNVERIFIED');return;}
    text('source-state','ERROR');$('source-state').dataset.fault='true';text('book-state','DISCONNECTED');
    text('error','Synthetic fetch unavailable  -  bounded retry '+(s.retry+1)+' / 5');
    if(++s.retry<5&&sessionClient.state==='ACTIVE'){const retryGeneration=s.generation;s.retryTimer=setTimeout(()=>{s.retryTimer=0;if(retryGeneration===s.generation&&!s.disposed)load(step);},[250,500,1000,2000][s.retry-1]);}
    text('chart-empty','Synthetic data unavailable');document.body.dataset.loading='false';s.playing=false;updatePlay();
  }finally{
    clearTimeout(timeout);
    if(generation===s.generation&&s.playing&&!s.disposed){
      if(step>=600){s.playing=false;updatePlay();}
      else s.timer=setTimeout(()=>{s.timer=0;load(step+1);},250);
    }
  }
}
function updatePlay(){text('play',s.playing?'Ⅱ Pause':'▶ Play');}
function stop(){s.playing=false;if(s.retryTimer){clearTimeout(s.retryTimer);s.retryTimer=0;}if(s.timer){clearTimeout(s.timer);s.timer=0;}updatePlay();}
on($('play'),'click',()=>{s.playing=!s.playing;updatePlay();if(s.playing)load(Number($('seek').value));else if(s.timer){clearTimeout(s.timer);s.timer=0;}});
on($('step-once'),'click',()=>{stop();load(Math.min(600,Number($('seek').value)+1));});
on($('restart'),'click',()=>{stop();load(0);});
for(const id of ['symbol','timeframe','seed','scenario'])on($(id),'change',()=>{stop();load(Number($('seek').value));});
on($('seek'),'input',()=>{stop();load(Number($('seek').value));});
on($('zoom-in'),'click',()=>zoom(.75));on($('zoom-out'),'click',()=>zoom(1.35));on($('reset-view'),'click',resetView);
on(canvas,'dblclick',resetView);
on(canvas,'wheel',event=>{event.preventDefault();const rect=canvas.getBoundingClientRect();zoom(event.deltaY<0?.85:1.18,Math.max(0,Math.min(1,(event.clientX-rect.left)/rect.width)));},{passive:false});
on(canvas,'pointerdown',event=>{if(!s.data)return;s.drag={x:event.clientX,start:s.start,end:s.end};canvas.setPointerCapture(event.pointerId);});
on(canvas,'pointermove',event=>{
  if(!s.drag){
    if(!s.data?.candles.length)return;
    const rect=canvas.getBoundingClientRect(),stamp=s.start+(event.clientX-rect.left-8)/(rect.width-70)*(s.end-s.start);
    const c=s.data.candles.find(c=>c.t<=stamp&&stamp<c.t+s.data.period_ms);
    if(c)text('chart-inspect',new Date(c.t).toISOString().slice(11,16)+' UTC · O '+c.o.toFixed(2)+' H '+c.h.toFixed(2)+' L '+c.l.toFixed(2)+' C '+c.c.toFixed(2)+' V '+c.v+(c.complete?' · closed':' · partial'));
    return;
  }
  const shift=(event.clientX-s.drag.x)/canvas.clientWidth*(s.drag.end-s.drag.start);s.start=s.drag.start-shift;s.end=s.drag.end-shift;clampView();schedule();
});
on(canvas,'pointerup',()=>{s.drag=null;});on(canvas,'pointercancel',()=>{s.drag=null;});
on(window,'resize',schedule);
const observer=new ResizeObserver(schedule);observer.observe(canvas);
function metrics(){
  const n=s.renderTimes.length,elapsed=n>1?(s.renderTimes.at(-1)-s.renderTimes[0])/1000:0;
  const sorted=[...s.samples].sort((a,b)=>a-b);
  const percentile=(v,p)=>{const a=[...v].sort((x,y)=>x-y);return a[Math.max(0,Math.ceil(a.length*p)-1)]||0;};
  return {session:sessionClient?.metrics()||{state:terminalState||'UNVERIFIED',closed:s.disposed,pending:0,active:0,requests:0,retries:0},startupPending:Number(Boolean(s.startupController&&!s.startupController.signal.aborted)),fetchLatencyMs:{p50:percentile(s.fetchSamples,.5),p95:percentile(s.fetchSamples,.95),p99:percentile(s.fetchSamples,.99)},fetchSamples:s.fetchSamples.length,fetchClock:'PERFORMANCE_NOW_REQUEST_TO_SETTLED',retryPending:Number(Boolean(s.retryTimer)),renders:s.renders,avgRenderMs:s.samples.length?s.samples.reduce((a,b)=>a+b,0)/s.samples.length:0,
    p95RenderMs:sorted.length?sorted[Math.min(sorted.length-1,Math.floor(sorted.length*.95))]:0,
    effectiveRenderFps:elapsed?(n-1)/elapsed:0,renderSamples:s.samples.length,retainedCandles:s.data?.candles.length||0,
    retainedEvents:s.data?.events.length||0,activeRequests:s.active,peakRequests:s.peak,aborted:s.aborted,
    rafPending:Number(Boolean(s.raf)),timerPending:Number(Boolean(s.timer)),listeners:s.listeners.length,
    dpr:devicePixelRatio,spanMs:s.end-s.start,windowEnd:s.end,bookRows:$('book-body').children.length,fixtureCount:s.contracts?.sources.length||0};
}
function dispose(){
  if(s.disposed)return;stop();sessionClient?.close();s.startupController?.abort();s.disposed=true;++s.generation;s.controller?.abort();
  if(s.raf)cancelAnimationFrame(s.raf);s.raf=0;observer.disconnect();
  s.listeners.forEach(remove=>remove());s.listeners=[];clearPanels();s.samples=[];s.renderTimes=[];
}
// R3 bounded synthetic renderer workload. No source access; final state deterministic.
let benchmarkRunning=false;
async function benchmark({updates=10000,batch=100,seed=17}={}){
  if(![10000,100000].includes(updates)||!Number.isInteger(batch)||batch<100||batch>500||!Number.isInteger(seed)||seed<0||seed>2147483647)throw Error('Invalid benchmark');
  if(s.disposed||!s.data||s.active)throw Error('Model unavailable');
  if(benchmarkRunning)throw Error('Benchmark already running');
  benchmarkRunning=true;try {
  stop();const generation=s.generation,identity=s.identity,started=performance.now();
  let checksum=seed>>>0,processed=0,frames=0,previous=0;
  const latency=[],intervals=[],draw=[];
  while(processed<updates){
    await new Promise(resolve=>requestAnimationFrame(resolve));
    if(s.disposed||s.generation!==generation||s.identity!==identity)throw Error('Benchmark cancelled');
    const begin=performance.now();
    for(let i=0;i<batch&&processed<updates;i++,processed++){
      checksum=(Math.imul(checksum,1664525)+1013904223)>>>0;
      const c=s.data.candles.at(-1);c.c=c.o+(checksum%101-50)/100;c.h=Math.max(c.h,c.c);c.l=Math.min(c.l,c.c);
    }
    s.modelDirty=true;
    // Use the same renderer as normal market updates, coalescing each ingress batch.
    if(s.raf){cancelAnimationFrame(s.raf);s.raf=0;}
    const now=performance.now();render(now);frames++;
    latency.push(performance.now()-begin);draw.push(s.samples.at(-1));
    if(previous)intervals.push(now-previous);previous=now;
  }
  const percentile=(values,p)=>{const v=[...values].sort((a,b)=>a-b);return v[Math.min(v.length-1,Math.ceil(v.length*p)-1)]||0;};
  const quantiles=v=>({p50:percentile(v,.5),p95:percentile(v,.95),p99:percentile(v,.99)});
  const elapsedMs=performance.now()-started;
  return {version:1,mode:'SYNTHETIC',authority:'SYNTHETIC_ONLY',seed,updates:processed,batch,checksum,frames,elapsedMs,
    updatesPerSecond:processed*1000/elapsedMs,renderCadenceFps:(frames-1)*1000/intervals.reduce((a,b)=>a+b,0),
    latencyScope:'BATCH_INGRESS_TO_RENDER_COMPLETE_NOT_PRESENTATION',latencyMs:quantiles(latency),drawMs:quantiles(draw),
    frameIntervalMs:quantiles(intervals),samples:latency.length,sampleScope:'WHOLE_WORKLOAD_MAX_1000_FRAMES',metrics:metrics()};
  }finally{benchmarkRunning=false;}
}
function terminal(state){
 terminalState=state;dispose();text('session-state',state);text('source-state',state);text('book-state',state);text('error','');text('chart-empty',state==='SESSION_ENDED'?'Synthetic session ended normally':'View stopped  -  reload to start a new view');document.body.dataset.loading='false';
 for(const input of document.querySelectorAll('.toolbar input,.toolbar select,.toolbar button,#seek'))input.disabled=true;
}
on($('close-view'),'click',()=>terminal('VIEW_CLOSED'));on(window,'pagehide',()=>terminal('VIEW_CLOSED'));
window.r2={benchmark,seek:step=>{stop();return load(step);},metrics,dispose};
window.r4={metrics,close:()=>terminal('VIEW_CLOSED')};
async function start(){
 try{
  const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),1500);
  s.startupController=controller;let status;try{const response=await fetch('/api/status',{signal:controller.signal});status=await response.json();if(!response.ok)throw Error();}finally{clearTimeout(timeout);s.startupController=null;}
  if(s.disposed)return;
  if(status.mode!=='SYNTHETIC'||status.sources!=='DISABLED'||status.execution!=='DISABLED'||status.source_clean!==true)throw Error();
  let initialized=false,previousSessionState='UNVERIFIED';
  sessionClient=new R4SessionClient({onState:(state,ended)=>{text('session-state',state);if(ended)terminal(state);else if(state==='DISCONNECTED'){stop();++s.generation;s.controller?.abort();clearPanels();text('source-state','DISCONNECTED');text('book-state','DISCONNECTED');document.body.dataset.loading='false';}else if(initialized&&previousSessionState==='DISCONNECTED'&&s.retry<5)load(Number($('seek').value));previousSessionState=state;}});
  await sessionClient.start(status.candidate_sha);
  if(s.disposed)return;
  initialized=true;if(sessionClient.state==='ACTIVE')load(0);else if(!s.disposed)text('source-state','DISCONNECTED');
 }catch{if(!s.disposed)terminal('UNVERIFIED');}
}
start();
})();

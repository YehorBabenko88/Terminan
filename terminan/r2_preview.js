/* Synthetic-only demand-driven rendering. No live/DB/order routes. */
'use strict';
(()=>{
const $=id=>document.getElementById(id), canvas=$('chart'), ctx=canvas.getContext('2d');
const s={data:null,contracts:null,generation:0,controller:null,playing:false,timer:0,raf:0,disposed:false,
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
  d.footprint.rows.forEach(r=>footprint.append(row([r.price.toFixed(2),r.buy,r.sell,r.delta,r.volume])));
  $('footprint-body').replaceChildren(footprint);
  text('footprint-time',d.footprint.rows.length?new Date(d.footprint.rows[0].t).toISOString()+' · closed minute · SYNTHETIC':'No available synthetic footprint');
  const contracts=document.createDocumentFragment();
  for(const c of s.contracts?.sources||[]){
    const div=document.createElement('div');div.className='contract';
    const label=document.createElement('div'),title=document.createElement('strong'),sub=document.createElement('small'),state=document.createElement('span');
    title.textContent=(c.source||'Source')+' / '+(c.kind||'contract');
    sub.textContent='SYNTHETIC · '+(c.provenance?.source_sha?.slice(0,10)||'rejected')+' · runtime NONE';
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
  if(s.disposed)return;
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
    try{const response=await fetch(route+'?'+query,{signal:controller.signal});const data=await response.json();if(!response.ok)throw Error(data.error||'Synthetic request failed');return data;}
    finally{s.active--;}
  }
  try{
    const [data,contracts]=await Promise.all([request('/api/synthetic/frame'),request('/api/synthetic/contracts')]);
    if(generation!==s.generation||s.disposed)return;
    if(data.mode!=='SYNTHETIC'||data.symbol+'|'+data.timeframe!==identity)throw Error('Synthetic identity mismatch');
    s.data=data;s.contracts=contracts;s.modelDirty=true;
    if(s.identity!==identity||!s.start){s.identity=identity;resetView();}else{
      if(follow&&data.candles.length){const span=s.end-s.start;s.end=data.candles.at(-1).t+data.period_ms;s.start=s.end-span;}
      clampView();
    }
    schedule();
  }catch(error){
    if(generation!==s.generation||s.disposed)return;
    text('error',error.name==='AbortError'?'Synthetic request cancelled or timed out':error.message);
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
function stop(){s.playing=false;if(s.timer){clearTimeout(s.timer);s.timer=0;}updatePlay();}
on($('play'),'click',()=>{s.playing=!s.playing;updatePlay();if(s.playing)load(Number($('seek').value));else if(s.timer){clearTimeout(s.timer);s.timer=0;}});
on($('step-once'),'click',()=>{stop();load(Math.min(600,Number($('seek').value)+1));});
on($('restart'),'click',()=>{stop();load(0);});
for(const id of ['symbol','timeframe','seed','scenario'])on($(id),'change',()=>{stop();load(Number($('seek').value));});
on($('seek'),'input',()=>{stop();load(Number($('seek').value));});
on($('zoom-in'),'click',()=>zoom(.75));on($('zoom-out'),'click',()=>zoom(1.35));on($('reset-view'),'click',resetView);
on(canvas,'dblclick',resetView);
on(canvas,'wheel',event=>{event.preventDefault();const rect=canvas.getBoundingClientRect();zoom(event.deltaY<0?.85:1.18,Math.max(0,Math.min(1,(event.clientX-rect.left)/rect.width)));},{passive:false});
on(canvas,'pointerdown',event=>{if(!s.data)return;s.drag={x:event.clientX,start:s.start,end:s.end};canvas.setPointerCapture(event.pointerId);});
on(canvas,'pointermove',event=>{if(!s.drag)return;const shift=(event.clientX-s.drag.x)/canvas.clientWidth*(s.drag.end-s.drag.start);s.start=s.drag.start-shift;s.end=s.drag.end-shift;clampView();schedule();});
on(canvas,'pointerup',()=>{s.drag=null;});on(canvas,'pointercancel',()=>{s.drag=null;});
on(window,'resize',schedule);
const observer=new ResizeObserver(schedule);observer.observe(canvas);
function metrics(){
  const n=s.renderTimes.length,elapsed=n>1?(s.renderTimes.at(-1)-s.renderTimes[0])/1000:0;
  return {renders:s.renders,avgRenderMs:s.samples.length?s.samples.reduce((a,b)=>a+b,0)/s.samples.length:0,
    effectiveRenderFps:elapsed?(n-1)/elapsed:0,renderSamples:s.samples.length,retainedCandles:s.data?.candles.length||0,
    retainedEvents:s.data?.events.length||0,activeRequests:s.active,peakRequests:s.peak,aborted:s.aborted,
    rafPending:Number(Boolean(s.raf)),timerPending:Number(Boolean(s.timer)),listeners:s.listeners.length,
    dpr:devicePixelRatio,spanMs:s.end-s.start,windowEnd:s.end,bookRows:$('book-body').children.length,fixtureCount:s.contracts?.sources.length||0};
}
function dispose(){
  if(s.disposed)return;stop();s.disposed=true;++s.generation;s.controller?.abort();
  if(s.raf)cancelAnimationFrame(s.raf);s.raf=0;observer.disconnect();
  s.listeners.forEach(remove=>remove());s.listeners=[];clearPanels();s.samples=[];s.renderTimes=[];
}
window.r2={seek:step=>{stop();return load(step);},metrics,dispose};load(0);
})();

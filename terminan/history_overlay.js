'use strict';
(() => {
 const $=id=>document.getElementById(id), NS='http://www.w3.org/2000/svg';
 const palette=['#ffbc73','#9f9bff','#55bafa','#ea8fca','#c9da75','#ff8585','#74ded1','#d0b18c','#f4d35e','#80b7fa','#aecc9e','#d6a7ff','#eab582','#a8d7dc','#ffabca','#b8c3ff'];
 let packets=[],layers=[],base=null,bounds=null,epoch=0,projection=null,hoverPoints=[],drag=null;
 const issue=message=>{$('status').textContent=message};
 const node=(tag,attrs={},content)=>{const n=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));if(content!==undefined)n.textContent=content;return n};
 const safeUTC=t=>t<=8640000000000000?new Date(t).toISOString().replace('T',' ').replace('.000Z',' UTC'):String(t)+' UTC ms';
 const key=()=> 'terminan.overlay.view.v1:'+packets.map(p=>p.receipt).sort().join(':');
 const canonical=v=>JSON.stringify(Array.isArray(v)?v.map(x=>JSON.parse(canonical(x))):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,JSON.parse(canonical(v[k]))])):v);
 async function hash(v){return [...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(canonical(v))))].map(x=>x.toString(16).padStart(2,'0')).join('')}
 async function scientificBinding(p){
  if(p.schema!=='terminan.scientific-overlay.v1')return;
  const r=p.request,result=p.result;
  if(!r||!result||!Array.isArray(r.nodes)||!Array.isArray(r.edges)||!Array.isArray(result.trace))throw Error('SCIENTIFIC_BINDING');
  const edges=await Promise.all(r.edges.map(async e=>({e,h:await hash(e)})));edges.sort((a,b)=>a.h<b.h?-1:a.h>b.h?1:0);
  const normalized={...r,nodes:[...r.nodes].sort((a,b)=>a.id<b.id?-1:a.id>b.id?1:0),edges:edges.map(x=>x.e)};
  if(await hash(normalized)!==result.requestSHA256)throw Error('SCIENTIFIC_REQUEST_DIGEST');
  for(const t of result.trace){const def=r.nodes.find(n=>n.id===t.node);if(!def||await hash(def)!==t.definitionSHA256)throw Error('SCIENTIFIC_DEFINITION_DIGEST')}
  for(const o of result.outputs){
   const t=result.trace.find(t=>t.node===o.node),port=t?.portOutputs?.find(p=>p.port===o.port);
   const expected=port?.sha256??(o.port==='value'?t?.outputSHA256:null);
   const value={type:o.type,unit:o.unit,values:o.values,timestamps:o.timestamps,availableAt:o.availableAt};
   if(!expected||await hash(value)!==expected)throw Error('SCIENTIFIC_OUTPUT_DIGEST');
  }
 }
 function settings(){return {version:1,from:Number($('from').value),to:Number($('to').value),asof:Number($('asof').value),mode:$('mode').value,prices:$('prices').checked,visible:Object.fromEntries(layers.map(l=>[l.id,l.visible]))}}
 function persist(){try{localStorage.setItem(key(),JSON.stringify(settings()))}catch{}}
 function restore(){try{const s=JSON.parse(localStorage.getItem(key()));
  if(!s||s.version!==1||![s.from,s.to,s.asof].every(Number.isSafeInteger)||s.from<bounds.lo||s.to>bounds.hi||s.to<=s.from||s.asof<0)return;
  $('from').value=s.from;$('to').value=s.to;$('asof').value=s.asof;$('mode').value=s.mode==='forward'?'forward':'historical';$('prices').checked=s.prices!==false;
  for(const l of layers)if(typeof s.visible?.[l.id]==='boolean')l.visible=s.visible[l.id];
 }catch{}}
 function setRange(start,end){const width=Math.min(bounds.hi-bounds.lo,Math.max(1,Math.round(end-start)));start=Math.max(bounds.lo,Math.min(bounds.hi-width,Math.round(start)));$('from').value=start;$('to').value=start+width}
 function fit(){if(!bounds)return;setRange(bounds.lo,bounds.hi);draw()}
 function view(){
  const raw=[$('from').value,$('to').value,$('asof').value];if(raw.some(v=>v.trim()===''))throw Error('INVALID_TIME_RANGE');
  const [start,end,asof]=raw.map(Number);
  if(![start,end].every(Number.isSafeInteger)||start<bounds.lo||end>bounds.hi||end<=start)throw Error('INVALID_TIME_RANGE');
  if(!Number.isSafeInteger(asof)||asof<0)throw Error('INVALID_ASOF');return {start,end,asof};
 }
 function legend(){
  const container=$('legend');for(const n of container.querySelectorAll('.model-label'))n.remove();
  for(const l of layers){const label=document.createElement('label');label.className='model-label';const input=document.createElement('input');input.type='checkbox';input.className='layer-toggle';input.checked=l.visible;input.dataset.color=l.color;input.setAttribute('aria-label',l.label);
   input.onchange=()=>{l.visible=input.checked;draw()};const swatch=document.createElement('span');swatch.className='swatch';swatch.style.background=l.color;
   label.append(input,swatch,document.createTextNode(l.label+' · '+l.receipt.slice(0,7)));container.append(label);
  }
 }
 function metadata(){
  $('identity').textContent=[base.identity.market.venue,base.identity.market.market_type,base.identity.market.symbol,base.identity.units.price,'dataset '+base.identity.dataset_id,'snapshot '+base.identity.snapshot_fingerprint].join(' · ');
  $('provenance').replaceChildren();for(const p of packets){const d=document.createElement('details');d.open=packets.length===1;const s=document.createElement('summary');s.textContent=p.metadata.model_version+' · '+p.receipt.slice(0,12)+' · '+p.integrity;
   const pre=document.createElement('pre');pre.textContent=JSON.stringify({schema:p.schema,sha256:p.receipt,integrity:p.integrity,source_authenticity:'UNATTESTED',units:p.identity.units,
    event_bounds:[Math.min(...p.observations.map(r=>r.time)),Math.max(...p.observations.map(r=>r.time))],availability_bounds:[Math.min(...p.observations.map(r=>r.available)),Math.max(...p.observations.map(r=>r.available))],
    forecast_bounds:p.layers.filter(l=>l.kind==='forecast'&&l.points.length).map(l=>({decision:[Math.min(...l.points.map(r=>r.decision)),Math.max(...l.points.map(r=>r.decision))],target:[Math.min(...l.points.map(r=>r.time)),Math.max(...l.points.map(r=>r.time))]})),...p.metadata},null,2);d.append(s,pre);$('provenance').append(d);
  }
 }
 function oos(asof){
  $('oos').replaceChildren();for(const p of packets){if(p.schema!=='terminan.history.scientific-handoff.v1')continue;const text=document.createElement('pre'),o=p.oos;
   text.textContent=p.receipt.slice(0,12)+' · '+(!o?'OOS_UNTIMED_NOT_DISPLAYED':o.available>asof?'NOT_AVAILABLE_ASOF · published '+safeUTC(o.available):o.label+'\nOOS '+safeUTC(o.start)+' → '+safeUTC(o.end)+'\npublished '+safeUTC(o.available)+'\n'+JSON.stringify(o.metrics,null,2)+'\nunits '+JSON.stringify(o.units));$('oos').append(text);
  }if(!$('oos').childNodes.length)$('oos').textContent='NO_PRODUCER_OOS';
 }
 function timeline(start,end,asof){
  const s=$('timeline');s.replaceChildren();const x=t=>10+980*(t-bounds.lo)/(bounds.hi-bounds.lo);
  s.append(node('rect',{x:10,y:10,width:980,height:12,fill:'#24384c',rx:4}),node('rect',{x:x(start),y:7,width:Math.max(1,x(end)-x(start)),height:18,fill:'#537996',rx:4}));
  if(asof>=bounds.lo&&asof<=bounds.hi)s.append(node('line',{x1:x(asof),x2:x(asof),y1:3,y2:30,stroke:'#f59cae','stroke-width':2}));
  $('asofSlider').min=bounds.lo;$('asofSlider').max=bounds.hi;$('asofSlider').value=Math.max(bounds.lo,Math.min(bounds.hi,asof));
 }
 function tooltip(p){
  $('tooltip').textContent=p.kind==='forecast'?`${p.label} · ${p.time>projection.asof?'FUTURE_HORIZON':'PAST_PREDICTION'} · value ${p.value} ${base.identity.units.price} · feature ${safeUTC(p.feature_event)} · available ${safeUTC(p.available)} · decision ${safeUTC(p.decision)} · target ${safeUTC(p.time)} · request ${p.request_digest}`:
   `${p.label} · ${p.kind==='observation'?'OBSERVATION':'SCIENTIFIC_HISTORICAL_RESULT (not a forecast)'} · value ${p.value} ${base.identity.units.price} · event ${safeUTC(p.time)} · available ${safeUTC(p.available)}`;
 }
 function screenPoint(event){const rect=$('chart').getBoundingClientRect();return {x:(event.clientX-rect.left)*1000/rect.width,y:(event.clientY-rect.top)*420/rect.height}}
 function draw(){
  const svg=$('chart');svg.replaceChildren();projection=null;hoverPoints=[];$('tooltip').textContent='Наведите crosshair на точку или выберите её клавишей Tab.';if(!base)return;
  let v;try{v=view()}catch(e){$('counts').textContent='INVALID_VIEW · данные скрыты';$('oos').textContent='INVALID_VIEW';$('timeline').replaceChildren();issue(e.message);return}
  const {start,end,asof}=v,within=r=>r.time>=start&&r.time<=end;
  const observations=$('prices').checked?base.observations.filter(r=>within(r)&&r.available<=asof):[];
  const rendered=layers.filter(l=>l.visible).map(l=>({...l,eligible:l.points.filter(r=>within(r)&&r.available<=asof&&(l.kind!=='scientific'||r.time<=asof)&&(l.kind!=='forecast'||r.decision<=asof&&($('mode').value!=='forward'||r.time>asof)))}));
  const values=[...observations.map(r=>r.value),...rendered.flatMap(l=>l.eligible.map(r=>r.value))],lo=values.length?Math.min(...values):0,hi=values.length?Math.max(...values):1;
  const scale=Math.max(1,Math.abs(lo),Math.abs(hi)),low=lo/scale,high=hi/scale,pad=Math.max(1e-9,(high-low)*.08);
  const bottom=Math.max(-Number.MAX_VALUE/scale,low-pad),top=Math.min(Number.MAX_VALUE/scale,high+pad);
  const x=t=>72+900*(t-start)/(end-start),y=value=>350-300*(value/scale-bottom)/(top-bottom);
  projection={...v,x,y};svg.append(node('rect',{x:0,y:0,width:1000,height:420,fill:'#0e1a28'}));
  const defs=node('defs'),clip=node('clipPath',{id:'plotClip'});clip.append(node('rect',{x:70,y:25,width:905,height:335}));defs.append(clip);svg.append(defs);
  for(let i=0;i<=4;i++){const yy=50+75*i;svg.append(node('line',{x1:72,y1:yy,x2:972,y2:yy,stroke:'#263a50'}));const value=(bottom+(top-bottom)*(4-i)/4)*scale;svg.append(node('text',{x:65,y:yy+4,fill:'#9eb2c8','font-size':11,'text-anchor':'end'},value.toPrecision(6)))}
  for(let i=0;i<=4;i++){const t=Math.round(start+(end-start)*i/4);svg.append(node('text',{x:x(t),y:382,fill:'#9eb2c8','font-size':10,'text-anchor':i===0?'start':i===4?'end':'middle'},safeUTC(t)))}
  svg.append(node('text',{x:72,y:18,fill:'#5ee0c3','font-size':12},base.identity.market.symbol+' · '+base.identity.units.price),node('text',{x:970,y:18,fill:'#9eb2c8','font-size':10,'text-anchor':'end'},'SYNTHETIC / UNATTESTED'));
  const plot=node('g',{'clip-path':'url(#plotClip)'});svg.append(plot);
  const addPoint=(r,kind,label,color)=>{
   const xx=x(r.time),yy=y(r.value),future=kind==='forecast'&&r.time>asof,attrs={class:'point '+(kind==='forecast'?(future?'forecast-future':'forecast-past'):kind==='observation'?'observation-point':'scientific-point'),tabindex:0,fill:kind==='forecast'&&!future?'#0e1a28':color,stroke:color,'stroke-width':1.5};
   const point=kind==='forecast'&&!future?node('path',{...attrs,d:`M${xx},${yy-5}l5,5l-5,5l-5,-5Z`}):node('circle',{...attrs,cx:xx,cy:yy,r:kind==='observation'?2:4});
   const p={...r,kind,label,xx,yy};point.setAttribute('aria-label',label+' '+kind+' '+r.value+' '+safeUTC(r.time));point.onfocus=()=>tooltip(p);point.append(node('title',{},point.getAttribute('aria-label')));plot.append(point);hoverPoints.push(p);
  };
  if(observations.length){plot.append(node('polyline',{class:'observation-line',points:observations.map(r=>`${x(r.time)},${y(r.value)}`).join(' '),fill:'none',stroke:'#5ee0c3','stroke-width':2}));for(const r of observations)addPoint(r,'observation','Наблюдения','#5ee0c3')}
  for(const l of rendered){if(l.kind==='scientific'&&l.eligible.length)plot.append(node('polyline',{class:'scientific-line',points:l.eligible.map(r=>`${x(r.time)},${y(r.value)}`).join(' '),fill:'none',stroke:l.color,'stroke-width':2,'stroke-dasharray':'5 4'}));for(const r of l.eligible)addPoint(r,l.kind,l.label,l.color)}
  if(asof>=start&&asof<=end)svg.append(node('line',{x1:x(asof),x2:x(asof),y1:25,y2:355,stroke:'#f59cae','stroke-dasharray':'6 4'}),node('text',{x:Math.min(910,x(asof)+6),y:36,fill:'#f59cae','font-size':11},'asOf'));
  svg.append(node('line',{id:'crossX',x1:0,x2:0,y1:25,y2:355,stroke:'#8daac4','stroke-dasharray':'3 4',visibility:'hidden','pointer-events':'none'}),node('line',{id:'crossY',x1:72,x2:972,y1:0,y2:0,stroke:'#8daac4','stroke-dasharray':'3 4',visibility:'hidden','pointer-events':'none'}));
  const forecasts=rendered.filter(l=>l.kind==='forecast').flatMap(l=>l.eligible);
  $('counts').textContent=`OBSERVATIONS ${observations.length} · PAST_PREDICTIONS ${forecasts.filter(r=>r.time<=asof).length} · FUTURE_HORIZON ${forecasts.filter(r=>r.time>asof).length} · SCIENTIFIC ${rendered.filter(l=>l.kind==='scientific').reduce((n,l)=>n+l.eligible.length,0)}`;
  $('rangeLabel').textContent=`${safeUTC(start)} → ${safeUTC(end)} · asOf ${safeUTC(asof)}`;timeline(start,end,asof);oos(asof);persist();issue('SYNTHETIC · UNATTESTED · SHA256_MATCH (integrity only) · READ_ONLY · NO_TRADING'+(!values.length?' · NO_CAUSALLY_AVAILABLE_POINTS':''));
 }
 function commit(next){
  packets=next;base=packets.find(p=>p.schema==='terminan.history.scientific-handoff.v1')||packets[0];const old=new Map(layers.map(l=>[l.id,l.visible]));
  layers=packets.flatMap(p=>p.layers.map((l,i)=>({...l,id:p.receipt+':'+i,receipt:p.receipt,visible:old.get(p.receipt+':'+i)??true})));layers.forEach((l,i)=>l.color=palette[i]);
  const times=[...base.observations.flatMap(r=>[r.time,r.available]),...layers.flatMap(l=>l.points.flatMap(r=>[r.time,r.available,...(l.kind==='forecast'?[r.decision]:[])]))];
  bounds={lo:Math.min(...times),hi:Math.max(...times)};if(bounds.hi===bounds.lo){if(bounds.hi<Number.MAX_SAFE_INTEGER)bounds.hi++;else bounds.lo--}
  $('asof').value=Math.max(...base.observations.map(r=>r.available));setRange(bounds.lo,bounds.hi);restore();legend();metadata();draw();
 }
 $('upload').onchange=async event=>{
  const batch=[...event.target.files],mine=++epoch;event.target.value='';if(!batch.length)return;issue('VALIDATING_IMPORT');
  try{
   if(batch.length>8)throw Error('PACKET_LIMIT');const additions=[];
   for(const f of batch){if(f.size>2*1024*1024)throw Error('FILE_LIMIT');const raw=await f.text();if(mine!==epoch)return;
    const response=await fetch('/api/history-overlay/validate',{method:'POST',headers:{'Content-Type':'application/json'},body:raw});
    if(!response.ok){const err=await response.json().catch(()=>({error:'VALIDATOR_UNAVAILABLE'}));throw Error(err.error)}
    const admitted=await response.json();await scientificBinding(JSON.parse(raw));additions.push(admitted);
   }if(mine!==epoch)return;
   const next=[...packets];for(const p of additions)if(!next.some(x=>x.receipt===p.receipt))next.push(p);
   if(next.length>8||next.reduce((n,p)=>n+p.layers.length,0)>16)throw Error('LAYER_LIMIT');
   const first=next[0];for(const p of next)if(canonical(p.identity)!==canonical(first.identity)||p.observation_digest!==first.observation_digest)throw Error('INCOMPATIBLE_DATASET_MARKET_OR_UNITS');commit(next);
  }catch(e){if(mine===epoch)issue('IMPORT_REJECTED: '+e.message+' · retained '+packets.length+' packets · UNATTESTED')}
 };
 $('clear').onclick=()=>{epoch++;packets=[];layers=[];base=null;bounds=null;projection=null;hoverPoints=[];$('chart').replaceChildren();$('timeline').replaceChildren();for(const id of ['identity','counts','provenance','oos'])$(id).textContent='NO_DATA';for(const id of ['from','to','asof'])$(id).value='';$('tooltip').textContent='NO_DATA';legend();issue('NO_DATA')};
 for(const id of ['from','to','asof','mode','prices'])$(id).addEventListener('change',draw);
 $('asofSlider').oninput=()=>{if(!base)return;$('asof').value=$('asofSlider').value;draw()};$('fit').onclick=fit;
 function zoom(factor,anchor=.5){if(!projection)return;const {start,end}=projection,width=(end-start)*factor,center=start+(end-start)*anchor;setRange(center-width*anchor,center+width*(1-anchor));draw()}
 function pan(fraction){if(!projection)return;const {start,end}=projection;setRange(start+(end-start)*fraction,end+(end-start)*fraction);draw()}
 $('zoomIn').onclick=()=>zoom(.7);$('zoomOut').onclick=()=>zoom(1/.7);$('panLeft').onclick=()=>pan(-.15);$('panRight').onclick=()=>pan(.15);
 const svg=$('chart');svg.addEventListener('wheel',e=>{if(!projection)return;e.preventDefault();zoom(e.deltaY>0?1.2:1/1.2,Math.max(0,Math.min(1,(screenPoint(e).x-72)/900)))},{passive:false});
 svg.onkeydown=e=>{const action={ArrowLeft:()=>pan(-.15),ArrowRight:()=>pan(.15),'+':()=>zoom(.7),'=':()=>zoom(.7),'-':()=>zoom(1/.7),Home:fit}[e.key];if(action){e.preventDefault();action()}};
 svg.onpointerdown=e=>{if(!projection||e.button!==0)return;const pt=screenPoint(e);drag={x:pt.x,start:projection.start,end:projection.end};svg.setPointerCapture(e.pointerId)};
 svg.onpointerup=e=>{drag=null;if(svg.hasPointerCapture(e.pointerId))svg.releasePointerCapture(e.pointerId)};svg.onpointercancel=()=>drag=null;
 svg.onpointermove=e=>{
  if(!projection)return;const pt=screenPoint(e);if(drag){const shift=(drag.x-pt.x)*(drag.end-drag.start)/900;setRange(drag.start+shift,drag.end+shift);draw();return}if(pt.x<72||pt.x>972||pt.y<25||pt.y>355)return;
  const cx=$('crossX'),cy=$('crossY');cx.setAttribute('x1',pt.x);cx.setAttribute('x2',pt.x);cy.setAttribute('y1',pt.y);cy.setAttribute('y2',pt.y);cx.setAttribute('visibility','visible');cy.setAttribute('visibility','visible');
  const near=hoverPoints.reduce((best,p)=>{const d=(p.xx-pt.x)**2+(p.yy-pt.y)**2;return !best||d<best.d?{p,d}:best},null);if(near&&near.d<2500)tooltip(near.p);else $('tooltip').textContent='UTC '+safeUTC(Math.round(projection.start+(pt.x-72)*(projection.end-projection.start)/900));
 };
 svg.onpointerleave=()=>{for(const id of ['crossX','crossY'])$(id)?.setAttribute('visibility','hidden')};
 $('timeline').onclick=e=>{if(!bounds||!projection)return;const r=$('timeline').getBoundingClientRect(),t=bounds.lo+Math.max(0,Math.min(1,(e.clientX-r.left)/r.width))*(bounds.hi-bounds.lo),half=(projection.end-projection.start)/2;setRange(t-half,t+half);draw()};
})();

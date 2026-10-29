'use strict';
(()=>{
 const $=id=>document.getElementById(id), controls=new AbortController();
 let catalog=null,current=null,rows=[],generation=0,controller=null,timer=0,closed=false,aborted=0,requests=0,active=0,peak=0,span=100,pan=0,replay=0,raf=0,drag=null,session=null,selectedTime=null,companion=[],companionStatus='NOT_REQUESTED',chartTimes=[],dragMoved=false;
 const text=(id,value)=>$(id).textContent=value;
 const source=()=>catalog?.sources.find(s=>s.id===$('saved-source').value);
 const dataset=()=>source()?.datasets.find(d=>d.name===$('dataset').value);
 const when=t=>Number.isSafeInteger(t)?new Date(t).toISOString():'—';
 const time=r=>r.ts??r.open_time??r.funding_time??r.created_at??r.event_ts??r.source_ts;
 const fmt=x=>x==null?'—':typeof x==='object'?JSON.stringify(x).slice(0,100):String(x);
 const add=(parent,tag,value,cls)=>{const e=document.createElement(tag);e.textContent=value;if(cls)e.className=cls;parent.append(e);return e;};
 function on(id,event,fn){$(id).addEventListener(event,fn,{signal:controls.signal});}
 async function read(url,signal){
  const r=await fetch(url,{signal,cache:'no-store'});const reader=r.body.getReader();let size=0,chunks=[];
  try{for(;;){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>1048576)throw Error('RESOURCE_LIMIT');chunks.push(value);}}finally{await reader.cancel().catch(()=>{});}
  const bytes=new Uint8Array(size);let at=0;for(const c of chunks){bytes.set(c,at);at+=c.length;}
  const data=JSON.parse(new TextDecoder().decode(bytes));if(!r.ok)throw Error(data.error||'SOURCE_UNAVAILABLE');return data;
 }
 async function lookupCache(p,gen){
  text('cache-match-state','Exact cache match: CHECKING');
  if(!p||!['footprint_1m','candles_1m'].includes(p.dataset)||source()?.source!=='grid'||
     !/^[a-f0-9]{64}$/.test(p.source_sha)||!p.rows.length){
   text('cache-match-state','Exact cache match: NOT_APPLICABLE');return;
  }
  const times=p.rows.map(r=>r.ts).filter(Number.isSafeInteger);
  if(!times.length){text('cache-match-state','Exact cache match: NO_RANGE');return;}
  const from=Math.min(...times),to=Math.max(...times);
  const query=new URLSearchParams({revision:p.source_sha,symbol:p.symbol,timeframe:displayTF(),
   from_ms:String(from),to_ms:String(to)});
  try{
   const d=await read('/api/saved/cache-lookup?'+query,controls.signal);
   if(closed||gen!==generation)return;
   if(d.authority!=='OFFLINE_ONLY'||typeof d.state!=='string')throw Error('UNVERIFIED_CACHE');
   if(d.state!=='READY'){
    if(!['MISS','EXPIRED','STALE','CORRUPT','AMBIGUOUS','UNAVAILABLE','DISABLED','MISSING'].includes(d.state))throw Error('UNVERIFIED_CACHE');
    text('cache-match-state','Exact cache match: '+d.state+' · source revision and UTC range required');
    return;
   }
   if(d.match!=='EXACT_SOURCE_REVISION_AND_RANGE'||d.source_revision!==p.source_sha||
      d.symbol!==p.symbol||d.timeframe!==displayTF()||!/^[a-f0-9]{64}$/.test(d.sha256)||
      !Array.isArray(d.candles)||d.candles.length>64||!Number.isSafeInteger(d.total_candles)||
      d.total_candles!==d.candles.length)throw Error('UNVERIFIED_CACHE');
   for(const c of d.candles){
    if(!Number.isSafeInteger(c.ts)||c.ts<from||c.ts>to||
       !['open','high','low','close','volume','delta'].every(k=>typeof c[k]==='number'&&Number.isFinite(c[k]))||
       c.low>Math.min(c.open,c.close)||c.high<Math.max(c.open,c.close)||c.volume<0)throw Error('UNVERIFIED_CACHE');
   }
   $('cache-result-rows').replaceChildren();
   for(const c of d.candles){
    const tr=add($('cache-result-rows'),'tr','');
    for(const v of [when(c.ts),c.open,c.high,c.low,c.close,c.volume,c.delta])add(tr,'td',String(v));
   }
   text('cache-result-state','EXACT CACHE HIT · '+d.symbol+' · '+d.timeframe+' · '+d.total_candles+' candles · OFFLINE_ONLY');
   text('cache-match-state','Exact cache match: READY · SHA256 '+d.sha256.slice(0,12));
  }catch(_){
   if(closed||gen!==generation)return;
   text('cache-match-state','Exact cache match: UNAVAILABLE · no fallback');
  }
 }
 async function inspectCache(jobId){
  if(closed)return;
  text('cache-result-state','Loading verified offline cache...');
  $('cache-result-rows').replaceChildren();
  try{
   const d=await read('/api/saved/cache-result?job_id='+encodeURIComponent(jobId),controls.signal);
   if(closed)return;
   if(d.state!=='READY'||d.authority!=='OFFLINE_ONLY'||!/^[a-f0-9]{64}$/.test(d.sha256)||
      !Array.isArray(d.candles)||d.candles.length>64||
      !Number.isSafeInteger(d.total_candles)||d.total_candles<d.candles.length||
      !/^[A-Z0-9_-]{1,80}$/.test(d.symbol)||!['1m','5m','15m','1h','4h','1d'].includes(d.timeframe))
      throw Error('UNVERIFIED_CACHE');
   for(const c of d.candles){
    if(!Number.isSafeInteger(c.ts)||!['open','high','low','close','volume','delta'].every(k=>typeof c[k]==='number'&&Number.isFinite(c[k]))||
       c.low>Math.min(c.open,c.close)||c.high<Math.max(c.open,c.close)||c.volume<0)
       throw Error('UNVERIFIED_CACHE');
   }
   text('cache-result-state',d.symbol+' · '+d.timeframe+' · '+d.total_candles+' cached candles · OFFLINE_ONLY · SHA256 '+d.sha256.slice(0,12));
   for(const c of d.candles){
    const tr=add($('cache-result-rows'),'tr','');
    for(const v of [when(c.ts),c.open,c.high,c.low,c.close,c.volume,c.delta])add(tr,'td',String(v));
   }
  }catch(_){
   if(closed)return;
   $('cache-result-rows').replaceChildren();
   text('cache-result-state','CACHE_RESULT_UNAVAILABLE · no fallback');
  }
 }
 async function refreshCache(){
  if(closed)return;
  text('cache-summary','Checking local cache...');
  $('cache-jobs').replaceChildren();
  try{
   const d=await read('/api/saved/cache-status',controls.signal);
   if(closed)return;
   if(!['READ_ONLY','DISABLED'].includes(d.mode)||d.authority!=='OFFLINE_ONLY'||
      !Array.isArray(d.jobs)||d.jobs.length>100||!Number.isSafeInteger(d.entries)||d.entries<0)
      throw Error('CACHE_SCHEMA_UNVERIFIED');
   const valid=d.jobs.every(j=>/^[a-f0-9]{32}$/.test(j.job_id)&&
      ['QUEUED','RUNNING','READY','FAILED'].includes(j.state)&&
      Number.isSafeInteger(j.attempt)&&j.attempt>=0&&
      (j.error_code==null||['COMPUTE_FAILED','INCOMPLETE','CACHE_FAILED'].includes(j.error_code)));
   if(!valid)throw Error('CACHE_SCHEMA_UNVERIFIED');
   text('cache-summary',d.mode+' · '+d.entries+' entries · '+d.jobs.length+' jobs');
   for(const j of d.jobs){
    const tr=add($('cache-jobs'),'tr','');
    for(const value of [j.job_id,j.state,j.attempt,j.error_code||'—'])add(tr,'td',String(value));
    if(j.state==='READY'){
     const cell=add(tr,'td','');
     const btn=add(cell,'button','View cached candles');
     btn.type='button';
     btn.addEventListener('click',()=>inspectCache(j.job_id),{signal:controls.signal});
    }
   }
  }catch(_){
   if(closed)return;
   $('cache-jobs').replaceChildren();
   text('cache-summary','CACHE_UNAVAILABLE · no fallback');
  }
 }
 function options(){
  const select=$('dataset');select.replaceChildren();for(const d of source()?.datasets||[]){const o=add(select,'option',d.name+(d.supported?'':' · excluded'));o.value=d.name;o.disabled=!d.supported;}
  const first=source()?.datasets.find(d=>d.supported);if(first)select.value=first.name;
  syncTimeframe();
  text('mode',source()?.backend==='fixture'?'SYNTHETIC FIXTURES · NOT LIVE':source()?'HISTORICAL READ ONLY · NOT LIVE':'SOURCES DISABLED');
 }
 function syncTimeframe(){
  const d=dataset(),select=$('saved-timeframe'),native=d?.timeframe;
  const local=d?.name==='footprint_1m'||d?.name==='candles_1m';
  for(const option of select.options)option.disabled=!local&&!!native&&option.value!==native;
  if(!local&&native&&select.value!==native)select.value=native;
  select.title=local?'Local bounded aggregation from native 1m; partial periods explicitly marked':native?'Dataset native timeframe: '+native:'Choose timeframe';
 }
 function displayTF(){return $('saved-timeframe').value;}
 function aggregated(){
  if(!current||!window.SavedMTF||!['footprint_1m','candles_1m'].includes(dataset()?.name))return [];
  const candles=dataset()?.name==='footprint_1m'?companion:rows;
  const levels=dataset()?.name==='footprint_1m'?rows:[];
  return window.SavedMTF.aggregate(candles,levels,displayTF());
 }
 function chartCount(){return ['footprint_1m','candles_1m'].includes(dataset()?.name)?aggregated().length:rows.length;}
 function chartWindow(){const count=chartCount();return Math.max(0,Math.min(count,Math.round(span)));}
 function stopReplay(){clearTimeout(timer);timer=0;text('saved-play','▶ Replay page');}
 function clearIdentity(){text('row-detail','');text('provenance','');delete document.body.dataset.identity;delete document.body.dataset.dataset;}
 function blank(){text('cache-match-state','Exact cache match: NOT_CHECKED');stopReplay();rows=[];current=null;replay=0;selectedTime=null;companion=[];companionStatus='NOT_REQUESTED';$('next').disabled=true;clearIdentity();render();}
 function validate(p,expected,next){
  const d=dataset(),s=source();
  if(!p||p.version!==1||p.candidate_sha!==catalog.candidate_sha||p.source_id!==s.id||p.dataset!==d.name||p.source_sha!==s.source_sha||p.provenance?.source_sha!==s.source_sha||p.rows?.length>200||!Array.isArray(p.rows)||!/^[a-f0-9]{64}$/.test(p.epoch)||!Number.isSafeInteger(p.as_of_ms)||p.cutoff_ms>p.as_of_ms)throw Error('INVALID_SOURCE_RESPONSE');
  if(p.symbol!==(d.scope==='SYMBOL'?expected.symbol:null)||p.timeframe!==((d.timeframe||d.columns.includes('timeframe'))?expected.timeframe:null))throw Error('SOURCE_IDENTITY_MISMATCH');
  if(p.authority!==(s.backend==='fixture'?'SYNTHETIC_ONLY':'HISTORICAL_ONLY')||p.mode!==(s.backend==='fixture'?'SYNTHETIC':'HISTORICAL'))throw Error('AUTHORITY_MISMATCH');
  if(p.previous_sequence!==(next?current?.sequence:0)||p.sequence!==p.previous_sequence+1||next&&p.epoch!==current?.epoch)throw Error('SEQUENCE_ERROR');
  for(const r of p.rows){if(d.scope==='SYMBOL'&&r.symbol!==expected.symbol||d.columns.includes('timeframe')&&r.timeframe!==expected.timeframe)throw Error('SOURCE_IDENTITY_MISMATCH');for(const v of Object.values(r)){if(typeof v==='number'&&!Number.isFinite(v))throw Error('INVALID_DATA');}const t=time(r);if(t!=null&&(!Number.isSafeInteger(t)||t>p.cutoff_ms))throw Error('FUTURE_LEAKAGE');}
 }
 async function load(next=false){
  if(closed||!source()||!dataset())return;syncTimeframe();
  const gen=++generation;controller?.abort();if(active)aborted++;stopReplay();
  const c=new AbortController();controller=c;const timeout=setTimeout(()=>c.abort(),3500);
  const expected={symbol:$('saved-symbol').value,timeframe:['footprint_1m','candles_1m'].includes(dataset()?.name)?'1m':$('saved-timeframe').value};
  const q=new URLSearchParams({source:source().id,dataset:dataset().name,...expected,limit:$('limit').value});
  if($('from-utc').value)q.set('from_ms',Date.parse($('from-utc').value+'Z'));if($('to-utc').value)q.set('cutoff_ms',Date.parse($('to-utc').value+'Z'));
  if(next&&current?.next_cursor){q.set('cursor',current.next_cursor);q.set('cutoff_ms',current.cutoff_ms);q.set('from_ms',current.from_ms);}else{next=false;blank();}
  text('saved-error','');text('saved-status','LOADING · authority UNVERIFIED');$('next').disabled=true;requests++;active=1;peak=Math.max(peak,active);
  try{
   const p=await read('/api/saved/page?'+q,c.signal);if(closed||gen!==generation)return;validate(p,expected,next);current=p;rows=p.rows;replay=rows.length;span=rows.length;pan=0;selectedTime=null;
   await loadCompanion(p,c.signal,gen);if(closed||gen!==generation)return;
   if(companionStatus==='HISTORICAL_PAGE_ONLY')span=companion.length;
   document.body.dataset.identity=(p.symbol??'GLOBAL')+'|'+(p.timeframe??'UNSCOPED');document.body.dataset.dataset=dataset().name;
   text('saved-status',`${p.mode} · ${p.state} · ${p.authority} · ${p.freshness} · ${p.symbol??'GLOBAL'} / ${p.timeframe??'UNSCOPED'} · page sequence ${p.sequence}`);
   text('provenance',`Source ${p.source_id} / ${p.source_sha} · schema ${p.provenance.schema_id} / ${p.schema_sha} · UTC as-of ${when(p.as_of_ms)} · ${p.coverage.scope} · ${p.provenance.publication}`);
   $('next').disabled=!p.next_cursor;render();void lookupCache(p,gen);
  }catch(e){if(closed||gen!==generation)return;rows=[];current=null;replay=0;selectedTime=null;companion=[];companionStatus='UNAVAILABLE';clearIdentity();render();text('saved-status','UNVERIFIED · no fallback');text('saved-error',/^[A-Z_]{1,50}$/.test(e.message)?e.message:e.name==='AbortError'?'REQUEST_TIMEOUT':'INVALID_SOURCE_RESPONSE');}
  finally{clearTimeout(timeout);if(gen===generation){active=0;controller=null;document.body.dataset.loading='false';}}
 }
 async function loadCompanion(p,signal,gen){
  companion=[];companionStatus='NOT_APPLICABLE';
  if(p.dataset!=='footprint_1m'||p.source_id!==source()?.id||source()?.source!=='grid')return;
  const ds=source().datasets.find(d=>d.name==='candles_1m'&&d.supported);
  if(!ds){companionStatus='NO_CANDLE_DATASET';return;}
  const times=p.rows.map(r=>r.ts).filter(Number.isSafeInteger);
  if(!times.length){companionStatus='NO_FOOTPRINT_ROWS';return;}
  const min=Math.min(...times),max=Math.max(...times);
  const q=new URLSearchParams({source:p.source_id,dataset:'candles_1m',symbol:p.symbol,timeframe:'1m',
   limit:'200',from_ms:String(min),cutoff_ms:String(Math.min(p.cutoff_ms,max))});
  companionStatus='LOADING';
  try{
   const x=await read('/api/saved/page?'+q,signal);
   if(closed||gen!==generation)return;
   if(x.version!==1||x.candidate_sha!==p.candidate_sha||x.source_id!==p.source_id||
      x.source_sha!==p.source_sha||x.dataset!=='candles_1m'||x.symbol!==p.symbol||
      x.timeframe!=='1m'||x.mode!==p.mode||x.authority!==p.authority||
      x.provenance?.source_sha!==p.source_sha||!Array.isArray(x.rows)||
      x.rows.length>200||x.next_cursor||x.previous_sequence!==0||x.sequence!==1||
      !Number.isSafeInteger(x.cutoff_ms)||x.cutoff_ms>p.cutoff_ms||
      !/^[a-f0-9]{64}$/.test(x.epoch))throw Error('COMPANION_IDENTITY');
   const seen=new Set();
   for(const r of x.rows){
    if(r.symbol!==p.symbol||!Number.isSafeInteger(r.ts)||r.ts<min||r.ts>max||
       seen.has(r.ts)||!['open','high','low','close','buy_volume','sell_volume'].every(k=>typeof r[k]==='number'&&Number.isFinite(r[k]))||
       r.low>Math.min(r.open,r.close)||r.high<Math.max(r.open,r.close)||
       Math.min(r.buy_volume,r.sell_volume)<=-1e-12||
       (r.volume!=null&&(!Number.isFinite(r.volume)||r.volume<0)))
       throw Error('COMPANION_INVALID');
    seen.add(r.ts);
   }
   companion=x.rows;companionStatus=x.rows.length?'HISTORICAL_PAGE_ONLY':'NO_MATCHING_CANDLES';
  }catch(e){
   if(closed||gen!==generation)return;
   companion=[];companionStatus=e.name==='AbortError'?'REQUEST_TIMEOUT':'UNVERIFIED';
  }
 }
 function render(){
  $('saved-seek').max=rows.length;$('saved-seek').value=replay;text('saved-position',`${replay} / ${rows.length}`);text('row-count',`${rows.length} rows`);text('saved-title',dataset()?.name||'Saved candles');
  const visible=rows.slice(0,replay);const research=dataset()?.name==='research_results';const head=$('saved-head'),body=$('saved-body');head.replaceChildren();body.replaceChildren();
  const fields=research?['run_id','strategy_id','strategy_version','created_at','net_pnl','win_rate','max_drawdown','trades','wins','losses','fees','profit_factor','coverage','publication_state']:Object.keys(visible[0]||{}).slice(0,12);
  const tr=add(head,'tr','');for(const k of fields)add(tr,'th',k);
  for(const r of visible){const tr=add(body,'tr','');if(selectedTime!==null&&time(r)===selectedTime)tr.classList.add('saved-time-selected');for(const k of fields){let value=r[k]??(research?r.metrics?.[k]:null);if(dataset()?.time_columns?.includes(k)||['ts','open_time','created_at','event_ts','source_ts','funding_time'].includes(k))value=when(value);add(tr,'td',fmt(value));}tr.onclick=()=>{text('row-detail',JSON.stringify(r,null,2));const t=time(r);if(Number.isSafeInteger(t))selectTime(t);};}
  text('columns-note','First12 table columns; select a row for all projected fields. Internal/secret-bearing fields are excluded by the reviewed catalog. Page coverage never asserts full history.');
  const clusters=$('saved-clusters');clusters.replaceChildren();
  if(dataset()?.name==='footprint_1m'){
   const groups=new Map();
   if(displayTF()==='1m'){for(const r of visible){if(!groups.has(r.ts))groups.set(r.ts,[]);groups.get(r.ts).push(r);}}
   else {for(const period of aggregated()){if(!period.levels.length)continue;groups.set(period.ts,period.levels.map(r=>({...r,ts:period.ts,partial:!period.complete||!period.footprint_complete})));}}
   // One shared price axis across every visible minute. Price levels are placed
   // at their actual vertical price coordinate, not stacked by row index.
   const all=[...groups.values()].flat();
   if(all.length){
    const prices=[...new Set(all.map(r=>r.price))].sort((a,b)=>a-b);
    const lo=prices[0],hi=prices[prices.length-1];
    const diffs=prices.slice(1).map((p,i)=>p-prices[i]).filter(v=>v>0);
    const tick=diffs.length?Math.min(...diffs):1;
    const maxCells=80,step=Math.max(tick,(hi-lo)/Math.max(1,maxCells-1));
    const height=Math.max(180,Math.min(900,(hi-lo)/step*30+44));
    clusters.style.setProperty('--cluster-height',height+'px');
    clusters.style.setProperty('--cluster-step',step);
    const axis=add(clusters,'div','', 'cluster-price-axis');
    const axisTop=add(axis,'span',String(hi));axisTop.className='cluster-axis-top';
    const axisBottom=add(axis,'span',String(lo));axisBottom.className='cluster-axis-bottom';
    for(const [t,levels] of groups){
     const card=add(clusters,'article','', 'price-cluster-candle');
     card.dataset.minute=String(t);
     if(selectedTime===t)card.classList.add('cluster-selected-minute');
     card.tabIndex=0;card.setAttribute('role','button');card.setAttribute('aria-label','Select UTC minute '+when(t));
     card.addEventListener('click',()=>selectTime(t));
     card.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();selectTime(t);}});
     const plot=add(card,'div','', 'cluster-price-plot');
     const max=Math.max(...levels.map(r=>r.volume));
     const sorted=[...levels].sort((a,b)=>b.price-a.price);
     const top=Math.max(...levels.map(r=>r.price)),bottom=Math.min(...levels.map(r=>r.price));
     const y=price=>height-22-(price-lo)/(hi-lo||1)*(height-44);
     const spine=add(plot,'div','', 'cluster-candle-spine');
     spine.style.top=y(top)+'px';spine.style.height=Math.max(2,y(bottom)-y(top))+'px';
     for(const r of sorted){
      const line=add(plot,'div','',r.volume===max&&!r.partial?'level poc price-cluster-level':'level price-cluster-level');
      line.dataset.price=String(r.price);
      line.dataset.side=r.delta>0?'buy':r.delta<0?'sell':'neutral';
      line.style.top=y(r.price)+'px';
      line.title=`Price ${r.price} · Sell ${r.sell_volume} · Buy ${r.buy_volume} · Volume ${r.volume} · Delta ${r.delta}`;
      add(line,'span',`${r.sell_volume} × ${r.buy_volume}`);
     }
     const label=add(card,'small',when(t)+(levels.some(r=>r.partial)?' · PARTIAL':''),'cluster-minute-label');
     label.title=when(t);
     add(card,'small',`ΣV ${levels.reduce((s,r)=>s+r.volume,0)} · Δ ${levels.reduce((s,r)=>s+r.delta,0)}`,'cluster-minute-totals');
    }
   }
  }else add(clusters,'p','Select footprint_1m to view multiple saved minute clusters. The synthetic book is a separate panel.');
  text('selected-utc',selectedTime===null?'No minute selected':'Selected UTC '+when(selectedTime));
  text('companion-state','Candle companion: '+companionStatus+' · same Grid source · bounded page');
  scheduleDraw();text('saved-metrics',`Retained ${rows.length}/200 rows · requests ${requests} · active ${active} · cancelled ${aborted} · page only`);
 }
 function selectTime(t){
  if(!Number.isSafeInteger(t)||!rows.some(r=>time(r)===t))return;
  selectedTime=t;
  const index=rows.findIndex(r=>time(r)===t);
  if(index>=replay)replay=index+1;
  stopReplay();render();
  const card=[...$('saved-clusters').querySelectorAll('[data-minute]')].find(el=>el.dataset.minute===String(t));
  if(card)card.scrollIntoView({block:'nearest',inline:'nearest'});
 }
 function syncClusterWindow(){
  const cluster=$('saved-clusters');
  const cards=[...cluster.querySelectorAll('.price-cluster-candle')];
  if(!cards.length)return;
  const times=new Set(chartTimes.filter(Number.isSafeInteger));
  const hasCompanion=dataset()?.name==='footprint_1m'&&companionStatus==='HISTORICAL_PAGE_ONLY';
  for(const card of cards){
   const t=Number(card.dataset.minute);
   card.classList.toggle('outside-candle-window',hasCompanion&&!times.has(t));
  }
  if(!hasCompanion||!times.size)return;
  const first=cards.find(card=>times.has(Number(card.dataset.minute)));
  if(first){
   const left=Math.max(0,first.offsetLeft-cluster.offsetLeft-62);
   if(Math.abs(cluster.scrollLeft-left)>100)cluster.scrollLeft=left;
  }
 }
 function scheduleDraw(){if(!closed&&!raf)raf=requestAnimationFrame(draw);}
 function draw(){
  raf=0;const canvas=$('saved-chart'),rect=canvas.getBoundingClientRect(),dpr=devicePixelRatio;canvas.width=Math.round(rect.width*dpr);canvas.height=Math.round(rect.height*dpr);const c=canvas.getContext('2d');c.scale(dpr,dpr);c.clearRect(0,0,rect.width,rect.height);
  const footprint=dataset()?.name==='footprint_1m';
  const visibleTimes=new Set(rows.slice(0,replay).map(r=>r.ts));
  const candles=(['footprint_1m','candles_1m'].includes(dataset()?.name)?aggregated().filter(r=>r.ts<=Math.max(...visibleTimes,0)):rows.slice(0,replay)).filter(r=>['open','high','low','close'].every(k=>typeof r[k]==='number'));const n=Math.min(candles.length,Math.max(1,Math.round(span))),maxPan=Math.max(0,candles.length-n),offset=Math.max(0,Math.min(maxPan,Math.round(pan))),end=candles.length-offset,view=candles.slice(Math.max(0,end-n),end);
  chartTimes=view.map(time);syncClusterWindow();$('saved-empty').hidden=view.length>0;if(!view.length)return;const low=Math.min(...view.map(r=>r.low)),high=Math.max(...view.map(r=>r.high)),range=high-low||1,height=rect.height-70,width=rect.width/view.length,y=v=>18+(high-v)/range*(height-36),vol=r=>r.volume??(r.buy_volume??0)+(r.sell_volume??0),vmax=Math.max(1,...view.map(vol));
  view.forEach((r,i)=>{const x=(i+.5)*width;c.fillStyle=c.strokeStyle=r.close>=r.open?'#64dca6':'#ff8c95';c.beginPath();c.moveTo(x,y(r.high));c.lineTo(x,y(r.low));c.stroke();c.fillRect(x-width*.3,Math.min(y(r.open),y(r.close)),Math.max(1,width*.6),Math.max(1,Math.abs(y(r.close)-y(r.open))));c.globalAlpha=.4;c.fillRect(x-width*.3,height+8,width*.6,vol(r)/vmax*44);c.globalAlpha=1;if(r.complete===false){c.fillStyle='#ffdc87';c.font='9px monospace';c.fillText('PARTIAL',x-width*.42,14);}if(selectedTime!==null&&time(r)===selectedTime){c.strokeStyle='#ffdc87';c.lineWidth=2;c.strokeRect(x-width*.42,8,width*.84,height-2);c.lineWidth=1;}if(r.complete!==false&&r.poc_price!=null){c.fillStyle='#ffdc87';c.fillRect(x-width*.3,y(r.poc_price),width*.6,2);}});
  c.fillStyle='#91a3b8';c.font='11px monospace';c.fillText(`${when(time(view[0]))}  →  ${when(time(view.at(-1)))}`,8,rect.height-5);
 }
 function tick(){timer=0;if(closed)return;if(replay>=rows.length){stopReplay();return;}replay++;selectedTime=time(rows[replay-1])??null;render();timer=setTimeout(tick,180);}
 function dispose(state='VIEW_CLOSED'){
  if(closed)return;closed=true;chartTimes=[];++generation;controller?.abort();controller=null;active=0;stopReplay();cancelAnimationFrame(raf);raf=0;observer.disconnect();controls.abort();session?.close();rows=[];current=null;selectedTime=null;companion=[];companionStatus='VIEW_CLOSED';$('saved-head').replaceChildren();$('saved-body').replaceChildren();$('saved-clusters').replaceChildren();text('row-detail','');text('host-state',state);text('saved-status',state+' · requests stopped');text('saved-error','');for(const e of document.querySelectorAll('button,select,input'))e.disabled=true;
 }
 for(const id of ['saved-symbol','limit','from-utc','to-utc'])on(id,'change',()=>load());on('saved-source','change',()=>{options();load();});on('dataset','change',()=>{syncTimeframe();load();});on('saved-timeframe','change',()=>{if(['footprint_1m','candles_1m'].includes(dataset()?.name)){span=aggregated().length;pan=0;render();}else load();});on('reload','click',()=>load());on('next','click',()=>load(true));
 on('cache-refresh','click',refreshCache);
 on('zoom-in','click',()=>{span=Math.max(4,Math.min(chartCount(),span*.7));scheduleDraw();});on('zoom-out','click',()=>{span=Math.min(chartCount(),Math.max(4,span*1.4));scheduleDraw();});on('reset','click',()=>{span=chartCount();pan=0;scheduleDraw();});
 on('saved-chart','click',e=>{
  if(closed||drag!==null||dragMoved||!chartTimes.length){dragMoved=false;return;}
  const bounds=$('saved-chart').getBoundingClientRect();
  if(bounds.width<=0)return;
  const x=Math.max(0,Math.min(bounds.width-1,e.clientX-bounds.left));
  const i=Math.min(chartTimes.length-1,Math.floor(x/bounds.width*chartTimes.length));
  const t=chartTimes[i];
  if(Number.isSafeInteger(t))selectTime(t);
 });
 on('saved-chart','wheel',e=>{e.preventDefault();span=Math.max(4,Math.min(chartCount(),span*(e.deltaY>0?1.2:.8)));scheduleDraw();});on('saved-chart','pointerdown',e=>{drag=e.clientX;dragMoved=false;$('saved-chart').setPointerCapture(e.pointerId);});on('saved-chart','pointermove',e=>{if(drag==null)return;if(Math.abs(e.clientX-drag)>3)dragMoved=true;pan=Math.max(0,Math.min(Math.max(0,chartCount()-span),pan+(e.clientX-drag)/$('saved-chart').clientWidth*span));drag=e.clientX;scheduleDraw();});on('saved-chart','pointerup',()=>{drag=null;});on('saved-chart','dblclick',()=>{span=chartCount();pan=0;scheduleDraw();});
 on('cluster-prev','click',()=>{const times=[...new Set(rows.slice(0,replay).map(time).filter(Number.isSafeInteger))].sort((a,b)=>a-b);const i=times.indexOf(selectedTime);if(times.length)selectTime(times[Math.max(0,i<0?times.length-1:i-1)]);});
 on('cluster-next','click',()=>{const times=[...new Set(rows.map(time).filter(Number.isSafeInteger))].sort((a,b)=>a-b);const i=times.indexOf(selectedTime);if(times.length)selectTime(times[Math.min(times.length-1,i<0?0:i+1)]);});
 on('saved-play','click',()=>{if(timer){stopReplay();return;}if(replay>=rows.length)replay=0;text('saved-play','Pause');tick();});on('saved-step','click',()=>{stopReplay();replay=Math.min(rows.length,replay+1);selectedTime=replay?time(rows[replay-1])??null:null;render();});on('saved-seek','input',()=>{stopReplay();replay=Number($('saved-seek').value);selectedTime=replay?time(rows[replay-1])??null:null;render();});on('close','click',()=>dispose());window.addEventListener('pagehide',()=>dispose(),{signal:controls.signal});
 window.addEventListener('resize',scheduleDraw,{signal:controls.signal});
 const observer=new ResizeObserver(scheduleDraw);observer.observe($('saved-chart'));
 window.saved={load,dispose,metrics:()=>({closed,rows:rows.length,active,peak,aborted,requests,span,pan,replay,selectedTime,companionRows:companion.length,companionStatus,timer:!!timer,raf:!!raf,session:session?.metrics?.()})};
 (async()=>{const c=new AbortController();controller=c;const timeout=setTimeout(()=>c.abort(),3500);try{catalog=await read('/api/saved/catalog',c.signal);if(closed)return;controller=null;if(catalog.version!==1||!Array.isArray(catalog.sources)||catalog.sources.length>8||!/^[a-f0-9]{40}$/.test(catalog.candidate_sha))throw Error('INVALID_CATALOG');text('saved-sha',catalog.candidate_sha);for(const s of catalog.sources){const o=add($('saved-source'),'option',`${s.id} · ${s.backend}`);o.value=s.id;}options();refreshCache();session=new R4SessionClient({onState:(state,terminal)=>{text('host-state',state);if(terminal)dispose(state);}});session.start(catalog.candidate_sha);if(source())await load();else document.body.dataset.loading='false';}catch(e){if(!closed){text('saved-error','CATALOG_UNAVAILABLE');document.body.dataset.loading='false';}}finally{clearTimeout(timeout);}})();
})();

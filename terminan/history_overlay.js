'use strict';
(() => {
 const $=id=>document.getElementById(id), svgNS='http://www.w3.org/2000/svg';
 let packet=null;
 const issue=msg=>{$('status').textContent=msg;};
 function validate(p){
  if(!p||p.schema!=='terminan.history.scientific-handoff.v1'||p.evidence_class!=='SYNTHETIC'||p.source_authenticity!=='UNATTESTED'||p.scientific_api!=='NOT_EXECUTED')throw Error('UNSUPPORTED_OR_UNTRUSTED_PACKET');
  if(p.execution_authority!==false||p.trading_authorized!==false||p.training_authorized!==false)throw Error('AUTHORITY_DENIED');
  if(!p.market||typeof p.market!=='object'||typeof p.market.symbol!=='string'||!p.market.symbol||typeof p.strategy!=='string')throw Error('MARKET_IDENTITY_REQUIRED');\n  if(typeof p.handoff_sha256!=='string'||!(/^[a-f0-9]{64}$/i).test(p.handoff_sha256))throw Error('RECEIPT_REQUIRED');
  if(!Array.isArray(p.observed_prices)||!p.observed_prices.length||p.observed_prices.length>2000||!Array.isArray(p.forecast_points)||p.forecast_points.length>2000)throw Error('ROW_LIMIT');
  let previous=-1;
  for(const r of p.observed_prices){const {event_end_ms:e,available_at_ms:a,watermark_ms:w,value:v}=r;
   if(![e,a,w].every(n=>Number.isSafeInteger(n)&&n>=0)||!(previous<e&&e<=w&&w<=a)||!Number.isFinite(v)||v<=0)throw Error('INVALID_SOURCE_CLOCK_OR_PRICE');previous=e;}
  for(const r of p.forecast_points){const {feature_event_end_ms:e,feature_available_at_ms:a,decision_ms:d,target_event_end_ms:t,value:v}=r;
   if(![e,a,d,t].every(n=>Number.isSafeInteger(n)&&n>=0)||!(e<=a&&a<=d&&d<t)||!Number.isFinite(v)||v<=0||typeof r.request_digest!=='string'||!(/^[a-f0-9]{64}$/).test(r.request_digest))throw Error('INVALID_FORECAST_CLOCK');}
  return p;
 }
 const el=(tag,attrs)=>{const n=document.createElementNS(svgNS,tag);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,String(v)));return n;};
 function draw(){
  if(!packet)return;
  const svg=$('chart');svg.replaceChildren();const all=packet.observed_prices;
  const start=Number($('from').value)||all[0].event_end_ms,end=Number($('to').value)||all.at(-1).event_end_ms;
  if(end<=start){issue('INVALID_TIME_RANGE');return}
  const asOf=Number($('asof').value);
  if(!Number.isSafeInteger(asOf)||asOf<0){issue('INVALID_ASOF');return}
  const prices=all.filter(r=>r.event_end_ms>=start&&r.event_end_ms<=end&&r.available_at_ms<=asOf);
  const mode=$('mode').value;
  const forecast=packet.forecast_points.filter(r=>r.target_event_end_ms>=start&&r.target_event_end_ms<=end&&r.decision_ms<=asOf&&(mode!=='forward'||r.target_event_end_ms>asOf));
  const ys=[...prices.map(r=>r.value),...forecast.map(r=>r.value)];
  if(!ys.length){issue('NO_CAUSALLY_AVAILABLE_POINTS');return}
  const lo=Math.min(...ys),hi=Math.max(...ys),margin=Math.max(1e-9,(hi-lo)*0.07);
  const x=t=>55+920*(t-start)/(end-start),y=v=>330-280*(v-(lo-margin))/(hi-lo+2*margin);
  svg.append(el('rect',{x:0,y:0,width:1000,height:370,fill:'#101b28'}));
  for(let i=0;i<=4;i++){const yy=50+70*i;svg.append(el('line',{x1:55,y1:yy,x2:975,y2:yy,stroke:'#314354'}));}
  if($('prices').checked&&prices.length){svg.append(el('polyline',{points:prices.map(r=>x(r.event_end_ms)+','+y(r.value)).join(' '),stroke:'#6ecfc1','stroke-width':2.5,fill:'none'}));}
  if($('forecast').checked)for(const p of forecast){svg.append(el('circle',{cx:x(p.target_event_end_ms),cy:y(p.value),r:4.5,fill:'#ffb664'}));}
  if(asOf>=start&&asOf<=end){const xx=x(asOf);svg.append(el('line',{x1:xx,y1:25,x2:xx,y2:340,stroke:'#e87991','stroke-dasharray':'7,5'}));}
  for(const [t,xx,yy] of [['price',12,15],['UTC ms '+start+' → '+end,55,362],['min '+lo.toPrecision(7)+' / max '+hi.toPrecision(7),700,18]]){const node=el('text',{x:xx,y:yy,fill:'#d9e5ef','font-size':13});node.textContent=t;svg.append(node)}
  $('counts').textContent='Available price bars: '+prices.length+' · Causally eligible forecasts: '+forecast.length+' · No verified market data or future price claims';
  issue('SYNTHETIC · UNATTESTED · READ_ONLY · NO_TRADING');
 }
 $('upload').onchange=async e=>{try{const f=e.target.files[0];if(!f)return;if(f.size>2*1024*1024)throw Error('FILE_LIMIT');const p=validate(JSON.parse(await f.text()));packet=p;
  const rows=p.observed_prices;$('from').value=rows[0].event_end_ms;$('to').value=Math.max(rows.at(-1).event_end_ms,...p.forecast_points.map(f=>f.target_event_end_ms));
  $('asof').value=rows.at(-1).available_at_ms;$('identity').textContent='Dataset '+p.dataset_id+' · snapshot '+p.snapshot_fingerprint+' · market '+JSON.stringify(p.market)+' · receipt '+p.handoff_sha256+' (not independently verified)';
  draw();
 }catch(err){packet=null;$('chart').replaceChildren();issue('IMPORT_REJECTED: '+err.message)}finally{e.target.value=''}};
 for(const id of ['from','to','asof','mode','prices','forecast'])$(id).addEventListener('change',draw);
 $('fit').onclick=()=>{if(!packet)return;const p=packet.observed_prices;$('from').value=p[0].event_end_ms;$('to').value=Math.max(p.at(-1).event_end_ms,...packet.forecast_points.map(x=>x.target_event_end_ms));draw()};
})();

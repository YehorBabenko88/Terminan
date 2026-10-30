/* Viewport projection and inert trace presentation; no scientific calculations. */
(function(root){
'use strict';
let data=[],makeSvg,range=null,identity=0;
const states=new WeakMap();
const $=id=>document.getElementById(id);
function state(e){if(!states.has(e))states.set(e,{id:++identity,name:'Эксперимент '+identity,hidden:new Set()});return states.get(e)}
function domain(){let lo=Infinity,hi=-Infinity;for(const e of data)for(const o of e.result.outputs)for(const t of o.timestamps){lo=Math.min(lo,t);hi=Math.max(hi,t)}return Number.isFinite(lo)?[lo,Math.max(lo+1,hi)]:[0,1]}
function time(t){const d=new Date(t);return Number.isFinite(d.getTime())?d.toISOString().replace('1970-01-01T','').replace('.000Z','Z'):String(t)+' ms'}
function changeZoom(f){const [lo,hi]=range||domain(),middle=lo+(hi-lo)/2,full=domain(),span=Math.max(1,Math.min(full[1]-full[0],(hi-lo)*f));range=[middle-span/2,middle+span/2];clamp();paint()}
function clamp(){const [lo,hi]=domain(),span=Math.min(hi-lo,range[1]-range[0]);if(range[1]-range[0]>span)range=[lo,hi];if(range[0]<lo)range=[lo,lo+span];if(range[1]>hi)range=[hi-span,hi]}
function pan(direction){const d=range||domain(),step=(d[1]-d[0])*.25;range=[d[0]+step*direction,d[1]+step*direction];clamp();paint()}
function render(experiments,svg){data=experiments;makeSvg=svg;if(!data.length)range=null;if(range)clamp();paint();legend()}
function legend(){const box=$('seriesLegend');box.replaceChildren();for(const e of data){const s=state(e);for(const o of e.result.outputs){const label=document.createElement('label'),input=document.createElement('input');input.type='checkbox';input.checked=!s.hidden.has(o.node+':'+o.port);input.onchange=()=>{input.checked?s.hidden.delete(o.node+':'+o.port):s.hidden.add(o.node+':'+o.port);paint()};label.style.color=e.color;label.append(input,document.createTextNode(s.name+' / '+(e.snapshot.nodes.find(n=>n.id===o.node)?.label||o.node)+' ['+o.node+':'+o.port+']'+' · '+o.unit));box.append(label);}}}
function paint(){
 if(!makeSvg)return;const svg=makeSvg,chart=$('chart');chart.replaceChildren();const [t0,t1]=range||domain();$('chartWindow').textContent=data.length?time(t0)+' → '+time(t1):'Нет результатов';
 const units=[...new Set(data.flatMap(e=>e.result.outputs.filter(o=>!state(e).hidden.has(o.node+':'+o.port)).map(o=>o.unit)))];chart.setAttribute('viewBox',`0 0 1000 ${Math.max(1,units.length)*270}`);
 const defs=svg('defs'),clip=svg('clipPath',{id:'resultClip'});clip.append(svg('rect',{x:40,y:25,width:940,height:Math.max(1,units.length)*270-50}));defs.append(clip);chart.append(defs);
 units.forEach((unit,lane)=>{
  const rows=data.flatMap(e=>e.result.outputs.filter(o=>o.unit===unit&&!state(e).hidden.has(o.node+':'+o.port)).map(o=>({o,e})));
  let low=Infinity,high=-Infinity;for(const {o}of rows)for(const v of o.values){low=Math.min(low,v);high=Math.max(high,v)}
  const scale=Math.max(1,Math.abs(low),Math.abs(high)),lower=low/scale,span=high/scale-lower||1,y0=lane*270;
  chart.append(svg('text',{x:12,y:y0+18,fill:'#c3dce0','font-size':12},unit+' · ['+low+', '+high+']'));
  for(let i=0;i<=4;i++){const t=t0+(t1-t0)*i/4,x=40+940*i/4;chart.append(svg('line',{x1:x,y1:y0+30,x2:x,y2:y0+220,stroke:'#28414b'}),svg('text',{class:'time-tick',x,y:y0+245,fill:'#91b3bc','font-size':9,'text-anchor':i===4?'end':'start'},time(t)));}
  rows.forEach(({o,e},i)=>{const points=o.values.map((v,j)=>`${40+(o.timestamps[j]-t0)*940/(t1-t0)},${y0+220-(v/scale-lower)*175/span}`).join(' ');const line=svg('polyline',{points,fill:'none',stroke:e.color,'stroke-width':2,'data-unit':unit,'data-output':o.node,'data-port':o.port,'clip-path':'url(#resultClip)','stroke-dasharray':i%2?'7 3':'none'});line.append(svg('title',{},state(e).name+' / '+o.node+' · '+unit));chart.append(line);if(o.values.length===1)chart.append(svg('circle',{cx:40+(o.timestamps[0]-t0)*940/(t1-t0),cy:y0+220-(o.values[0]/scale-lower)*175/span,r:4,fill:e.color,'data-scalar':o.node+':'+o.port,'data-timestamp':o.timestamps[0],'clip-path':'url(#resultClip)'}));});
 });
}
function trace(e){const detail=document.createElement('details');detail.className='trace';const title=document.createElement('summary');title.textContent='Подробная трассировка Math';detail.append(title);const name=document.createElement('input');name.value=state(e).name;name.setAttribute('aria-label','Название эксперимента');name.onchange=()=>{state(e).name=name.value.slice(0,100)||'Эксперимент';legend()};detail.append(name);const search=document.createElement('input');search.type='search';search.placeholder='Найти узел в trace';search.setAttribute('aria-label','Поиск trace');detail.append(search);const table=document.createElement('table');const header=document.createElement('tr');for(const t of ['Узел','Операция','Зависимости','Единицы','Происхождение','SHA256']){const th=document.createElement('th');th.textContent=t;header.append(th)}table.append(header);for(const t of e.result.trace){const tr=document.createElement('tr');for(const v of [t.node,t.kind,JSON.stringify(t.dependencies),t.unit,JSON.stringify(t.provenance||t.knowledge||null),JSON.stringify(t.portOutputs||[{port:'value',sha256:t.outputSHA256}])]){const td=document.createElement('td');td.textContent=v||'NOT_PROVIDED';tr.append(td)}table.append(tr)}search.oninput=()=>{Array.from(table.rows).slice(1).forEach(row=>row.hidden=!row.textContent.toLocaleLowerCase().includes(search.value.toLocaleLowerCase()))};detail.append(table);return detail}
$('chartZoomIn').onclick=()=>changeZoom(.5);$('chartZoomOut').onclick=()=>changeZoom(2);$('chartPanLeft').onclick=()=>pan(-1);$('chartPanRight').onclick=()=>pan(1);$('chartReset').onclick=()=>{range=null;paint()};
$('chart').addEventListener('wheel',e=>{if(!data.length)return;e.preventDefault();changeZoom(e.deltaY<0?.8:1.25)},{passive:false});
$('chart').addEventListener('keydown',e=>{if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();pan(e.key==='ArrowLeft'?-1:1)}if(e.key==='+'||e.key==='=')changeZoom(.5);if(e.key==='-')changeZoom(2);if(e.key==='Home'){range=null;paint()}});
root.LabResults={render,trace};
})(globalThis);

/* Structural editing only. Mathematical validation and execution belong to Math. */
(function(root){
'use strict';
const LIMIT=262144,UNITS=['dimensionless','USD','USDT','BTC','1','m','km','s','min','h','kg','g','A','K','mol','cd','N','J','W','Hz','Pa','m/s','km/h','m/s²'];
const kinds={source:[],formula:['x'],model:['x'],method:['x'],knowledge:['x'],difference:['a','b'],average:['a','b'],multiply:['a','b'],divide:['a','b'],convert:['x'],lag:['x'],sum:['a','b'],'rolling-mean':['x'],derivative:['x'],integral:['x'],overlay:['a','b'],compare:['a','b'],'engine-model':['x'],hypothesis:[],result:['x']};
const fail=code=>{throw Error(code)};
const object=x=>x&&typeof x==='object'&&!Array.isArray(x);
const exact=(x,keys)=>object(x)&&Object.keys(x).every(k=>keys.includes(k));
const finite=x=>typeof x==='number'&&Number.isFinite(x);
const integer=x=>Number.isSafeInteger(x)&&x>=0;
const str=(x,n)=>typeof x==='string'&&x.length>0&&x.length<=n;
function empty(){return {schema:'terminan.scientific-lab.v1',execution_authority:false,trading_authorized:false,asOf:120000,nodes:[],edges:[],view:{x:30,y:30,zoom:1}}}
function node(kind,id,x,y){
 if(!Object.hasOwn(kinds,kind))fail('UNKNOWN_NODE');
 let parameters={};
 if(kind==='source')parameters={values:[1,2,3],timestamps:[0,60000,120000],availableAt:[0,60000,120000],sourceId:'manual-unattested',version:'1',sha256:'0'.repeat(64)};
 if(kind==='formula'||kind==='model')parameters={formula:'x+1'};
 if(kind==='knowledge')parameters={reference:{id:'unselected',sha256:'0'.repeat(64)}};
 if(kind==='rolling-mean')parameters={window:2};
 if(kind==='engine-model')parameters={model:'affine',parameters:{gain:1,offset:0}};
 if(kind==='lag')parameters={steps:1};
 if(kind==='method')parameters={method:'polynomial',parameter:2};
 if(kind==='hypothesis')parameters={schema:'terminan.hypothesis.v1',title:'Unverified hypothesis',sourceId:'manual',page:1,version:'1',attested:false};
 return {id,kind,label:kind,x,y,unit:'dimensionless',parameters};
}
function output(n){return n.kind==='hypothesis'?'knowledge':'series'}
const extensionFeatures={sum:['causal-calculus'],'rolling-mean':['causal-calculus'],derivative:['causal-calculus'],integral:['causal-calculus'],overlay:['multi-output-nodes','aligned-overlay-comparison'],compare:['multi-output-nodes','aligned-overlay-comparison'],'engine-model':['fixed-models']};
function outputs(n,cap){const names=n.kind==='result'?[]:n.kind==='overlay'?['value','reference']:n.kind==='compare'?['value','absolute','rmse','mae','bias']:['value'];return names.filter(port=>!cap||n.kind==='hypothesis'||cap.ports?.[n.kind==='engine-model'?'model':n.kind==='model'?'formula':n.kind]?.outputs?.includes(port)).map(port=>({port,type:outputType(n,port)}))}
function supported(n,cap){if(!cap)return false;const engineKind=n.kind==='engine-model'?'model':n.kind==='model'?'formula':n.kind;if(['hypothesis','result'].includes(n.kind))return true;const spec=cap.ports?.[engineKind];if(!spec||!Array.isArray(spec.inputs)||!Array.isArray(spec.outputs)||spec.inputs.length!==kinds[n.kind].length||spec.inputs.some((p,i)=>p!==kinds[n.kind][i])||!spec.outputs.includes('value')||spec.outputs.some(p=>!outputs(n).some(o=>o.port===p)))return false;return !extensionFeatures[n.kind]||(cap.apiRevision==='2.1'&&extensionFeatures[n.kind].every(f=>cap.features?.includes(f)))}
function inputs(n){const a=kinds[n.kind].map((name,i)=>({port:i,name,type:['result','formula','model','knowledge','method','convert','engine-model','sum','average','difference','multiply','divide','compare'].includes(n.kind)?'numeric':'series',unit:n.unit}));
 if(['formula','model'].includes(n.kind))a.push({port:'knowledge',name:'hypothesis',type:'knowledge',unit:null});return a;}
function outputType(n,port='value',d,seen=new Set()){if(n.kind==='compare'&&['rmse','mae','bias'].includes(port))return 'scalar';if(d&&!['source','hypothesis','overlay'].includes(n.kind)&&!seen.has(n.id)){seen.add(n.id);const edge=d.edges.find(e=>e.to===n.id&&e.port===0);if(edge){const parent=d.nodes.find(x=>x.id===edge.from);if(parent)return outputType(parent,edge.fromPort||'value',d,seen)}}return output(n)}
function validate(d,complete=false,cap=null){
 if(!exact(d,['schema','execution_authority','trading_authorized','asOf','nodes','edges','view','outputs'])||d.schema!=='terminan.scientific-lab.v1'||d.execution_authority!==false||d.trading_authorized!==false)fail('INVALID_AUTHORITY_OR_SCHEMA');
 if(!integer(d.asOf)||!Array.isArray(d.nodes)||d.nodes.length>24||!Array.isArray(d.edges)||d.edges.length>24||!exact(d.view,['x','y','zoom'])||![d.view.x,d.view.y,d.view.zoom].every(finite)||d.view.zoom<.25||d.view.zoom>2.5)fail('DOCUMENT_LIMIT');
 const ids=new Map();let compute=0,total=0;
 for(const n of d.nodes){
  if(!exact(n,['id','kind','label','x','y','unit','parameters'])||!str(n.id,32)||!/^[a-z][a-z0-9_-]*$/.test(n.id)||ids.has(n.id)||!Object.hasOwn(kinds,n.kind)||!str(n.label,100)||![n.x,n.y].every(finite)||Math.abs(n.x)>10000||Math.abs(n.y)>10000||!str(n.unit,96)||!object(n.parameters))fail('INVALID_NODE');
  const p=n.parameters;
  if(!['hypothesis','result'].includes(n.kind))compute++;
  if(n.kind==='source'){
   if(!exact(p,['values','timestamps','availableAt','sourceId','version','sha256'])||!Array.isArray(p.values)||p.values.length<2||p.values.length>2000||!p.values.every(finite)||!Array.isArray(p.timestamps)||!Array.isArray(p.availableAt)||p.timestamps.length!==p.values.length||p.availableAt.length!==p.values.length||!p.timestamps.every(integer)||!p.availableAt.every(integer)||!str(p.sourceId,128)||!str(p.version,64)||!/^([a-f0-9]{64})$/.test(p.sha256))fail('INVALID_SERIES_OR_PROVENANCE');
   total+=p.values.length;
   if(p.timestamps.some((t,i)=>t>d.asOf||p.availableAt[i]>d.asOf||(i>0&&t<=p.timestamps[i-1])))fail('TEMPORAL_OR_LOOKAHEAD');
  }else if(['formula','model'].includes(n.kind)){
   if(!exact(p,['formula'])||!str(p.formula,160))fail('INVALID_FORMULA');
  }else if(n.kind==='method'){
   if(!exact(p,['method','parameter'])||!['polynomial','sine','gaussian'].includes(p.method)||!finite(p.parameter)||Math.abs(p.parameter)>1e6)fail('INVALID_NUMERIC_PARAMETER');
  }else if(n.kind==='knowledge'){
   if(!exact(p,['reference'])||!exact(p.reference,['id','sha256'])||!str(p.reference.id,64)||!/^[a-z][a-z0-9_-]{0,63}$/.test(p.reference.id)||!/^([a-f0-9]{64})$/.test(p.reference.sha256))fail('INVALID_KNOWLEDGE_REFERENCE');
  }else if(n.kind==='rolling-mean'){
   if(!exact(p,['window'])||!Number.isSafeInteger(p.window)||p.window<1||p.window>2000)fail('INVALID_WINDOW');
  }else if(n.kind==='engine-model'){
   const fields={affine:['gain','offset'],'landau-map':['mu','beta'],'logistic-map':['r']}[p.model];
   if(!exact(p,['model','parameters'])||!fields||!exact(p.parameters,fields)||fields.some(k=>!finite(p.parameters[k])))fail('INVALID_MODEL_PARAMETERS');
  }else if(n.kind==='lag'){
   if(!exact(p,['steps'])||!Number.isSafeInteger(p.steps)||p.steps<1||p.steps>1999)fail('INVALID_NUMERIC_PARAMETER');
  }else if(n.kind==='hypothesis'){
   if(!exact(p,['schema','title','sourceId','page','version','attested'])||p.schema!=='terminan.hypothesis.v1'||!str(p.title,160)||!str(p.sourceId,128)||!str(p.version,64)||!Number.isSafeInteger(p.page)||p.page<1||p.attested!==false)fail('INVALID_KNOWLEDGE');
  }else if(Object.keys(p).length)fail('INVALID_PARAMETERS');
  ids.set(n.id,n);
 }
 if(compute>12||total>16384)fail('DOCUMENT_LIMIT');
 const edgeIds=new Set(),ports=new Set();
 for(const e of d.edges){
  if(!exact(e,['id','from','to','port','fromPort'])||!str(e.id,80)||edgeIds.has(e.id)||!ids.has(e.from)||!ids.has(e.to)||ids.get(e.from).kind==='result')fail('INVALID_EDGE');
  if(Object.hasOwn(e,'fromPort')&&typeof e.fromPort!=='string')fail('MISSING_OUTPUT_PORT');
  const a=ids.get(e.from),b=ids.get(e.to),input=inputs(b).find(p=>p.port===e.port);
  if(!outputs(a).some(p=>p.port===(e.fromPort||'value')))fail('MISSING_OUTPUT_PORT');const type=outputType(a,e.fromPort||'value',d);if(!input||!(input.type===type||input.type==='numeric'&&type!=='knowledge'||input.type==='series'&&type==='comparison-series'))fail('TYPE_MISMATCH');
  if(input.type!=='knowledge'&&!['convert','multiply','divide','formula','model','knowledge','derivative','integral','engine-model','result'].includes(b.kind)&&a.unit!==b.unit)fail('UNIT_MISMATCH');
  const key=e.to+':'+e.port;if(ports.has(key))fail('PORT_OCCUPIED');ports.add(key);edgeIds.add(e.id);
 }
 if(d.outputs!==undefined){if(!Array.isArray(d.outputs)||d.outputs.length>64)fail('OUTPUT_LIMIT');const refs=new Set();for(const o of d.outputs){if(!exact(o,['node','port'])||!ids.has(o.node)||!outputs(ids.get(o.node)).some(p=>p.port===o.port)||refs.has(o.node+':'+o.port))fail('INVALID_OUTPUT');refs.add(o.node+':'+o.port);}}
 const state=new Map();function visit(id){if(state.get(id)===1)fail('GRAPH_CYCLE');if(state.get(id)===2)return;state.set(id,1);for(const e of d.edges.filter(e=>e.to===id))visit(e.from);state.set(id,2)}
 d.nodes.forEach(n=>visit(n.id));
 if(complete&&cap){for(const n of d.nodes){if(!supported(n,cap))fail('UNSUPPORTED_OPERATION: '+n.kind);if(!(cap.apiRevision==='2.1'&&cap.features?.includes('compound-units-v1'))&&!cap.units?.includes(n.unit)&&!UNITS.includes(n.unit))fail('UNSUPPORTED_UNIT');if(n.kind==='engine-model'&&!cap.models?.includes(n.parameters.model))fail('UNSUPPORTED_MODEL');}for(const o of d.outputs||[])if(!outputs(ids.get(o.node),cap).some(p=>p.port===o.port))fail('UNSUPPORTED_OUTPUT_PORT');for(const e of d.edges)if(!outputs(ids.get(e.from),cap).some(p=>p.port===(e.fromPort||'value')))fail('UNSUPPORTED_OUTPUT_PORT');}
 if(complete){if(compute<2)fail('EMPTY_GRAPH');for(const n of d.nodes)for(const p of inputs(n).filter(p=>p.type!=='knowledge'))if(!ports.has(n.id+':'+p.port))fail('MISSING_PORT: '+n.label+' / '+p.name);}
 if(new TextEncoder().encode(JSON.stringify(d)).length>LIMIT)fail('DOCUMENT_LIMIT');return d;
}
function parse(text){if(new TextEncoder().encode(text).length>LIMIT)fail('DOCUMENT_LIMIT');return validate(JSON.parse(text))}
function connect(d,from,to,port,fromPort='value'){const edge={id:'e-'+from+(fromPort==='value'?'':'-'+fromPort)+'-'+to+'-'+port,from,to,port,...(fromPort==='value'?{}:{fromPort})};const candidate={...d,edges:[...d.edges,edge]};validate(candidate);d.edges=candidate.edges;return edge;}
function disconnect(d,id){d.edges=d.edges.filter(e=>e.id!==id)}
function remove(d,id){if(d.outputs)d.outputs=d.outputs.filter(o=>o.node!==id);d.nodes=d.nodes.filter(n=>n.id!==id);d.edges=d.edges.filter(e=>e.from!==id&&e.to!==id)}
const api={empty,node,inputs,outputs,supported,extensionFeatures,outputType,validate,parse,connect,disconnect,remove,UNITS,kinds,LIMIT};
if(typeof module!=='undefined')module.exports=api;root.LabGraph=api;
})(typeof globalThis!=='undefined'?globalThis:this);

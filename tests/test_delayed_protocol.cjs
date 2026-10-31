const {test}=require('node:test'),assert=require('node:assert/strict');
const G=require('../terminan/lab_graph.js'),P=require('../terminan/lab_protocol.js');
test('editor and cryptographic protocol preserve delayed source clocks without executing Math',async()=>{
 const d=G.empty();d.asOf=121000;const n=G.node('source','s',0,0);
 n.unit='USDT/BTC';n.parameters={values:[101,101],timestamps:[60000,120000],availableAt:[60500,120500],sourceId:'fixture',version:'1',sha256:'a'.repeat(64)};d.nodes=[n];
 assert.doesNotThrow(()=>G.validate(d));
 const source={id:'s',kind:'source',type:'series',unit:n.unit,...n.parameters,provenance:{sourceId:'fixture',version:'1',sha256:'a'.repeat(64)}};
 delete source.sourceId;delete source.version;delete source.sha256;
 const q={schema:'math.scientific.graph.v2',mode:'HISTORICAL_RESEARCH',execution_authority:false,asOf:d.asOf,nodes:[source],edges:[],outputs:[{node:'s',port:'value'}]};
 const output={type:'series',unit:n.unit,values:n.parameters.values,timestamps:n.parameters.timestamps,availableAt:n.parameters.availableAt};
 const r={schema:'math.scientific.result.v2',status:'RESEARCH_ONLY',source:'CALLER_SUPPLIED_UNATTESTED',mathematicallyVerified:false,execution_authority:false,training_authorized:false,trading_authorized:false,
  requestSHA256:await P.requestDigest(q),order:['s'],outputs:[{node:'s',port:'value',...output}],trace:[{node:'s',kind:'source',definitionSHA256:await P.digest(source),dependencies:[],unit:n.unit,type:'series',outputSHA256:await P.digest(output),provenance:source.provenance,knowledge:null}]};
 const cap={ports:{source:{inputs:[],outputs:['value']}},knowledge:[]};await P.verify(r,q,cap);
 const future=structuredClone(d);future.nodes[0].parameters.availableAt[1]=121001;assert.throws(()=>G.validate(future),/TEMPORAL|LOOKAHEAD/);
});

test('real Math comparison scalars retain final event time and latest causal publication',async()=>{
 const path=require('node:path'),{pathToFileURL}=require('node:url');
 const M=await import(pathToFileURL(path.join(process.env.MATH_REPO||path.resolve('../math-v21'),'src/scientific-engine.mjs')).href);
 const source=(id,values,availableAt)=>({id,kind:'source',type:'series',unit:'dimensionless',values,timestamps:[1000,2000],availableAt,provenance:{sourceId:id,version:'1',sha256:'a'.repeat(64)}});
 const q={schema:'math.scientific.graph.v2',mode:'HISTORICAL_RESEARCH',execution_authority:false,asOf:3000,
  nodes:[source('a',[2,4],[2500,2100]),source('b',[1,2],[1500,2900]),{id:'c',kind:'compare'}],
  edges:[{from:{node:'a',port:'value'},to:{node:'c',port:'a'}},{from:{node:'b',port:'value'},to:{node:'c',port:'b'}}],
  outputs:[{node:'a',port:'value'},{node:'b',port:'value'},...['value','absolute','rmse','mae','bias'].map(port=>({node:'c',port}))]};
 const r=M.executeScientificGraph(q),cap=M.scientificCapabilities();
 for(const port of ['rmse','mae','bias']){const o=r.outputs.find(o=>o.node==='c'&&o.port===port);assert.deepEqual(o.timestamps,[2000]);assert.deepEqual(o.availableAt,[2900]);}
 await P.verify(r,q,cap);
 for(const port of ['rmse','mae','bias']){
  const bad=structuredClone(r),o=bad.outputs.find(o=>o.node==='c'&&o.port===port);o.availableAt=[2000];
  const {node,port:outputPort,...payload}=o,t=bad.trace.find(t=>t.node==='c');
  t.portOutputs.find(p=>p.port===outputPort).sha256=await P.digest(payload);
  await assert.rejects(P.verify(bad,q,cap),/TEMPORAL_PROPAGATION_MISMATCH/);
 }
});

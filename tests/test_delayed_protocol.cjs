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

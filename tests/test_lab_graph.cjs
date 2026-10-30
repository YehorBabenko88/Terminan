const {test}=require('node:test');
const assert=require('node:assert/strict');
const G=require('../terminan/lab_graph.js');
function doc(){const d=G.empty();d.nodes=[G.node('source','s',0,0),G.node('formula','f',300,0),G.node('formula','g',600,0)];return d;}
test('two formulas connect freely; deletion and occupied port require explicit relink',()=>{
 const d=doc();G.connect(d,'s','f',0);G.connect(d,'f','g',0);G.validate(d,true);
 assert.equal(d.edges.length,2);assert.throws(()=>G.connect(d,'s','g',0),/PORT_OCCUPIED/);
 G.disconnect(d,d.edges[1].id);G.connect(d,'s','g',0);assert.equal(d.edges[1].from,'s');
 G.remove(d,'s');assert.equal(d.edges.length,0);assert.throws(()=>G.validate(d,true),/MISSING_PORT/);
});
test('cycle, type and unit failures leave graph untouched',()=>{
 const d=doc();G.connect(d,'f','g',0);assert.throws(()=>G.connect(d,'g','f',0),/CYCLE/);assert.equal(d.edges.length,1);
 d.nodes.push(G.node('hypothesis','e',0,0));assert.throws(()=>G.connect(d,'s','e',0),/TYPE/);
 d.nodes.push(G.node('average','a',0,0));d.nodes[0].unit='USD';assert.throws(()=>G.connect(d,'s','a',0),/UNIT/);
});
test('bounded transactional import rejects authority, nonfinite parameters and malicious fields',()=>{
 const d=doc();const text=JSON.stringify(d);assert.deepEqual(G.parse(text),d);
 for(const mutate of [x=>x.execution_authority=true,x=>x.nodes[0].x=Infinity,x=>x.nodes[1].parameters.formula='x'.repeat(161),x=>x.nodes[0].parameters.values=[1,'2'],x=>x.nodes[0].parameters.extra='javascript:evil']){
  const bad=structuredClone(d);mutate(bad);assert.throws(()=>G.validate(bad));
 }
 assert.throws(()=>G.parse(' '.repeat(262145)),/LIMIT/);
 assert.throws(()=>G.parse('{!'));assert.equal(JSON.stringify(d),text);
});
test('hypotheses retain versioned unattested citations and result sinks are typed',()=>{
 const d=doc();d.nodes.push(G.node('hypothesis','h',0,0),G.node('result','r',0,0));
 G.connect(d,'h','f','knowledge');G.connect(d,'f','r',0);G.validate(d);
 d.nodes[3].parameters.attested=true;assert.throws(()=>G.validate(d),/KNOWLEDGE/);
});
test('scientific methods require finite bounded parameters and allow explicit SI conversion',()=>{
 const d=G.empty();d.nodes=[G.node('source','s',0,0),G.node('method','m',300,0),G.node('convert','c',600,0)];
 G.connect(d,'s','m',0);G.connect(d,'m','c',0);G.validate(d,true);
 d.nodes[1].parameters.parameter=NaN;assert.throws(()=>G.validate(d),/PARAMETER/);
});

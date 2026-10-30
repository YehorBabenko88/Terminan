/* Catalogue metadata only. The Math server owns definitions and execution. */
(function(root){
'use strict';
function entries(c){
 if(!c||c.schema!=='math.scientific.capabilities.v2'||['execution_authority','training_authorized','trading_authorized','mathematicallyVerified'].some(k=>c[k]!==false)||!Array.isArray(c.methods)||c.methods.length>32||new Set(c.methods).size!==c.methods.length||!Array.isArray(c.knowledge)||c.knowledge.length>64||!c.ports)throw Error('UNTRUSTED_CATALOG');
 if(c.apiRevision!==undefined&&typeof c.apiRevision!=='string'||c.features!==undefined&&(!Array.isArray(c.features)||c.features.length>32||c.features.some(f=>typeof f!=='string'||f.length>64))||c.models!==undefined&&(!Array.isArray(c.models)||c.models.length>16||new Set(c.models).size!==c.models.length))throw Error('UNTRUSTED_CAPABILITIES');
 for(const p of Object.values(c.ports)){if(!p||!Array.isArray(p.inputs)||!Array.isArray(p.outputs)||p.inputs.length>8||p.outputs.length>8||[...p.inputs,...p.outputs].some(v=>typeof v!=='string'||v.length>32)||new Set(p.inputs).size!==p.inputs.length||new Set(p.outputs).size!==p.outputs.length)throw Error('UNTRUSTED_PORT_CATALOG');}
 const items=[];
 for(const method of c.methods){if(!['polynomial','sine','gaussian'].includes(method))throw Error('UNSUPPORTED_CATALOG_METHOD');items.push({key:'method:'+method,kind:'method',label:method+' · Math',category:'Методы Math',description:'Параметризованный метод из каталога Math',parameters:{method,parameter:2},unit:'dimensionless'});}
 const G=typeof module!=='undefined'?require('./lab_graph.js'):root.LabGraph;
 for(const kind of ['sum','rolling-mean','derivative','integral','overlay','compare']){const n=G.node(kind,'probe',0,0);if(G.supported(n,c))items.push({kind,label:kind+' · Math 2.1',category:'Math 2.1',description:'Операция, объявленная каталогом Math',parameters:n.parameters,unit:n.unit});}
 for(const model of c.models||[]){if(!['affine','landau-map','logistic-map'].includes(model))continue;const n=G.node('engine-model','probe',0,0);if(G.supported(n,c))items.push({kind:'engine-model',label:model+' · Math 2.1',category:'Модели Math',description:'Фиксированная модель Math',unit:'dimensionless',parameters:{model,parameters:model==='affine'?{gain:1,offset:0}:model==='landau-map'?{mu:0,beta:1}:{r:2}}});}
 const seen=new Set();
 for(const k of c.knowledge){
  if(!k||typeof k.id!=='string'||!/^[a-z][a-z0-9_-]{0,63}$/.test(k.id)||seen.has(k.id)||!/^([a-f0-9]{64})$/.test(k.sha256)||k.confidence!=='NOT_VERIFIED'||typeof k.inputUnit!=='string'||typeof k.outputUnit!=='string')throw Error('UNTRUSTED_KNOWLEDGE_REFERENCE');
  seen.add(k.id);items.push({key:'knowledge:'+k.id,kind:'knowledge',label:k.id,category:'Знания / формулы Math',description:k.hypothesis||'NOT_VERIFIED',unit:k.outputUnit,parameters:{reference:{id:k.id,sha256:k.sha256}},metadata:k});
 }
 return items;
}
function search(items,q){const query=q.trim().toLocaleLowerCase();return items.filter(e=>[e.label,e.kind,e.category,e.description].join(' ').toLocaleLowerCase().includes(query));}
const api={entries,search};if(typeof module!=='undefined')module.exports=api;root.LabCatalog=api;
})(globalThis);

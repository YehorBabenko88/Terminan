/* Catalogue metadata only. The Math server owns definitions and execution. */
(function(root){
'use strict';
function entries(c){
 if(!c||c.schema!=='math.scientific.capabilities.v2'||['execution_authority','training_authorized','trading_authorized','mathematicallyVerified'].some(k=>c[k]!==false)||!Array.isArray(c.methods)||c.methods.length>32||new Set(c.methods).size!==c.methods.length||!Array.isArray(c.knowledge)||c.knowledge.length>64||!c.ports)throw Error('UNTRUSTED_CATALOG');
 const items=[];
 for(const method of c.methods){if(!['polynomial','sine','gaussian'].includes(method))throw Error('UNSUPPORTED_CATALOG_METHOD');items.push({key:'method:'+method,kind:'method',label:method+' · Math',category:'Методы Math',description:'Параметризованный метод из каталога Math',parameters:{method,parameter:2},unit:'dimensionless'});}
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

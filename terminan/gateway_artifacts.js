/* Local metadata consumer only. No transport, authority, artifact loading or series. */
(function(root,factory){'use strict';const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.TerminanGatewayArtifacts=api;})(globalThis,function(){
  'use strict';
  const VERSION='terminan.gateway.artifact-metadata.v1';
  const fail=code=>{throw Error(code||'INVALID_METADATA');};
  function decode(raw){
    if(typeof raw!=='string')fail();if(new TextEncoder().encode(raw).length>65536)fail('INPUT_LIMIT');
    let i=0,nodes=0;const ws=()=>{while(/[\x20\x09\x0a\x0d]/.test(raw[i]||'!'))i++;};
    const count=()=>{if(++nodes>4096)fail('INPUT_LIMIT');};
    function str(){const start=i++;while(i<raw.length){const c=raw[i++];if(c==='"'){let s;try{s=JSON.parse(raw.slice(start,i));}catch{fail();}if(s.length>256)fail('INPUT_LIMIT');if(/[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/u.test(s))fail();return s;}if(c==='\\')i++;}fail();}
    function value(depth){count();if(depth>8)fail('INPUT_LIMIT');ws();const c=raw[i];
      if(c==='"')return str();
      if(c==='{'||c==='['){i++;ws();const object=c==='{',out=object?Object.create(null):[],seen=new Set();let size=0;const close=object?'}':']';if(raw[i]===close){i++;return out;}
        while(i<raw.length){if(++size>32)fail('INPUT_LIMIT');ws();let key;if(object){if(raw[i]!=='"')fail();count();key=str();if(seen.has(key))fail('DUPLICATE_KEY');seen.add(key);ws();if(raw[i++]!==':')fail();}const v=value(depth+1);if(object)out[key]=v;else out.push(v);ws();const end=raw[i++];if(end===close)return out;if(end!==',')fail();}fail();
      }
      for(const [token,v]of [['null',null],['true',true],['false',false]])if(raw.startsWith(token,i)){i+=token.length;return v;}
      // Metadata v1 has no numeric fields. Reject numeric tokens before conversion.
      fail();
    }
    const out=value(0);ws();if(i!==raw.length)fail();return out;
  }
  function closed(obj,keys){if(obj===null||typeof obj!=='object'||Array.isArray(obj)||Object.keys(obj).length!==keys.length||keys.some(k=>!Object.hasOwn(obj,k)))fail();}
  function text(s,max=256){if(typeof s!=='string'||!s.length||s.length>max||/[\x00-\x1f\x7f]/.test(s))fail();}
  function id(s){text(s,128);if(!/^[A-Za-z0-9._-]+$/.test(s))fail();}
  function choice(s,values){if(!values.includes(s))fail();}
  function refs(a){if(!Array.isArray(a)||a.length>32)fail();a.forEach(id);if(new Set(a).size!==a.length)fail();}
  function utc(s){if(typeof s!=='string'||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(s))fail();const t=Date.parse(s);if(!Number.isFinite(t)||new Date(t).toISOString()!==s.slice(0,-1)+'.000Z')fail();return t;}
  function validate(v){
    closed(v,['schema_version','experiment_id','dataset','result_digest','instrument','time','units','fidelity','simulation_status','provenance','integrity','rendering_spec','qualification']);
    if(v.schema_version!==VERSION)fail('UNSUPPORTED_SCHEMA');id(v.experiment_id);
    closed(v.dataset,['dataset_id','revision']);id(v.dataset.dataset_id);id(v.dataset.revision);
    closed(v.result_digest,['algorithm','hex']);if(v.result_digest.algorithm!=='SHA256'||typeof v.result_digest.hex!=='string'||! /^[a-f0-9]{64}$/.test(v.result_digest.hex))fail();
    closed(v.instrument,['instrument_id','venue']);id(v.instrument.instrument_id);id(v.instrument.venue);
    closed(v.time,['start_utc','end_utc','as_of_utc']);if(utc(v.time.start_utc)>utc(v.time.end_utc))fail();utc(v.time.as_of_utc);
    if(!Array.isArray(v.units)||!v.units.length||v.units.length>32)fail();const fields=new Set();for(const unit of v.units){closed(unit,['field','unit']);id(unit.field);text(unit.unit,96);if(fields.has(unit.field))fail();fields.add(unit.field);}
    closed(v.fidelity,['status','limitations']);choice(v.fidelity.status,['UNKNOWN','DECLARED']);if(!Array.isArray(v.fidelity.limitations)||v.fidelity.limitations.length>16)fail();v.fidelity.limitations.forEach(x=>text(x));
    choice(v.simulation_status,['UNKNOWN','RESEARCH_ONLY','PAPER_SIMULATION']);
    closed(v.provenance,['status','producer_id','source_head','evidence_refs']);choice(v.provenance.status,['UNATTESTED']);id(v.provenance.producer_id);if(v.provenance.source_head!==null&&(typeof v.provenance.source_head!=='string'||! /^[a-f0-9]{40}$/.test(v.provenance.source_head)))fail();refs(v.provenance.evidence_refs);
    closed(v.integrity,['status']);choice(v.integrity.status,['NOT_VERIFIED']);
    closed(v.rendering_spec,['kind','artifact_refs']);choice(v.rendering_spec.kind,['METADATA_SUMMARY']);refs(v.rendering_spec.artifact_refs);
    choice(v.qualification,['TEST_ONLY','LOCAL_UNVERIFIED']);return v;
  }
  function freeze(v){if(v&&typeof v==='object'){for(const x of Object.values(v))freeze(x);Object.freeze(v);}return v;}
  function parseArtifactMetadata(rawText=null){
    if(rawText===null)return Object.freeze({status:'UNAVAILABLE',model:null,error_code:'NO_ARTIFACT_METADATA'});
    try{return Object.freeze({status:'UNATTESTED',model:freeze(validate(decode(rawText))),error_code:null});}
    catch(error){return Object.freeze({status:'UNAVAILABLE',model:null,error_code:['INPUT_LIMIT','DUPLICATE_KEY','UNSUPPORTED_SCHEMA'].includes(error.message)?error.message:'INVALID_METADATA'});}
  }
  function renderArtifactMetadata(rootElement,rawText=null){
    const result=parseArtifactMetadata(rawText),v=result.model,doc=rootElement.ownerDocument;
    const el=(tag,text)=>{const n=doc.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
    const panel=el('section');panel.className='gateway-artifact';panel.append(el('h2','Gateway artifact metadata'));
    const status=el('p',v?v.qualification+' · UNATTESTED · NOT_VERIFIED · RUNTIME BLOCKED':'UNAVAILABLE — no usable artifact metadata');status.setAttribute('role','status');panel.append(status);
    if(v){const rows=[['Experiment',v.experiment_id],['Dataset / revision',v.dataset.dataset_id+' / '+v.dataset.revision],['Instrument / venue',v.instrument.instrument_id+' / '+v.instrument.venue],['Time range',v.time.start_utc+' → '+v.time.end_utc],['As of (declared)',v.time.as_of_utc],['Simulation',v.simulation_status],['Fidelity (declared)',v.fidelity.status],['Units (declared)',v.units.map(x=>x.field+': '+x.unit).join(' · ')],['Limitations',v.fidelity.limitations.join(' · ')],['Advertised SHA256 (bytes not verified)',v.result_digest.hex]];
      const list=el('dl');for(const [label,value]of rows)list.append(el('dt',label),el('dd',value));panel.append(list);
      panel.append(el('p','Metadata only. No artifact bytes loaded; provenance, content integrity and runtime authorization remain unverified.'));
      const details=el('details');details.append(el('summary','Complete metadata and evidence references (unverified)'),el('pre',JSON.stringify(v,null,2)));panel.append(details);
    }
    rootElement.replaceChildren(panel);return result;
  }
  return Object.freeze({parseArtifactMetadata,renderArtifactMetadata});
});

/* ROOT-approved LOCAL read-only prototype. No C3 wire, provider or authority. */
(function(root,factory){const api=factory();if(typeof module==='object')module.exports=api;else root.TerminanOperations=api;})(globalThis,function(){
  'use strict';
  // Exact approved local schema artifact SHA256 e7b90440767e7c33ed8acb2c310a5bd502ce5a727d527488350922ae0c61fcab.
  const schema={"type":"object","additionalProperties":false,"properties":{"schema":{"const":"terminan.operations.local-view.v1"},"data_mode":{"enum":["TEST_ONLY","LOCAL_CAPTURE_UNVERIFIED"]},"captured_at_utc":{"anyOf":[{"type":"string","pattern":"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z(?![\\s\\S])"},{"type":"null"}]},"coverage":{"const":"BOUNDED_CAPTURE_NOT_COMPLETE_HISTORY"},"effects_authorized":{"const":false},"source_pins":{"type":"array","items":{"type":"object","additionalProperties":false,"properties":{"id":{"enum":["inventory","supervisor","mission","ci","deployment"]},"repository":{"type":"string","maxLength":160,"pattern":"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?![\\s\\S])"},"head":{"type":"string","pattern":"^[0-9a-f]{40}(?![\\s\\S])"},"tree":{"type":"string","pattern":"^[0-9a-f]{40}(?![\\s\\S])"},"capture_sha256":{"type":"string","pattern":"^[0-9a-f]{64}(?![\\s\\S])"}},"required":["id","repository","head","tree","capture_sha256"]},"maxItems":5},"sections":{"type":"object","additionalProperties":false,"properties":{"inventory":{"type":"object","additionalProperties":false,"properties":{"state":{"enum":["UNAVAILABLE","REPORTED"]},"source_id":{"anyOf":[{"type":"string","pattern":"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}(?![\\s\\S])"},{"type":"null"}]},"has_more":{"anyOf":[{"type":"boolean"},{"type":"null"}]},"rows":{"type":"array","items":{"type":"object","additionalProperties":false,"properties":{"node_id":{"enum":["LS5","PC4","PC3","PC2","PC1","LS7"]},"declared_role":{"enum":["COORDINATOR","WORKER","UNKNOWN"]},"declared_os_edition":{"enum":["WINDOWS_11_PRO","WINDOWS_11_HOME","UNKNOWN"]},"supervisor_version":{"type":"null"},"installed_release_sha":{"type":"null"},"service_state":{"const":"UNAVAILABLE"},"evidence_refs":{"type":"array","items":{"type":"object","additionalProperties":false,"properties":{"ref":{"type":"string","pattern":"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}(?![\\s\\S])"},"sha256":{"anyOf":[{"type":"string","pattern":"^[0-9a-f]{64}(?![\\s\\S])"},{"type":"null"}]}},"required":["ref","sha256"]},"maxItems":16}},"required":["node_id","declared_role","declared_os_edition","supervisor_version","installed_release_sha","service_state","evidence_refs"]},"maxItems":6}},"required":["state","source_id","has_more","rows"],"allOf":[{"if":{"properties":{"state":{"const":"UNAVAILABLE"}}},"then":{"properties":{"rows":{"maxItems":0},"has_more":{"type":"null"}}}},{"if":{"properties":{"state":{"const":"REPORTED"}}},"then":{"properties":{"source_id":{"type":"string","pattern":"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}(?![\\s\\S])"}}}}]},"node_journal":{"type":"object","additionalProperties":false,"properties":{"state":{"enum":["UNAVAILABLE","REPORTED"]},"source_id":{"anyOf":[{"type":"string","pattern":"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}(?![\\s\\S])"},{"type":"null"}]},"has_more":{"anyOf":[{"type":"boolean"},{"type":"null"}]},"rows":{"type":"array","items":{"type":"object","additionalProperties":false,"properties":{"task_id":{"type":"string","pattern":"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}(?![\\s\\S])"},"node_id":{"enum":["LS5","PC4","PC3","PC2","PC1","LS7"]},"journal_sequence":{"type":"integer","minimum":0,"maximum":9007199254740991},"operation_type":{"enum":["READ_INVENTORY","VERIFY_ARTIFACT","VERIFY_CONFIGURATION","CHECK_SERVICE","CHECK_HEALTH","PREPARE_INSTALL","PREPARE_UPDATE","VERIFY_RELEASE","COLLECT_LOGS","REPORT_STATUS","REQUEST_DRAIN","VERIFY_BACKUP","PREPARE_ROLLBACK"]},"state":{"enum":["CREATED","VERIFIED","AUTHORIZED","PREPARED","RUNNING","VERIFYING","COMPLETED","BLOCKED","FAILED","INTERRUPTED","RECOVERY_REQUIRED","ROLLBACK_REQUIRED","CANCELLED","UNKNOWN_OUTCOME"]},"release_ref":{"anyOf":[{"type":"string","pattern":"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}(?![\\s\\S])"},{"type":"null"}]},"approval_ref":{"anyOf":[{"type":"string","pattern":"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}(?![\\s\\S])"},{"type":"null"}]},"authority_generation_ref":{"anyOf":[{"type":"string","pattern":"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}(?![\\s\\S])"},{"type":"null"}]},"result_code":{"anyOf":[{"type":"string","pattern":"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}(?![\\s\\S])"},{"type":"null"}]},"journal_integrity":{"enum":["PASS","FAIL","UNKNOWN"]},"effects_authorized":{"const":false},"physical_acceptance":{"const":"NOT_RUN"},"evidence_refs":{"type":"array","items":{"type":"object","additionalProperties":false,"properties":{"ref":{"type":"string","pattern":"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}(?![\\s\\S])"},"sha256":{"anyOf":[{"type":"string","pattern":"^[0-9a-f]{64}(?![\\s\\S])"},{"type":"null"}]}},"required":["ref","sha256"]},"maxItems":16}},"required":["task_id","node_id","journal_sequence","operation_type","state","release_ref","approval_ref","authority_generation_ref","result_code","journal_integrity","effects_authorized","physical_acceptance","evidence_refs"]},"maxItems":128}},"required":["state","source_id","has_more","rows"],"allOf":[{"if":{"properties":{"state":{"const":"UNAVAILABLE"}}},"then":{"properties":{"rows":{"maxItems":0},"has_more":{"type":"null"}}}},{"if":{"properties":{"state":{"const":"REPORTED"}}},"then":{"properties":{"source_id":{"type":"string","pattern":"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}(?![\\s\\S])"}}}}]},"development_tasks":{"type":"object","additionalProperties":false,"properties":{"state":{"enum":["UNAVAILABLE","REPORTED"]},"source_id":{"anyOf":[{"type":"string","pattern":"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}(?![\\s\\S])"},{"type":"null"}]},"has_more":{"anyOf":[{"type":"boolean"},{"type":"null"}]},"rows":{"type":"array","items":{"type":"object","additionalProperties":false,"properties":{"task_id":{"type":"string","pattern":"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}(?![\\s\\S])"},"mission_id":{"type":"string","pattern":"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}(?![\\s\\S])"},"owner":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[^\\u0000-\\u001f\\u007f]+(?![\\s\\S])"},"repository":{"type":"string","maxLength":160,"pattern":"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?![\\s\\S])"},"base_sha":{"type":"string","pattern":"^[0-9a-f]{40}(?![\\s\\S])"},"allowed_files":{"type":"array","items":{"type":"string","minLength":1,"maxLength":256,"pattern":"^[^\\u0000-\\u001f\\u007f]+(?![\\s\\S])"},"maxItems":128},"blockers":{"type":"array","items":{"type":"string","minLength":1,"maxLength":512,"pattern":"^[^\\u0000-\\u001f\\u007f]+(?![\\s\\S])"},"maxItems":32},"next_actions":{"type":"array","items":{"type":"string","minLength":1,"maxLength":512,"pattern":"^[^\\u0000-\\u001f\\u007f]+(?![\\s\\S])"},"maxItems":32},"axes":{"type":"object","additionalProperties":false,"properties":{"source":{"enum":["UNKNOWN","PASS","FAIL","BLOCKED"]},"tested":{"enum":["UNKNOWN","PASS","FAIL","BLOCKED"]},"integrated":{"enum":["UNKNOWN","PASS","FAIL","BLOCKED"]},"windows":{"enum":["UNKNOWN","PASS","FAIL","BLOCKED"]},"physical":{"enum":["UNKNOWN","PASS","FAIL","BLOCKED"]}},"required":["source","tested","integrated","windows","physical"]},"grants_node_operations":{"const":false},"native_authority":{"const":false},"evidence_refs":{"type":"array","items":{"type":"object","additionalProperties":false,"properties":{"ref":{"type":"string","pattern":"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}(?![\\s\\S])"},"sha256":{"anyOf":[{"type":"string","pattern":"^[0-9a-f]{64}(?![\\s\\S])"},{"type":"null"}]}},"required":["ref","sha256"]},"maxItems":16}},"required":["task_id","mission_id","owner","repository","base_sha","allowed_files","blockers","next_actions","axes","grants_node_operations","native_authority","evidence_refs"]},"maxItems":128}},"required":["state","source_id","has_more","rows"],"allOf":[{"if":{"properties":{"state":{"const":"UNAVAILABLE"}}},"then":{"properties":{"rows":{"maxItems":0},"has_more":{"type":"null"}}}},{"if":{"properties":{"state":{"const":"REPORTED"}}},"then":{"properties":{"source_id":{"type":"string","pattern":"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}(?![\\s\\S])"}}}}]},"ci":{"type":"object","additionalProperties":false,"properties":{"state":{"enum":["UNAVAILABLE","REPORTED"]},"source_id":{"anyOf":[{"type":"string","pattern":"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}(?![\\s\\S])"},{"type":"null"}]},"has_more":{"anyOf":[{"type":"boolean"},{"type":"null"}]},"rows":{"type":"array","items":{"type":"object","additionalProperties":false,"properties":{"pin":{"type":"object","additionalProperties":false,"properties":{"repository":{"type":"string","maxLength":160,"pattern":"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?![\\s\\S])"},"workflow_id":{"type":"integer","minimum":1,"maximum":9007199254740991},"run_id":{"type":"integer","minimum":1,"maximum":9007199254740991},"attempt":{"type":"integer","minimum":1,"maximum":9007199254740991},"source_sha":{"type":"string","pattern":"^[0-9a-f]{40}(?![\\s\\S])"},"job_id":{"type":"integer","minimum":1,"maximum":9007199254740991}},"required":["repository","workflow_id","run_id","attempt","source_sha","job_id"]},"state":{"enum":["QUEUED","RUNNING","SUCCESS","FAILURE","CANCELLED","INFRA_BLOCKED","UNKNOWN"]},"authorization_state":{"enum":["CONSUMED","NOT_APPLICABLE"]},"runner_assignment":{"anyOf":[{"type":"integer","minimum":0,"maximum":9007199254740991},{"type":"null"}]},"runner_assignment_state":{"enum":["UNASSIGNED","ASSIGNED"]},"observed_at":{"type":"integer","minimum":0,"maximum":9007199254740991},"next_at":{"type":"integer","minimum":0,"maximum":9007199254740991},"conclusion":{"anyOf":[{"type":"string","minLength":1,"maxLength":32,"pattern":"^[^\\u0000-\\u001f\\u007f]+(?![\\s\\S])"},{"type":"null"}]},"data_origin":{"const":"UNVERIFIED_CAPTURE"},"raw_sha256":{"type":"string","pattern":"^[0-9a-f]{64}(?![\\s\\S])"},"artifact_ids":{"type":"array","items":{"type":"integer","minimum":1,"maximum":9007199254740991},"maxItems":64},"evidence_refs":{"type":"array","items":{"type":"object","additionalProperties":false,"properties":{"ref":{"type":"string","pattern":"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}(?![\\s\\S])"},"sha256":{"anyOf":[{"type":"string","pattern":"^[0-9a-f]{64}(?![\\s\\S])"},{"type":"null"}]}},"required":["ref","sha256"]},"maxItems":16}},"required":["pin","state","authorization_state","runner_assignment","runner_assignment_state","observed_at","next_at","conclusion","data_origin","raw_sha256","artifact_ids","evidence_refs"]},"maxItems":64}},"required":["state","source_id","has_more","rows"],"allOf":[{"if":{"properties":{"state":{"const":"UNAVAILABLE"}}},"then":{"properties":{"rows":{"maxItems":0},"has_more":{"type":"null"}}}},{"if":{"properties":{"state":{"const":"REPORTED"}}},"then":{"properties":{"source_id":{"type":"string","pattern":"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}(?![\\s\\S])"}}}}]},"approvals":{"type":"object","additionalProperties":false,"properties":{"state":{"enum":["UNAVAILABLE","REPORTED"]},"source_id":{"anyOf":[{"type":"string","pattern":"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}(?![\\s\\S])"},{"type":"null"}]},"has_more":{"anyOf":[{"type":"boolean"},{"type":"null"}]},"rows":{"type":"array","items":{"type":"object","additionalProperties":false,"properties":{"reference":{"type":"string","pattern":"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}(?![\\s\\S])"},"target_reference":{"type":"string","pattern":"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}(?![\\s\\S])"},"reported_state":{"enum":["UNKNOWN","REPORTED_APPROVAL","CONSUMED","NOT_APPLICABLE"]},"effective_grant":{"const":false},"evidence_refs":{"type":"array","items":{"type":"object","additionalProperties":false,"properties":{"ref":{"type":"string","pattern":"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}(?![\\s\\S])"},"sha256":{"anyOf":[{"type":"string","pattern":"^[0-9a-f]{64}(?![\\s\\S])"},{"type":"null"}]}},"required":["ref","sha256"]},"maxItems":16}},"required":["reference","target_reference","reported_state","effective_grant","evidence_refs"]},"maxItems":128}},"required":["state","source_id","has_more","rows"],"allOf":[{"if":{"properties":{"state":{"const":"UNAVAILABLE"}}},"then":{"properties":{"rows":{"maxItems":0},"has_more":{"type":"null"}}}},{"if":{"properties":{"state":{"const":"REPORTED"}}},"then":{"properties":{"source_id":{"type":"string","pattern":"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}(?![\\s\\S])"}}}}]},"lifecycle":{"type":"object","additionalProperties":false,"properties":{"state":{"enum":["UNAVAILABLE","REPORTED"]},"source_id":{"anyOf":[{"type":"string","pattern":"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}(?![\\s\\S])"},{"type":"null"}]},"has_more":{"anyOf":[{"type":"boolean"},{"type":"null"}]},"rows":{"type":"array","items":{"type":"object","additionalProperties":false,"properties":{"node_id":{"enum":["LS5","PC4","PC3","PC2","PC1","LS7"]},"kind":{"enum":["RECOVERY","UPDATE","ROLLBACK","DEPLOYMENT"]},"state":{"enum":["PLAN_ONLY","BLOCKED","UNKNOWN"]},"target_release_ref":{"anyOf":[{"type":"string","pattern":"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}(?![\\s\\S])"},{"type":"null"}]},"reason_code":{"type":"string","pattern":"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}(?![\\s\\S])"},"effects_authorized":{"const":false},"evidence_refs":{"type":"array","items":{"type":"object","additionalProperties":false,"properties":{"ref":{"type":"string","pattern":"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}(?![\\s\\S])"},"sha256":{"anyOf":[{"type":"string","pattern":"^[0-9a-f]{64}(?![\\s\\S])"},{"type":"null"}]}},"required":["ref","sha256"]},"maxItems":16}},"required":["node_id","kind","state","target_release_ref","reason_code","effects_authorized","evidence_refs"]},"maxItems":32}},"required":["state","source_id","has_more","rows"],"allOf":[{"if":{"properties":{"state":{"const":"UNAVAILABLE"}}},"then":{"properties":{"rows":{"maxItems":0},"has_more":{"type":"null"}}}},{"if":{"properties":{"state":{"const":"REPORTED"}}},"then":{"properties":{"source_id":{"type":"string","pattern":"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}(?![\\s\\S])"}}}}]}},"required":["inventory","node_journal","development_tasks","ci","approvals","lifecycle"]},"operational_axes":{"type":"object","additionalProperties":false,"properties":{"local_health":{"enum":["UNKNOWN","UNAVAILABLE"]},"authority_freshness":{"enum":["UNKNOWN","UNAVAILABLE"]},"compatibility":{"enum":["UNKNOWN","UNAVAILABLE"]},"integrity":{"enum":["UNKNOWN","UNAVAILABLE"]},"replication":{"enum":["UNKNOWN","UNAVAILABLE"]}},"required":["local_health","authority_freshness","compatibility","integrity","replication"]}},"required":["schema","data_mode","captured_at_utc","coverage","effects_authorized","source_pins","sections","operational_axes"],"$schema":"https://json-schema.org/draft/2020-12/schema","$id":"urn:terminan:operations:local-view:v1:PROPOSAL","$comment":"LOCAL_UI_PROPOSAL_ONLY_NOT_C3_WIRE_OR_BACKEND_SCHEMA; ordinary JSON integer metadata is not a C3 message. ROOT ACK required before implementation."};
  const fail=(code='INVALID_PROJECTION')=>{throw new Error(code);};
  const limit=(condition)=>{if(!condition)fail('BODY_LIMIT');};
  function decode(raw){
    limit(raw.length<=262144);limit(new TextEncoder().encode(raw).length<=262144);
    let i=0,nodes=0;
    const count=()=>limit(++nodes<=16384);
    const white=()=>{while(i<raw.length&&/[ \t\r\n]/.test(raw[i]))i++;};
    function string(){
      const start=i++;let escaped=false;
      while(i<raw.length){
        const ch=raw[i++];
        limit(i-start<=6146);
        if(!escaped&&ch==='"'){
          let value;try{value=JSON.parse(raw.slice(start,i));}catch{fail();}
          limit([...value].length<=512);
          if(/[\u0000-\u001f\u007f]/.test(value)||!value.isWellFormed())fail();
          return value;
        }
        if(!escaped&&ch==='\\')escaped=true;else escaped=false;
      }
      fail();
    }
    function read(parentDepth){
      white();count();const ch=raw[i];
      if(ch==='"')return string();
      for(const [literal,value] of [['null',null],['true',true],['false',false]])if(raw.startsWith(literal,i)){i+=literal.length;return value;}
      if(ch==='{'||ch==='['){
        const depth=parentDepth+1;limit(depth<=12);i++;white();
        if(ch==='['){
          const result=[];if(raw[i]===']'){i++;return Object.freeze(result);}
          while(true){limit(result.length<128);result.push(read(depth));white();if(raw[i]===']'){i++;return Object.freeze(result);}if(raw[i++]!==',')fail();}
        }
        const result=Object.create(null);let members=0;if(raw[i]==='}'){i++;return Object.freeze(result);}
        while(true){
          white();if(raw[i]!=='"')fail();count();limit(++members<=32);const key=string();limit([...key].length<=128);
          if(Object.hasOwn(result,key))fail('DUPLICATE_KEY');white();if(raw[i++]!==':')fail();result[key]=read(depth);white();
          if(raw[i]==='}'){i++;return Object.freeze(result);}if(raw[i++]!==',')fail();
        }
      }
      const match=raw.slice(i).match(/^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?/);
      // This local DTO contains nonnegative integer metadata only; never round a token.
      if(!match||! /^(?:0|[1-9][0-9]*)$/.test(match[0])||match[0].length>16)fail();
      const value=BigInt(match[0]);if(value>9007199254740991n)fail();i+=match[0].length;return Number(value);
    }
    const value=read(0);white();if(i!==raw.length)fail();return value;
  }
  function conforms(s,v){
    if(s.anyOf&&!s.anyOf.some(x=>conforms(x,v)))return false;
    if(s.enum&&!s.enum.some(x=>Object.is(x,v)))return false;
    if(Object.hasOwn(s,'const')&&!Object.is(s.const,v))return false;
    if(s.type==='null'&&v!==null)return false;
    if(s.type==='boolean'&&typeof v!=='boolean')return false;
    if(s.type==='integer'&&(!Number.isSafeInteger(v)||v<s.minimum||v>s.maximum))return false;
    if(s.type==='string'&&typeof v!=='string')return false;
    if(s.type==='array'&&!Array.isArray(v))return false;
    if(s.type==='object'&&(v===null||typeof v!=='object'||Array.isArray(v)))return false;
    if(typeof v==='string'){
      const length=[...v].length;
      if(s.minLength!==undefined&&length<s.minLength||s.maxLength!==undefined&&length>s.maxLength)return false;
      if(s.pattern&&!new RegExp(s.pattern,'u').test(v))return false;
    }
    if(Array.isArray(v)){
      if(s.maxItems!==undefined&&v.length>s.maxItems)return false;
      if(s.items&&!v.every(x=>conforms(s.items,x)))return false;
    }
    if(s.properties){
      if(v===null||typeof v!=='object'||Array.isArray(v))return false;
      if((s.required||[]).some(k=>!Object.hasOwn(v,k)))return false;
      if(s.additionalProperties===false&&Object.keys(v).some(k=>!Object.hasOwn(s.properties,k)))return false;
      for(const key of Object.keys(s.properties))if(Object.hasOwn(v,key)&&!conforms(s.properties[key],v[key]))return false;
    }
    if(s.allOf)for(const part of s.allOf){if(part.if){if(conforms(part.if,v)&&part.then&&!conforms(part.then,v))return false;}else if(!conforms(part,v))return false;}
    return true;
  }
  const sourceKinds={inventory:['inventory'],node_journal:['supervisor'],development_tasks:['mission'],ci:['ci'],approvals:['mission','supervisor'],lifecycle:['deployment']};
  const protectedPin=['YehorBabenko88/math',409676563,42352374979,1,'2446d04624469e34aa96ed766be7a4887d6d654c',128343065197];
  function unique(rows,key){const seen=new Set();for(const row of rows){const id=key(row);if(seen.has(id))fail();seen.add(id);}}
  function semantics(v){
    unique(v.source_pins,x=>x.id);const sources=new Set(v.source_pins.map(x=>x.id));
    if(v.captured_at_utc!==null){const date=new Date(v.captured_at_utc);if(!Number.isFinite(date.getTime())||date.toISOString()!==v.captured_at_utc.replace('Z','.000Z'))fail();}
    for(const [name,section] of Object.entries(v.sections)){
      if(section.source_id!==null&&(!sources.has(section.source_id)||!sourceKinds[name].includes(section.source_id)))fail();
      if(section.state==='REPORTED'&&section.source_id===null)fail();
    }
    unique(v.sections.inventory.rows,x=>x.node_id);
    unique(v.sections.node_journal.rows,x=>x.node_id+':'+x.journal_sequence);
    unique(v.sections.node_journal.rows,x=>JSON.stringify([x.node_id,x.task_id]));
    unique(v.sections.development_tasks.rows,x=>JSON.stringify([x.mission_id,x.task_id]));
    unique(v.sections.ci.rows,x=>JSON.stringify([x.pin.repository,x.pin.workflow_id,x.pin.run_id,x.pin.attempt,x.pin.source_sha,x.pin.job_id]));
    unique(v.sections.approvals.rows,x=>x.reference);
    unique(v.sections.lifecycle.rows,x=>JSON.stringify([x.node_id,x.kind,x.target_release_ref]));
    for(const task of v.sections.development_tasks.rows)for(const p of task.allowed_files){
      if(p.startsWith('/')||p.includes('\\')||/^[A-Za-z]:/.test(p)||p.split('/').some(x=>x===''||x==='.'||x==='..'))fail();
    }
    for(const row of v.sections.ci.rows){
      const pin=row.pin,values=[pin.repository,pin.workflow_id,pin.run_id,pin.attempt,pin.source_sha,pin.job_id];
      const protectedRun=pin.run_id===protectedPin[2],exact=values.every((x,i)=>x===protectedPin[i]);
      if(protectedRun&&!exact||row.authorization_state!==(exact?'CONSUMED':'NOT_APPLICABLE'))fail();
      if(row.runner_assignment_state!==((row.runner_assignment===null||row.runner_assignment===0)?'UNASSIGNED':'ASSIGNED')||row.next_at<=row.observed_at)fail();
    }
  }
  function parseLocalProjection(rawText=null){
    if(rawText===null||rawText===undefined)return Object.freeze({status:'UNAVAILABLE',model:null,errorCode:'NO_LOCAL_PROJECTION'});
    try{
      if(typeof rawText!=='string')fail();const model=decode(rawText);
      if(model===null||typeof model!=='object'||model.schema!=='terminan.operations.local-view.v1')fail('UNSUPPORTED_SCHEMA');
      if(!conforms(schema,model))fail();semantics(model);
      return Object.freeze({status:'REPORTED_ONLY',model,errorCode:null});
    }catch(error){
      const code=['BODY_LIMIT','DUPLICATE_KEY','UNSUPPORTED_SCHEMA'].includes(error.message)?error.message:'INVALID_PROJECTION';
      return Object.freeze({status:'UNAVAILABLE',model:null,errorCode:code});
    }
  }
  const sectionNames={inventory:'Declared inventory — installed facts unavailable',node_journal:'Local journal claims — not operational facts',development_tasks:'DEVELOPMENT CLAIMS — NOT VERIFIED',ci:'CI observations — UNVERIFIED_CAPTURE',approvals:'Approval references — no effective grant',lifecycle:'Recovery / update / rollback — PLAN ONLY'};
  const notes={inventory:'Supervisor version, installed release and service facts are UNAVAILABLE. Declared OS/role does not qualify a node.',node_journal:'Journal integrity reports only a local receipt chain. Authority generation / approval: REFERENCE ONLY. AUTHORIZED and COMPLETED are local history, not operational permission.',development_tasks:'Even reported physical PASS is an unverified DEVELOPMENT claim. Tasks never become Node Operations.',ci:'UNVERIFIED_CAPTURE is not hosted CI acceptance, runtime health or operation permission. Runner 0 / null is UNASSIGNED; queue age grants nothing.',approvals:'CONSUMED and NOT_APPLICABLE are non-authorizing observations. No token, approval renewal or effect exists here.',lifecycle:'Inactive plans and target-release references do not establish installation, containment, recovery or rollback success.'};
  const css=':host{color-scheme:dark}.ops-view{background:#0d1420;color:#e0e8f2;font:14px system-ui;padding:24px;border-radius:14px}.ops-view h1{font-size:26px}.ops-banner{background:#332b18;color:#ffe0a0;padding:16px;border:1px solid #78602b;border-radius:8px}.ops-axes{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:20px 0}.ops-card,.ops-section{background:#151e2c;border:1px solid #2a394f;padding:16px;border-radius:10px}.ops-section{margin-top:16px}.ops-section p{color:#a7b9cf}.ops-table{overflow:auto}.ops-view table{border-collapse:collapse;width:100%;font-size:12px}.ops-view th,.ops-view td{border-bottom:1px solid #314157;text-align:left;padding:8px;vertical-align:top;min-width:100px}.ops-view details{max-width:360px}.ops-view summary{cursor:pointer;color:#b8cbe1}.ops-view td{overflow-wrap:anywhere;max-width:360px}.ops-view pre{white-space:pre-wrap;word-break:break-word;max-width:360px;margin:0}.ops-view button{padding:10px;margin:6px;background:#202c3b;color:#a6b0bd;border:1px solid #435065;border-radius:7px}.ops-meta{color:#a7b9cf}';
  function renderOperations(rootElement,rawText=null){
    const result=parseLocalProjection(rawText),model=result.model,doc=rootElement.ownerDocument;
    const el=(tag,text)=>{const n=doc.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
    const container=el('div');container.className='ops-view';const style=el('style',css);container.append(style);
    container.append(el('p','TERMINAN / LOCAL READ-ONLY PROTOTYPE'),el('h1','Operations Dashboard'));
    const banner=el('p',model?(model.data_mode==='TEST_ONLY'?'TEST_ONLY — fixture data, not operational facts':'LOCAL CAPTURE UNVERIFIED — no operational authority'):'UNAVAILABLE — no usable local projection');
    banner.className='ops-banner';banner.setAttribute('role','status');container.append(banner);
    container.append(el('p',model?'Capture time (unverified): '+(model.captured_at_utc||'UNKNOWN')+' · '+model.coverage:'UNKNOWN source, health, installed release and service state. No provider is called.'));
    const axes=el('div');axes.className='ops-axes';
    for(const name of ['local_health','authority_freshness','compatibility','integrity','replication']){const card=el('section');card.className='ops-card';card.append(el('h2',name.replaceAll('_',' ')),el('strong',model?model.operational_axes[name]:'UNKNOWN'));axes.append(card);}container.append(axes);
    for(const name of Object.keys(sectionNames)){
      const block=el('section');block.className='ops-section';block.append(el('h2',sectionNames[name]),el('p',notes[name]));
      const section=model?model.sections[name]:null;
      block.append(el('p',section?section.state+' · source '+(section.source_id||'UNKNOWN')+' · More captured rows: '+(section.has_more===null?'UNKNOWN':String(section.has_more)):'UNAVAILABLE'));
      if(!section||!section.rows.length)block.append(el('p',section&&section.state==='REPORTED'?'No rows in this bounded capture; not complete history.':'UNAVAILABLE — no admitted operational data or usable local capture.'));
      else{
        const wrap=el('div');wrap.className='ops-table';const table=el('table'),thead=el('thead'),header=el('tr');
        const columns={inventory:['node_id','declared_role','declared_os_edition','service_state'],node_journal:['node_id','task_id','state','journal_integrity'],development_tasks:['owner','task_id','axes'],ci:['run','attempt','job','source','state','runner_assignment_state'],approvals:['reference','target_reference','reported_state'],lifecycle:['node_id','kind','state']};
        const label=key=>({node_id:'Node',task_id:'Task',declared_role:'Declared role',declared_os_edition:'Declared OS',service_state:'Service',journal_integrity:'Local receipt integrity',axes:'Reported development claims',runner_assignment_state:'Runner',source:'Source',run:'Run',attempt:'Attempt',job:'Job'}[key]||key.charAt(0).toUpperCase()+key.slice(1).replaceAll('_',' '));
        const keys=columns[name].filter(key=>name==='ci'||section.rows.some(row=>Object.hasOwn(row,key)));
        for(const key of [...keys,'Details'])header.append(el('th',label(key)));thead.append(header);table.append(thead);const body=el('tbody');
        for(const row of section.rows){const tr=el('tr');for(const key of keys){const td=el('td');let value=name==='ci'&&['run','attempt','job','source'].includes(key)?row.pin[{run:'run_id',attempt:'attempt',job:'job_id',source:'source_sha'}[key]]:row[key];
          if(key==='axes'){for(const [axis,claim] of Object.entries(value))td.append(el('div','Reported '+axis+': '+claim+' (UNVERIFIED)'));}
          else td.textContent=value===null||value===undefined?'UNAVAILABLE':String(value);tr.append(td);}
          const td=el('td'),details=el('details');details.append(el('summary','Source and evidence (unverified)'),el('pre',JSON.stringify(row,null,2)));td.append(details);tr.append(td);body.append(tr);
        }table.append(body);wrap.append(table);block.append(wrap);
      }
      container.append(block);
    }
    const sources=el('section');sources.className='ops-section';sources.append(el('h2','Public source / evidence references — UNVERIFIED'));const sourceDetails=el('details');sourceDetails.append(el('summary','Expand source pins and capture hashes (unverified)'),el('pre',model?JSON.stringify(model.source_pins,null,2):'UNAVAILABLE'));sources.append(sourceDetails);container.append(sources);
    const controls=el('section');controls.className='ops-section';controls.append(el('h2','Controls disabled — no effect handlers'));
    for(const name of ['Run task','Approve','Update','Rollback']){const button=el('button',name);button.disabled=true;button.setAttribute('disabled','');button.setAttribute('aria-disabled','true');controls.append(button);}container.append(controls);
    rootElement.replaceChildren(container);return result;
  }
  return Object.freeze({parseLocalProjection,renderOperations});
});

/* Strict TEST_ONLY fixture projections; no controller, native bridge or backend. */
'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const SOURCE=path.resolve(__dirname,'../../terminan/operations/dashboard.js');
const IDS=[
  'missing_input_pure_unavailable_no_io','strict_version_and_unknown_fields_reject',
  'duplicate_key_reject_before_projection','byte_depth_node_member_string_array_caps',
  'source_pin_link_and_unique_row_ids','unsupported_installed_release_service_facts_reject',
  'journal_completed_authorized_never_operational_grant','journal_integrity_pass_never_promotes_health_or_other_axes',
  'development_physical_pass_remains_unverified_claim','dev_tasks_never_cast_to_node_operations',
  'ci_runner_zero_unassigned_queued_not_running','ci_success_unverified_not_operational_or_hosted_acceptance',
  'protected_consumed_ordinary_not_applicable_no_grant','ci_unknown_conflict_never_infra_from_age',
  'test_only_banner_persistent_and_local_capture_banner_distinct','render_invalid_input_clears_previous_capture',
  'text_content_only_no_html_or_secret_log_exposure','all_controls_disabled_no_effect_handlers_or_provider_calls',
  'journal_current_task_identity_allows_multiple_tasks_per_capture',
  'mission_task_tuple_identity_has_no_delimiter_collision',
  'ci_pin_identity_ignores_object_key_order',
  'presentation_details_collapsed_preserve_hashes_and_qualifiers',
];
function api(){assert.ok(fs.existsSync(SOURCE),'MISSING_OPERATIONS_DASHBOARD');return require(SOURCE);}
const sha='a'.repeat(64),head='b'.repeat(40),tree='c'.repeat(40);
function fixture(){
  const sections={};for(const k of ['inventory','node_journal','development_tasks','ci','approvals','lifecycle'])sections[k]={state:'UNAVAILABLE',source_id:null,has_more:null,rows:[]};
  return {schema:'terminan.operations.local-view.v1',data_mode:'TEST_ONLY',captured_at_utc:'2026-11-07T12:00:00Z',coverage:'BOUNDED_CAPTURE_NOT_COMPLETE_HISTORY',effects_authorized:false,
    source_pins:['inventory','supervisor','mission','ci','deployment'].map(id=>({id,repository:'fixture/readonly',head,tree,capture_sha256:sha})),sections,
    operational_axes:{local_health:'UNKNOWN',authority_freshness:'UNKNOWN',compatibility:'UNKNOWN',integrity:'UNKNOWN',replication:'UNKNOWN'}};
}
function reported(v,section,rows){v.sections[section]={state:'REPORTED',source_id:({node_journal:'supervisor',development_tasks:'mission',approvals:'mission',lifecycle:'deployment'})[section]||section,has_more:false,rows};return v;}
function inventory(){return {node_id:'LS5',declared_role:'COORDINATOR',declared_os_edition:'WINDOWS_11_PRO',supervisor_version:null,installed_release_sha:null,service_state:'UNAVAILABLE',evidence_refs:[]};}
function journal(){return {task_id:'fixture-task',node_id:'LS5',journal_sequence:1,operation_type:'REPORT_STATUS',state:'COMPLETED',release_ref:'fixture-release',approval_ref:null,authority_generation_ref:'11111111-1111-4111-8111-111111111111',result_code:'LOCAL_RECEIPTS_ONLY',journal_integrity:'PASS',effects_authorized:false,physical_acceptance:'NOT_RUN',evidence_refs:[]};}
function development(){return {task_id:'dev-1',mission_id:'mission-1',owner:'fixture owner',repository:'fixture/repository',base_sha:head,allowed_files:['tests/local.cjs'],blockers:[],next_actions:['Review only'],axes:{source:'PASS',tested:'PASS',integrated:'UNKNOWN',windows:'UNKNOWN',physical:'PASS'},grants_node_operations:false,native_authority:false,evidence_refs:[]};}
function ci(){return {pin:{repository:'fixture/repository',workflow_id:1,run_id:2,attempt:1,source_sha:head,job_id:3},state:'QUEUED',authorization_state:'NOT_APPLICABLE',runner_assignment:0,runner_assignment_state:'UNASSIGNED',observed_at:100,next_at:200,conclusion:null,data_origin:'UNVERIFIED_CAPTURE',raw_sha256:sha,artifact_ids:[],evidence_refs:[]};}
function parse(v){return api().parseLocalProjection(typeof v==='string'?v:JSON.stringify(v));}
function valid(v){const r=parse(v);assert.equal(r.status,'REPORTED_ONLY',r.errorCode);return r;}
function invalid(v,code){const r=parse(v);assert.equal(r.status,'UNAVAILABLE');assert.equal(r.model,null);if(code)assert.equal(r.errorCode,code);return r;}
/* Model DOM only. Real browser rendering is verified separately, never claimed here. */
class Element{
  constructor(tag,doc){this.tagName=tag;this.ownerDocument=doc;this.children=[];this.attributes={};this.disabled=false;this._text='';}
  append(...nodes){this.children.push(...nodes);}
  replaceChildren(...nodes){this.children=[...nodes];this._text='';}
  setAttribute(k,v){assert.notEqual(k,'href');assert.ok(!k.startsWith('on'));this.attributes[k]=String(v);}
  set textContent(v){this._text=String(v);this.children=[];}
  get textContent(){return this._text+this.children.map(x=>typeof x==='string'?x:x.textContent).join(' ');}
  set innerHTML(_){throw Error('HTML_INJECTION');}
  addEventListener(){throw Error('EFFECT_HANDLER_FORBIDDEN');}
}
function dom(){const doc={createElement:tag=>new Element(tag,doc)};return new Element('main',doc);}
function all(root){return [root,...root.children.flatMap(x=>typeof x==='object'?all(x):[])];}

function registerTests(){
test(IDS[0],()=>{const a=api(),r=a.parseLocalProjection();assert.deepEqual(r,{status:'UNAVAILABLE',model:null,errorCode:'NO_LOCAL_PROJECTION'});assert.ok(Object.isFrozen(r));const root=dom();a.renderOperations(root);assert.match(root.textContent,/UNAVAILABLE/);});
test(IDS[1],()=>{for(const mutate of [v=>v.schema='other',v=>v.extra='secret',v=>v.sections.inventory.token='secret',v=>v.effects_authorized=true]){const v=fixture();mutate(v);invalid(v);}const r=valid(fixture());assert.ok(Object.isFrozen(r.model.sections));assert.ok(Object.isFrozen(r.model.source_pins));});
test(IDS[2],()=>{invalid('{"schema":"x","schema":"y"}','DUPLICATE_KEY');invalid('{"schema":"x","\\u0073chema":"y"}','DUPLICATE_KEY');invalid('{"__proto__":{"polluted":true}}');assert.equal({}.polluted,undefined);});
test(IDS[3],()=>{
  for(const raw of ['x'.repeat(262145),'['.repeat(13)+'null'+']'.repeat(13),JSON.stringify(Array(129).fill(null)),JSON.stringify(Object.fromEntries(Array.from({length:33},(_,i)=>['k'+i,null]))),JSON.stringify('x'.repeat(513)),JSON.stringify(Array.from({length:128},()=>Array.from({length:2},()=>Object.fromEntries(Array.from({length:32},(_,i)=>['k'+i,''])))))])invalid(raw,'BODY_LIMIT');
  invalid(JSON.stringify(fixture()).replace('"effects_authorized":false','"effects_authorized":9007199254740993'));
  const x=fixture();x.captured_at_utc='2026-02-30T12:00:00Z';invalid(x);
});
test(IDS[4],()=>{const v=reported(fixture(),'inventory',[inventory()]);valid(v);v.sections.inventory.source_id='missing';invalid(v);v.sections.inventory.source_id='inventory';v.source_pins.push(v.source_pins[0]);invalid(v);v.source_pins.pop();v.sections.inventory.rows.push(inventory());invalid(v);});
test(IDS[5],()=>{for(const change of [{supervisor_version:'v2'},{installed_release_sha:head},{service_state:'RUNNING'}])invalid(reported(fixture(),'inventory',[{...inventory(),...change}]));valid(reported(fixture(),'inventory',[inventory()]));});
test(IDS[6],()=>{for(const state of ['COMPLETED','AUTHORIZED']){const v=reported(fixture(),'node_journal',[{...journal(),state}]);valid(v);const root=dom();api().renderOperations(root,JSON.stringify(v));assert.match(root.textContent,/REFERENCE ONLY/);assert.match(root.textContent,/not operational/i);assert.equal(v.operational_axes.authority_freshness,'UNKNOWN');}invalid(reported(fixture(),'node_journal',[{...journal(),effects_authorized:true}]));});
test(IDS[7],()=>{const r=valid(reported(fixture(),'node_journal',[journal()]));assert.equal(r.model.sections.node_journal.rows[0].journal_integrity,'PASS');assert.ok(Object.values(r.model.operational_axes).every(x=>x==='UNKNOWN'));const v=fixture();v.operational_axes.local_health='HEALTHY';invalid(v);v.operational_axes.local_health='UNKNOWN';v.operational_axes.integrity='PASS';invalid(v);});
test(IDS[8],()=>{const v=reported(fixture(),'development_tasks',[development()]);valid(v);const root=dom();api().renderOperations(root,JSON.stringify(v));assert.match(root.textContent,/DEVELOPMENT CLAIMS/);assert.match(root.textContent,/UNVERIFIED/);assert.equal(parse(v).model.operational_axes.compatibility,'UNKNOWN');});
test(IDS[9],()=>{invalid(reported(fixture(),'node_journal',[development()]));invalid(reported(fixture(),'development_tasks',[{...development(),operation_type:'REPORT_STATUS'}]));invalid(reported(fixture(),'development_tasks',[{...development(),native_authority:true}]));const v=development();v.allowed_files=['../outside'];invalid(reported(fixture(),'development_tasks',[v]));});
test(IDS[10],()=>{const v=reported(fixture(),'ci',[ci()]);assert.equal(valid(v).model.sections.ci.rows[0].state,'QUEUED');v.sections.ci.rows[0].runner_assignment_state='ASSIGNED';invalid(v);v.sections.ci.rows[0].runner_assignment=null;v.sections.ci.rows[0].runner_assignment_state='UNASSIGNED';valid(v);});
test(IDS[11],()=>{const v=reported(fixture(),'ci',[{...ci(),state:'SUCCESS',conclusion:'success',runner_assignment:12,runner_assignment_state:'ASSIGNED'}]);valid(v);const root=dom();api().renderOperations(root,JSON.stringify(v));assert.match(root.textContent,/UNVERIFIED_CAPTURE/);assert.match(root.textContent,/not hosted.*acceptance/i);assert.ok(Object.values(parse(v).model.operational_axes).every(x=>x==='UNKNOWN'));});
test(IDS[12],()=>{const row=ci();row.pin={repository:'YehorBabenko88/math',workflow_id:409676563,run_id:42352374979,attempt:1,source_sha:'2446d04624469e34aa96ed766be7a4887d6d654c',job_id:128343065197};row.authorization_state='CONSUMED';valid(reported(fixture(),'ci',[row]));row.authorization_state='NOT_APPLICABLE';invalid(reported(fixture(),'ci',[row]));row.authorization_state='CONSUMED';row.pin.attempt=2;invalid(reported(fixture(),'ci',[row]));invalid(reported(fixture(),'ci',[{...ci(),authorization_state:'CONSUMED'}]));});
test(IDS[13],()=>{for(const state of ['QUEUED','UNKNOWN']){const v=reported(fixture(),'ci',[{...ci(),state,observed_at:0,next_at:900}]);assert.equal(valid(v).model.sections.ci.rows[0].state,state);}const v=ci();v.data_origin='VERIFIED_GITHUB';invalid(reported(fixture(),'ci',[v]));});
test(IDS[14],()=>{const root=dom(),v=fixture();api().renderOperations(root,JSON.stringify(v));assert.match(root.textContent,/TEST_ONLY/);v.data_mode='LOCAL_CAPTURE_UNVERIFIED';api().renderOperations(root,JSON.stringify(v));assert.match(root.textContent,/LOCAL CAPTURE UNVERIFIED/);assert.doesNotMatch(root.textContent,/TEST_ONLY/);});
test(IDS[15],()=>{const root=dom(),v=reported(fixture(),'development_tasks',[development()]);api().renderOperations(root,JSON.stringify(v));assert.match(root.textContent,/dev-1/);api().renderOperations(root,'not-json');assert.doesNotMatch(root.textContent,/dev-1/);assert.match(root.textContent,/UNAVAILABLE/);});
test(IDS[16],()=>{const v=development();v.blockers=['<img src=x onerror="fetch(1)">'];const root=dom();api().renderOperations(root,JSON.stringify(reported(fixture(),'development_tasks',[v])));assert.match(root.textContent,/<img/);assert.ok(all(root).every(x=>!['img','script','a'].includes(x.tagName)));});
test(IDS[17],()=>{const sandbox={TextEncoder,fetch(){throw Error('NETWORK');},setInterval(){throw Error('TIMER');},setTimeout(){throw Error('TIMER');},console:new Proxy({}, {get(){throw Error('RAW_LOGGING');}})};vm.createContext(sandbox);vm.runInContext(fs.readFileSync(SOURCE,'utf8'),sandbox);assert.deepEqual(Object.keys(sandbox.TerminanOperations).sort(),['parseLocalProjection','renderOperations']);const root=dom();sandbox.TerminanOperations.renderOperations(root,JSON.stringify(fixture()));const buttons=all(root).filter(x=>x.tagName==='button');assert.ok(buttons.length>=4);assert.ok(buttons.every(x=>x.disabled));assert.ok(all(root).every(x=>!Object.keys(x.attributes).some(k=>k.startsWith('on')||k==='href')));});
test(IDS[18],()=>{const a=journal(),b={...journal(),task_id:'other-task',journal_sequence:2};valid(reported(fixture(),'node_journal',[a,b]));invalid(reported(fixture(),'node_journal',[a,{...journal(),journal_sequence:3}]));});
test(IDS[19],()=>{const a={...development(),mission_id:'a:b',task_id:'c'},b={...development(),mission_id:'a',task_id:'b:c'};valid(reported(fixture(),'development_tasks',[a,b]));});
test(IDS[20],()=>{const a=ci(),b=ci();b.pin=Object.fromEntries(Object.entries(b.pin).reverse());invalid(reported(fixture(),'ci',[a,b]));});

test(IDS[21],()=>{const v=reported(reported(fixture(),'development_tasks',[development()]),'ci',[ci()]);const root=dom();api().renderOperations(root,JSON.stringify(v));const nodes=all(root),details=nodes.filter(x=>x.tagName==='details');assert.ok(details.length>=3);assert.ok(details.every(x=>!('open' in x.attributes)&&x.open!==true));assert.ok(details.some(x=>x.textContent.includes(sha)));assert.match(root.textContent,/Reported source: PASS \(UNVERIFIED\)/);const headers=nodes.filter(x=>x.tagName==='th').map(x=>x.textContent);for(const h of ['Run','Attempt','Job','Source'])assert.ok(headers.includes(h));assert.ok(headers.every(x=>!x.includes('_')));assert.ok(nodes.filter(x=>x.tagName==='pre').every(x=>details.some(d=>all(d).includes(x))));});
}

/* Standalone source-bound qualification; only this test file and Node builtins.
 * Workflow first compiles THESE exact Git blob bytes, not a workspace shadow.
 */
function runQualified(root,expectedHead,output,expectedIds=IDS){
  const cp=require('node:child_process'),crypto=require('node:crypto');
  root=path.resolve(root);output=path.resolve(output);
  if(output===root||!path.relative(root,output).startsWith('..'+path.sep))throw Error('EVIDENCE_MUST_BE_OUTSIDE_SOURCE');
  fs.mkdirSync(output,{recursive:true});
  const receipt={qualification:'LOCAL_NODE_READONLY_COMPONENT_ONLY_NOT_NATIVE_HOME_PHYSICAL',expected_head:expectedHead,node:process.version,platform:process.platform,tests_started:false,result:'FAIL'};
  const fail=code=>{throw Error(code);};
  const digest=raw=>crypto.createHash('sha256').update(raw).digest('hex');
  const git=process.platform==='win32'?'C:/Program Files/Git/cmd/git.exe':'/usr/bin/git';
  const g=(...args)=>cp.execFileSync(git,['--no-replace-objects','--no-optional-locks','-c','core.fsmonitor=false',...args],{cwd:root,maxBuffer:134217728,stdio:['pipe','pipe','pipe']});
  function noLinks(file){
    for(let p=file;;p=path.dirname(p)){if(fs.lstatSync(p).isSymbolicLink())fail('SOURCE_LINK');if(path.dirname(p)===p)break;}
  }
  function inventory(){
    noLinks(root);
    if(g('rev-parse','HEAD').toString().trim()!==expectedHead)fail('HEAD_MISMATCH');
    if(g('for-each-ref','refs/replace').length)fail('REPLACEMENT_REF');
    const graft=path.resolve(root,g('rev-parse','--git-path','info/grafts').toString().trim());if(fs.existsSync(graft))fail('GRAFTS_FORBIDDEN');
    const allowed=['.github/workflows/operations-dashboard.yml','docs/operations/operations-dashboard-contract.md','terminan/operations/dashboard.js','tests/operations/test_dashboard.cjs'];
    const diff=g('diff','--name-status','10e07ef108d155b9ca2278eec6a8361cb92fa488',expectedHead).toString().trim().split('\n').filter(Boolean).map(line=>{const [kind,name]=line.split('\t');if(kind!=='A'||!allowed.includes(name))fail('SOURCE_SCOPE_CHANGED');return name;}).sort();
    if(JSON.stringify(diff)!==JSON.stringify(allowed))fail('SOURCE_SCOPE_INCOMPLETE');
    const entries=g('ls-tree','-rz','--full-tree',expectedHead).toString('utf8').split('\0').filter(Boolean).map(row=>{
      const [meta,name]=row.split('\t'),[mode,kind,oid]=meta.split(' ');
      if(!['100644','100755'].includes(mode)||kind!=='blob')fail('SOURCE_MODE');
      const file=path.resolve(root,name);if(!file.startsWith(root+path.sep)||name.includes('\\'))fail('SOURCE_PATH');
      return {name,oid,file};
    });
    const raw=cp.execFileSync(git,['--no-replace-objects','--no-optional-locks','-c','core.fsmonitor=false','cat-file','--batch'],{cwd:root,input:entries.map(x=>x.oid+'\n').join(''),maxBuffer:134217728});
    let offset=0;const files={};
    for(const entry of entries){
      const end=raw.indexOf(10,offset);if(end<0)fail('GIT_BATCH');const [oid,type,sizeText]=raw.subarray(offset,end).toString().split(' '),size=Number(sizeText);offset=end+1;
      if(oid!==entry.oid||type!=='blob'||!Number.isSafeInteger(size)||size<0)fail('GIT_BATCH');const blob=raw.subarray(offset,offset+size);offset+=size;
      if(raw[offset++]!==10)fail('GIT_BATCH');noLinks(entry.file);const st=fs.lstatSync(entry.file);
      if(!st.isFile()||st.nlink!==1)fail('SOURCE_FILE_IDENTITY');
      const actual=fs.readFileSync(entry.file);if(!actual.equals(blob))fail('RAW_SOURCE_MISMATCH');files[entry.name]={git_blob:entry.oid,sha256:digest(blob)};
    }
    if(offset!==raw.length)fail('GIT_BATCH');
    function walk(dir){for(const entry of fs.readdirSync(dir,{withFileTypes:true})){
      const file=path.join(dir,entry.name),relative=path.relative(root,file).split(path.sep).join('/');
      if(relative==='.git')continue;
      const st=fs.lstatSync(file);if(st.isSymbolicLink())fail('UNEXPECTED_LINK');
      if(st.isDirectory())walk(file);else if(!Object.hasOwn(files,relative))fail('UNEXPECTED_FILE');
    }}
    walk(root);if(g('status','--porcelain','--untracked-files=all').length)fail('DIRTY_SOURCE');
    return {head:expectedHead,tree:g('rev-parse',expectedHead+'^{tree}').toString().trim(),files};
  }
  try{
    for(const key of ['NODE_OPTIONS','NODE_PATH','NODE_COMPILE_CACHE','NODE_V8_COVERAGE'])if(process.env[key])fail('AMBIENT_NODE_CONFIG');
    if(process.execArgv.length!==1||process.execArgv[0]!=='--no-addons')fail('NODE_FLAGS');
    if(!/^[0-9a-f]{40}$/.test(expectedHead))fail('EXPECTED_HEAD');
    if(!Array.isArray(expectedIds)||JSON.stringify(expectedIds)!==JSON.stringify(IDS)||new Set(expectedIds).size!==22)fail('MANDATORY_INVENTORY');
    const before=inventory();receipt.before=before;
    receipt.tests_started=true;
    const run=cp.spawnSync(process.execPath,['--no-addons','--test','--test-reporter=tap',path.join(root,'tests/operations/test_dashboard.cjs')],{cwd:root,encoding:'utf8',maxBuffer:1048576,env:process.env});
    fs.writeFileSync(path.join(output,'tests.tap'),run.stdout||'');fs.writeFileSync(path.join(output,'tests.stderr.log'),run.stderr||'');
    const tap=run.stdout||'',actual=[...tap.matchAll(/^# Subtest: (.+)$/gm)].map(x=>x[1]);
    if(run.status!==0||JSON.stringify(actual)!==JSON.stringify(expectedIds))fail('MANDATORY_TESTS');
    const counts={};for(const name of ['tests','pass','fail','cancelled','skipped','todo']){const matches=[...tap.matchAll(new RegExp('^# '+name+' (\\d+)\\s*$','gm'))];if(matches.length!==1)fail('TAP_COUNTS');counts[name]=Number(matches[0][1]);}
    if(JSON.stringify(counts)!==JSON.stringify({tests:22,pass:22,fail:0,cancelled:0,skipped:0,todo:0}))fail('TAP_COUNTS');
    receipt.counts=counts;receipt.executed_ids=actual;
    const after=inventory();receipt.after=after;if(JSON.stringify(before)!==JSON.stringify(after))fail('SOURCE_CHANGED_AFTER');
    receipt.result='PASS';return receipt;
  }catch(error){receipt.failure_code=/^[A-Z_]+$/.test(error.message)?error.message:'QUALIFICATION_FAILURE';throw error;}
  finally{fs.writeFileSync(path.join(output,'source-receipt.json'),JSON.stringify(receipt,null,2)+'\n');}
}
module.exports={IDS,fixture,reported,inventory,journal,development,ci,runQualified};
if(require.main===module){
  if(process.argv[2]==='--source-bound-run'){
    try{const r=runQualified(path.resolve(__dirname,'../..'),process.argv[3],process.argv[4]);process.stdout.write(JSON.stringify({head:r.expected_head,result:r.result,tests:r.counts.tests})+'\n');}catch{process.stderr.write('OPERATIONS_SOURCE_QUALIFICATION_FAILED\n');process.exitCode=1;}
  }else registerTests();
}

/* Local source-bound tests, not runtime/physical qualification. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),cp=require('node:child_process'),crypto=require('node:crypto');
function run(root,head,out){
 root=path.resolve(root);out=path.resolve(out);if(out===root||!path.relative(root,out).startsWith('..'+path.sep))throw Error('EXTERNAL_EVIDENCE_REQUIRED');fs.mkdirSync(out,{recursive:true});
 const receipt={head,result:'FAIL',qualification:'LOCAL_METADATA_COMPONENT_NOT_RUNTIME_PHYSICAL',tests_started:false,node:process.version};
 const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
 const git=process.platform==='win32'?'C:/Program Files/Git/cmd/git.exe':'/usr/bin/git';
 const g=(...args)=>cp.execFileSync(git,['--no-replace-objects','--no-optional-locks','-c','core.fsmonitor=false',...args],{cwd:root,maxBuffer:134217728});
 function inventory(){
  if(!/^[a-f0-9]{40}$/.test(head)||g('rev-parse','HEAD').toString().trim()!==head)throw Error('HEAD_MISMATCH');
  if(g('for-each-ref','refs/replace').length||fs.existsSync(path.join(g('rev-parse','--absolute-git-dir').toString().trim(),'info/grafts')))throw Error('ALTERNATE_HISTORY');
  const changes=g('diff','--name-status','c752dff751d964c57daf3b3afe4987ea3377839b',head).toString().trim().split('\n');
  for(const line of changes){const [kind,file]=line.trim().split('\t');if(kind!=='A'||!(file==='terminan/gateway_artifacts.js'||file==='.github/workflows/gateway-artifacts.yml'||file.startsWith('tests/gateway_artifacts/')||file.startsWith('docs/gateway/artifacts/')))throw Error('OWNERSHIP_SCOPE');}
  const entries=g('ls-tree','-rz','--full-tree','HEAD').toString().split('\0').filter(Boolean),files=new Set(),items=[];
  const objects=cp.execFileSync(git,['--no-replace-objects','cat-file','--batch'],{cwd:root,input:entries.map(e=>e.split('\t')[0].split(' ')[2]+'\n').join(''),maxBuffer:134217728});let offset=0;
  for(const entry of entries){const [meta,name]=entry.split('\t'),[mode,type,oid]=meta.split(' ');if(type!=='blob'||!['100644','100755'].includes(mode))throw Error('SOURCE_MODE');files.add(name);const end=objects.indexOf(10,offset),header=objects.subarray(offset,end).toString().split(' '),size=Number(header[2]),blob=objects.subarray(end+1,end+1+size);offset=end+2+size;if(header[0]!==oid||header[1]!=='blob')throw Error('BLOB_HEADER');const file=path.join(root,name),stat=fs.lstatSync(file);if(!stat.isFile()||stat.isSymbolicLink()||stat.nlink!==1)throw Error('SOURCE_LINK');const raw=fs.readFileSync(file);if(!blob.equals(raw))throw Error('RAW_SOURCE_MISMATCH');items.push({path:name,sha256:hash(raw)});}
  function walk(dir){for(const e of fs.readdirSync(dir,{withFileTypes:true})){if(dir===root&&e.name==='.git')continue;const file=path.join(dir,e.name),rel=path.relative(root,file).split(path.sep).join('/');if(e.isSymbolicLink())throw Error('SOURCE_LINK');if(e.isDirectory())walk(file);else if(!files.has(rel))throw Error('UNTRACKED_SOURCE');}}
  if(fs.lstatSync(root).isSymbolicLink())throw Error('SOURCE_LINK');walk(root);if(g('status','--porcelain','--untracked-files=all').length)throw Error('DIRTY_SOURCE');return items;
 }
 try{
  for(const key of ['NODE_OPTIONS','NODE_PATH','NODE_COMPILE_CACHE','NODE_V8_COVERAGE'])if(process.env[key])throw Error('AMBIENT_NODE_CONFIG');
  if(JSON.stringify(process.execArgv)!==JSON.stringify(['--no-addons']))throw Error('NODE_FLAGS');
  receipt.before=inventory();const testFile=path.join(root,'tests/gateway_artifacts/test_metadata.cjs');
  const expected=['missing_input_unavailable','metadata_detached_frozen_unattested','closed_version_and_fields','decoded_duplicate_keys_reject','bounded_raw_depth_members_nodes_strings_arrays','canonical_dates_and_range','opaque_refs_no_urls_or_html','units_unique_and_bounded','digest_not_verification','simulation_never_real_orders','unsafe_numeric_tokens_reject','invalid_render_clears_previous','render_qualifiers_and_all_metadata','text_only_no_html_links_or_effects','pure_module_no_network_timers_storage_logs'];
  receipt.tests_started=true;const child=cp.spawnSync(process.execPath,['--no-addons','--test','--test-reporter=tap',testFile],{cwd:root,encoding:'utf8',maxBuffer:1048576});fs.writeFileSync(path.join(out,'tests.tap'),child.stdout||'');fs.writeFileSync(path.join(out,'tests.stderr'),child.stderr||'');
  const ids=[...(child.stdout||'').matchAll(/^# Subtest: (.+)$/gm)].map(x=>x[1]);if(child.status!==0||JSON.stringify(ids)!==JSON.stringify(expected)||!/^# tests 15$/m.test(child.stdout)||!/^# pass 15$/m.test(child.stdout)||!/^# fail 0$/m.test(child.stdout)||!/^# skipped 0$/m.test(child.stdout)||!/^# cancelled 0$/m.test(child.stdout)||!/^# todo 0$/m.test(child.stdout))throw Error('MANDATORY_TESTS');
  receipt.after=inventory();if(JSON.stringify(receipt.before)!==JSON.stringify(receipt.after))throw Error('SOURCE_CHANGED');receipt.tests=15;receipt.result='PASS';return receipt;
 }catch(e){receipt.error=/^[A-Z_]+$/.test(e.message)?e.message:'QUALIFICATION_FAILED';throw e;}finally{fs.writeFileSync(path.join(out,'source-receipt.json'),JSON.stringify(receipt,null,2)+'\n');}
}
module.exports={run};if(require.main===module){try{console.log(JSON.stringify(run(process.argv[2],process.argv[3],process.argv[4])));}catch(e){console.error(e.message);process.exitCode=1;}}

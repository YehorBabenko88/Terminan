/* Local source-bound tests, not runtime/physical qualification. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),cp=require('node:child_process'),crypto=require('node:crypto');
function run(root,head,out){
 root=path.resolve(root);out=path.resolve(out);if(out===root||!path.relative(root,out).startsWith('..'+path.sep))throw Error('EXTERNAL_EVIDENCE_REQUIRED');fs.mkdirSync(out,{recursive:true});
 const receipt={head,result:'FAIL',qualification:'PURE_EXPERIMENT_CLIENT_NOT_ENDPOINT_OR_AUTH_ACCEPTANCE',implementation_base:'22e6e7230d2f66fd22dda648a77910579812bd60',tests_started:false,node:process.version};
 const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
 const git=process.platform==='win32'?'C:/Program Files/Git/cmd/git.exe':'/usr/bin/git';
 const g=(...args)=>cp.execFileSync(git,['--no-replace-objects','--no-optional-locks','-c','core.fsmonitor=false',...args],{cwd:root,maxBuffer:134217728});
 function inventory(){
  if(!/^[a-f0-9]{40}$/.test(head)||g('rev-parse','HEAD').toString().trim()!==head)throw Error('HEAD_MISMATCH');
  if(g('for-each-ref','refs/replace').length||fs.existsSync(path.join(g('rev-parse','--absolute-git-dir').toString().trim(),'info/grafts')))throw Error('ALTERNATE_HISTORY');
  g('merge-base','--is-ancestor','22e6e7230d2f66fd22dda648a77910579812bd60',head);
  const changes=g('diff','--name-status','22e6e7230d2f66fd22dda648a77910579812bd60',head).toString().trim().split('\n');
  for(const line of changes){const [kind,file]=line.trim().split('\t');if(kind!=='A'||!(file==='terminan/experiment_view.js'||file==='.github/workflows/experiment-view.yml'||file.startsWith('tests/experiment_view/')||file.startsWith('docs/gateway/experiment-view/')))throw Error('OWNERSHIP_SCOPE');}
  const entries=g('ls-tree','-rz','--full-tree','HEAD').toString().split('\0').filter(Boolean),files=new Set(),items=[];
  const objects=cp.execFileSync(git,['--no-replace-objects','cat-file','--batch'],{cwd:root,input:entries.map(e=>e.split('\t')[0].split(' ')[2]+'\n').join(''),maxBuffer:134217728});let offset=0;
  for(const entry of entries){const [meta,name]=entry.split('\t'),[mode,type,oid]=meta.split(' ');if(type!=='blob'||!['100644','100755'].includes(mode))throw Error('SOURCE_MODE');files.add(name);const end=objects.indexOf(10,offset),header=objects.subarray(offset,end).toString().split(' '),size=Number(header[2]),blob=objects.subarray(end+1,end+1+size);offset=end+2+size;if(header[0]!==oid||header[1]!=='blob')throw Error('BLOB_HEADER');const file=path.join(root,name),stat=fs.lstatSync(file);if(!stat.isFile()||stat.isSymbolicLink()||stat.nlink!==1)throw Error('SOURCE_LINK');const raw=fs.readFileSync(file);if(!blob.equals(raw))throw Error('RAW_SOURCE_MISMATCH');items.push({path:name,sha256:hash(raw)});}
  function walk(dir){for(const e of fs.readdirSync(dir,{withFileTypes:true})){if(dir===root&&e.name==='.git')continue;const file=path.join(dir,e.name),rel=path.relative(root,file).split(path.sep).join('/');if(e.isSymbolicLink())throw Error('SOURCE_LINK');if(e.isDirectory())walk(file);else if(!files.has(rel))throw Error('UNTRACKED_SOURCE');}}
  if(fs.lstatSync(root).isSymbolicLink())throw Error('SOURCE_LINK');walk(root);if(g('status','--porcelain','--untracked-files=all').length)throw Error('DIRTY_SOURCE');return items;
 }
 try{
  for(const key of ['NODE_OPTIONS','NODE_PATH','NODE_COMPILE_CACHE','NODE_V8_COVERAGE'])if(process.env[key])throw Error('AMBIENT_NODE_CONFIG');
  if(JSON.stringify(process.execArgv)!==JSON.stringify(['--no-addons']))throw Error('NODE_FLAGS');
  receipt.before=inventory();const testFiles=['test_pure_client.cjs','test_scientific_read_prep.cjs','test_recovery_prep.cjs'].map(name=>path.join(root,'tests/experiment_view',name));
  const expected=["pure_view_path_exact_case_no_normalization", "pure_view_invalid_route_types_and_options", "pure_view_observed_byte_caps_not_json_claims", "pure_view_clear_before_load_aborts_previous", "pure_view_invalid_id_clears_and_aborts", "pure_view_denial_discards_response", "pure_view_unapproved_200_never_auth_success", "pure_view_header_and_stream_size_limits", "pure_view_depth_and_framing_across_chunks", "pure_view_stale_response_cannot_replace_new_load", "pure_view_stale_failure_cannot_replace_reset", "pure_view_cross_controller_ticket_has_no_effect", "pure_view_no_network_storage_logs_or_auth_provider", "pure_view_abort_held_reader_retains_no_payload"];
  expected.push("prep_science_local_g_artifact_is_not_read_authority","prep_science_digest_match_is_not_permission","prep_science_matching_revision_claim_is_not_current_read","prep_science_stale_revision_claim_never_renders","prep_science_owner_role_claim_is_not_rbac","prep_science_logical_history_is_not_payload_scope","prep_science_native_metadata_is_not_payload_scope","prep_science_denial_supersedes_pending_bytes","prep_science_independent_clients_do_not_share_permission","prep_science_units_simulation_provenance_are_not_a_grant");
  expected.push("prep_recovery_invalidation_clears_and_aborts","prep_recovery_unknown_signal_fails_closed","prep_recovery_late_bytes_cannot_restore","prep_recovery_manual_begin_is_not_auto_retry_or_permission","prep_recovery_old_failure_cannot_replace_new_pending","prep_recovery_isolated_clients_share_no_grant");
  receipt.tests_started=true;const child=cp.spawnSync(process.execPath,['--no-addons','--test','--test-reporter=tap',...testFiles],{cwd:root,encoding:'utf8',maxBuffer:1048576});fs.writeFileSync(path.join(out,'tests.tap'),child.stdout||'');fs.writeFileSync(path.join(out,'tests.stderr'),child.stderr||'');
  const ids=[...(child.stdout||'').matchAll(/^# Subtest: (.+)$/gm)].map(x=>x[1]);if(child.status!==0||JSON.stringify(ids.sort())!==JSON.stringify(expected.sort())||!/^# tests 30$/m.test(child.stdout)||!/^# pass 30$/m.test(child.stdout)||!/^# fail 0$/m.test(child.stdout)||!/^# skipped 0$/m.test(child.stdout)||!/^# cancelled 0$/m.test(child.stdout)||!/^# todo 0$/m.test(child.stdout))throw Error('MANDATORY_TESTS');
  receipt.after=inventory();if(JSON.stringify(receipt.before)!==JSON.stringify(receipt.after))throw Error('SOURCE_CHANGED');receipt.tests=30;receipt.result='PASS';return receipt;
 }catch(e){receipt.error=/^[A-Z_]+$/.test(e.message)?e.message:'QUALIFICATION_FAILED';throw e;}finally{fs.writeFileSync(path.join(out,'source-receipt.json'),JSON.stringify(receipt,null,2)+'\n');}
}
module.exports={run};if(require.main===module){try{console.log(JSON.stringify(run(process.argv[2],process.argv[3],process.argv[4])));}catch(e){console.error(e.message);process.exitCode=1;}}

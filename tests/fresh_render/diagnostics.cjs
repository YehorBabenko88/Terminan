'use strict';
const PHASES=new Set(['PREPARE','TOOLING_VALIDATE','RUN_DIRECTORY','HTTP_LISTEN','BROWSER_LAUNCH','OWNED_PID_WRITE','SPAWN_VALIDATE','CLIENT_CONNECT','CONTEXT_CREATE','ROUTE_INSTALL','PAGE_CREATE','PAGE_NAVIGATE','PAGE_WAIT','MODEL_VALIDATE','SCREENSHOT','SCREENSHOT_WRITE','INPUT_CONFIRM','CONTEXT_CLOSE','CLIENT_DISCONNECT','SERVER_CLOSE','SERVER_EXIT_OBSERVE','HTTP_CLOSE','RECEIPT_WRITE','RETIRE_READY','DIAGNOSTIC_LIMIT']);
const NAMES=new Set(['Error','TimeoutError','TypeError','RangeError','AbortError']);
const NET=new Set(['ERR_ADDRESS_UNREACHABLE','ERR_CONNECTION_REFUSED','ERR_CONNECTION_CLOSED','ERR_CONNECTION_RESET','ERR_CONNECTION_ABORTED','ERR_TIMED_OUT','ERR_NAME_NOT_RESOLVED','ERR_NETWORK_CHANGED','ERR_INTERNET_DISCONNECTED','ERR_BLOCKED_BY_CLIENT','ERR_BLOCKED_BY_ADMINISTRATOR','ERR_ABORTED','ERR_FAILED','ERR_EMPTY_RESPONSE','ERR_SSL_PROTOCOL_ERROR','ERR_CERT_AUTHORITY_INVALID','ERR_CERT_DATE_INVALID']);
const CODES=new Set(['DEADLINE','SIZE_LIMIT','INPUT_DIGEST','PIN_DIGEST','ARTIFACT_BYTES_MISMATCH','FRESH_INPUT_CHANGED','FILE_CHANGED','PATH_CHANGED','REPARSE_CHECK_FAILED','SECURITY_SWITCH','PROFILE_OUTSIDE_TEMP','RENDER_MODEL_MISMATCH','RENDER_DOM_MISMATCH','RENDER_CELLS_MISMATCH','UNEXPECTED_BROWSER_REQUEST','SDK_ALREADY_IMPORTED','AMBIENT_RUNTIME_CONFIG','NODE_RUNTIME','DEPENDENCY_TREE_DIGEST','SYNC_SPAWN_DENIED_ROOT_JOB_TEARDOWN_REQUIRED']);
function ownString(value,key){try{if(!value||(typeof value!=='object'&&typeof value!=='function'))return null;const d=Object.getOwnPropertyDescriptor(value,key);return d&&typeof d.value==='string'?d.value:null;}catch{return null;}}
function safeFailure(error){
 const name=ownString(error,'name'),message=ownString(error,'message')||'';let isError=false;try{isError=error instanceof Error;}catch{}const error_name=NAMES.has(name)?name:isError?'Error':'UNKNOWN';
 let net_error=null;for(const m of message.slice(0,4096).matchAll(/\bnet::(ERR_[A-Z0-9_]+)(?![A-Z0-9_])/g))if(NET.has(m[1])){net_error=m[1];break;}
 return Object.freeze({error_name,timeout:error_name==='TimeoutError'||message==='DEADLINE',net_error,code:CODES.has(message)?message:'UNCLASSIFIED'});
}
function createTelemetry(write=line=>process.stdout.write(line)){
 const events=[];let bytes=0,overflow=false,io_failed=false;
 const elapsed=()=>Math.min(Number.MAX_SAFE_INTEGER,Math.max(0,Math.floor(process.uptime()*1000)));
 function append(event){const line=JSON.stringify(event)+'\n';if(Buffer.byteLength(line)>256||bytes+Buffer.byteLength(line)>6144){overflow=true;return;}events.push(Object.freeze(event));bytes+=Buffer.byteLength(line);try{write(line);}catch{io_failed=true;}}
 function record(phase,state,error=null,status){
  if(!PHASES.has(phase)||!['BEGIN','OK','FAIL'].includes(state))throw Error('DIAGNOSTIC_PHASE');if(overflow)return;
  const event={phase,state,elapsed_ms:elapsed()};if(state==='FAIL')event.failure=safeFailure(error);if(Number.isInteger(status)&&status>=100&&status<=599)event.http_status=status;
  const line=JSON.stringify(event)+'\n';if(events.length>=55||Buffer.byteLength(line)>256||bytes+Buffer.byteLength(line)>5888){overflow=true;append({phase:'DIAGNOSTIC_LIMIT',state:'FAIL',elapsed_ms:elapsed()});return;}append(event);
 }
 return Object.freeze({record,begin:phase=>record(phase,'BEGIN'),assertUsable:()=>{if(overflow||io_failed)throw Error('DIAGNOSTIC_UNAVAILABLE');},step:async(phase,fn)=>{record(phase,'BEGIN');try{const value=await fn();record(phase,'OK');return value;}catch(e){record(phase,'FAIL',e);throw e;}},snapshot:()=>Object.freeze({schema:'terminan.render.diagnostics.v1',clock:'NODE_MONOTONIC_MS_SINCE_PROCESS_START_NOT_UTC',events:Object.freeze([...events]),event_count:events.length,stream_bytes:bytes,overflow,io_failed})});
}
async function writeFinalReceipt(receipt,telemetry,write){
 telemetry.begin('RECEIPT_WRITE');telemetry.assertUsable();receipt.diagnostics={...telemetry.snapshot(),finalization:'ENDED_BEFORE_FINAL_WRITE'};
 // No mandatory diagnostic write follows publication. File-write/process exit
 // evidence remains separate; this does not issue a durable/runtime commit.
 await write(Buffer.from(JSON.stringify(receipt,null,2)+'\n'));
}
module.exports=Object.freeze({safeFailure,createTelemetry,writeFinalReceipt});

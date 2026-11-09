'use strict';
// Correlation gate only. Root must establish OS isolation before sending GO.
const {Buffer}=require('node:buffer');
const WAIT_MS=5000,MAX_STDIN=1024;
function need(v,code){if(!v)throw Error(code);}
function parseArgs(args){
 need(Array.isArray(args)&&args.length===10&&args.every(x=>typeof x==='string'&&x.length>0&&x.length<=2048)&&args.reduce((n,x)=>n+x.length,0)<=12288,'BOOTSTRAP_ARGS');
 const [nonce,testRoot,request,envelope,artifact,r,e,a,modulePath,executable]=args;
 need(nonce.length===32&&/^[a-f0-9]+$/.test(nonce),'BOOTSTRAP_ARGS');for(const d of [r,e,a])need(d.length===64&&/^[a-f0-9]+$/.test(d),'BOOTSTRAP_ARGS');
 return {nonce,spec:{testRoot,request,envelope,artifact,digests:{request:r,envelope:e,artifact:a}},modulePath,executable};
}
function waitForGo(input,nonce){
 need(typeof nonce==='string'&&nonce.length===32&&/^[a-f0-9]+$/.test(nonce),'BOOTSTRAP_ARGS');
 return new Promise((resolve,reject)=>{
  const expected=Buffer.from('GO '+nonce+'\n','ascii'),buffer=Buffer.alloc(MAX_STDIN);let used=0,done=false;
  const finish=code=>{if(done)return;done=true;clearTimeout(timer);input.pause();input.removeListener('data',data);input.removeListener('end',end);input.removeListener('close',end);input.removeListener('error',error);code?reject(Error(code)):resolve();};
  const data=chunk=>{if(!Buffer.isBuffer(chunk))return finish('GO_PROTOCOL');if(used+chunk.length>MAX_STDIN)return finish('GO_SIZE');chunk.copy(buffer,used);used+=chunk.length;if(used>expected.length||!buffer.subarray(0,used).equals(expected.subarray(0,used)))return finish('GO_PROTOCOL');if(used===expected.length)finish();};
  const end=()=>finish('GO_EOF'),error=()=>finish('GO_IO');const timer=setTimeout(()=>finish('GO_TIMEOUT'),WAIT_MS);
  input.on('data',data);input.once('end',end);input.once('close',end);input.once('error',error);input.resume();
 });
}
async function main(args){
 need(process.version==='v24.22.1'&&process.execArgv.length===1&&process.execArgv[0]==='--no-addons','BOOTSTRAP_RUNTIME');
 for(const [k,v]of Object.entries(process.env))need(!v||!(/^(NODE_OPTIONS|NODE_PATH|NODE_COMPILE_CACHE|NODE_V8_COVERAGE|ELECTRON_RUN_AS_NODE|PW_|PLAYWRIGHT_|SELENIUM_|DEBUG$)/i.test(k)),'BOOTSTRAP_ENV');
 const config=parseArgs(args),gate=waitForGo(process.stdin,config.nonce);
 const ready=JSON.stringify({pid:process.pid,nonce:config.nonce})+'\n';need(Buffer.byteLength(ready)<=128,'BOOTSTRAP_READY_SIZE');process.stdout.write(ready);
 await gate;
 process.exitCode=1;
 const inputEvent=state=>process.stdout.write(JSON.stringify({phase:'GO_INPUT_CLOSE',state,elapsed_ms:Math.floor(process.uptime()*1000)})+'\n');inputEvent('BEGIN');
 try{await closeGoInput(process.stdin);inputEvent('OK');}catch(e){inputEvent('FAIL');throw e;}
 // Single fixed lazy import; no filesystem, renderer or SDK work before this line.
 const {run}=require('./harness.cjs');
 const result=await run(config.spec,config.modulePath,config.executable);
 const receipt=JSON.stringify({run_root:result.runRoot,result:result.receipt.result})+'\n';need(Buffer.byteLength(receipt)<=4096,'BOOTSTRAP_RESULT_SIZE');process.stdout.write(receipt);process.exitCode=result.exitCode;
 process.once('beforeExit',()=>process.stdout.write(JSON.stringify({phase:'NODE_NATURAL_IDLE',state:'OBSERVED',elapsed_ms:Math.floor(process.uptime()*1000)})+'\n'));
}
function closeGoInput(input){return new Promise((resolve,reject)=>{if(input.closed===true)return resolve();let done=false;const finish=ok=>{if(done)return;done=true;clearTimeout(timer);input.removeListener('close',closed);input.removeListener('error',failed);ok?resolve():reject(Error('GO_INPUT_CLOSE'));};const closed=()=>finish(true),failed=()=>finish(false),timer=setTimeout(failed,500);input.once('close',closed);input.once('error',failed);try{input.destroy();}catch{failed();}});}
module.exports={WAIT_MS,MAX_STDIN,parseArgs,waitForGo,closeGoInput};
if(require.main===module)main(process.argv.slice(2)).catch(()=>{process.stderr.write('BOOTSTRAP_REFUSED\n');process.exitCode=1;});

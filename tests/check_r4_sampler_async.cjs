const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const child=require('node:child_process');
const text=fs.readFileSync(path.join(__dirname,'browser/r4.spec.cjs'),'utf8');
const source=text.slice(text.indexOf(' const rss=async()=>'),text.indexOf('\n const rssBefore='));
assert(source.startsWith(' const rss=async()=>'));
const expectedCommand=process.env.R2_PYTHON||'python';
const expectedArgs=['-m','terminan.process_metrics','123','456'];
const cdp={send:async()=>({processInfo:[{id:123},{id:456}]})};
const result={state:'AVAILABLE',rss_bytes:100,process_count:2};
const fixture=['-e',`setTimeout(()=>process.stdout.write(${JSON.stringify(JSON.stringify(result))}),300)`];
function argumentsMatch(command,args){assert.equal(command,expectedCommand);assert.deepEqual(args,expectedArgs);}
function bind(execFile,spawnSync){return new Function('browserCDP','execFile','spawnSync',source+';return rss;')(cdp,execFile,spawnSync);}
(async()=>{
 let timerFired=false,observedOptions;
 const timer=setTimeout(()=>{timerFired=true;},30);
 const rss=bind((command,args,options,callback)=>{
  argumentsMatch(command,args);observedOptions=options;
  return child.execFile(process.execPath,fixture,options,callback);
 },(command,args,options)=>{
  argumentsMatch(command,args);return child.spawnSync(process.execPath,fixture,options);
 });
 assert.deepEqual(await rss(),result);
 assert.equal(timerFired,true,'RSS sampler blocked the Playwright driver and its routed session heartbeats');
 clearTimeout(timer);
 assert.equal(observedOptions.timeout,10000);
 assert.equal(observedOptions.maxBuffer,65536);
 assert.equal(observedOptions.windowsHide,true);
 for(const failure of ['exit','timeout','invalid-json','oversized']){
  const bad=bind((command,args,options,callback)=>{
   argumentsMatch(command,args);
   const programs={exit:"process.stderr.write('PRIVATE_CHILD_DETAIL');process.exit(7)",timeout:'setTimeout(()=>{},2000)',
    'invalid-json':"process.stdout.write('PRIVATE_INVALID_JSON')",oversized:"process.stdout.write('x'.repeat(70000))"};
   return child.execFile(process.execPath,['-e',programs[failure]],{...options,timeout:failure==='timeout'?50:options.timeout},callback);
  },()=>{throw Error('blocking sampler must not be used');});
  await assert.rejects(bad(),error=>error.message==='Resource sampler failed');
 }
 console.log('R4 sampler responsive event loop, exact PID command, bounded child and closed errors PASS');
})().catch(error=>{console.error(error);process.exitCode=1;});

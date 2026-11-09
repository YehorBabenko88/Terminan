'use strict';
async function cleanupIssued(handles,telemetry,budgetMs=10000){
 if(!Number.isInteger(budgetMs)||budgetMs<=0||budgetMs>10000)throw Error('CLEANUP_BUDGET');
 const started=process.hrtime.bigint(),deadline=started+BigInt(budgetMs)*1000000n,r={context:'NOT_ISSUED',client:'NOT_ISSUED',server:'NOT_ISSUED',http:'NOT_ISSUED',confirmed:false,exit_observed:false,fallback_sdk_kill:false,budget_ms:budgetMs,expired:false,deadline_expired:false,expiration_phase:null};
 function expire(phase,now){r.expired=true;if(now>=deadline)r.deadline_expired=true;if(r.expiration_phase===null)r.expiration_phase=phase;}
 async function attempt(phase,fn){
  const begin=process.hrtime.bigint(),operationDeadline=begin+5000000000n<deadline?begin+5000000000n:deadline;
  const check=()=>{const now=process.hrtime.bigint();if(now>=operationDeadline){expire(phase,now);throw Error('DEADLINE');}return now;};
  try{
   check();const result=await telemetry.step(phase,async()=>{check();let timer;try{const ms=Math.ceil(Number(operationDeadline-check())/1000000);const result=await Promise.race([Promise.resolve().then(()=>{check();return fn();}),new Promise((_,reject)=>{timer=setTimeout(()=>{expire(phase,process.hrtime.bigint());reject(Error('DEADLINE'));},ms);})]);check();if(result!==true)throw Error('OWNED_CLEANUP_UNCONFIRMED');return true;}finally{clearTimeout(timer);}});
   // A delayed telemetry continuation must not hide elapsed cleanup time either.
   check();return result;
  }catch{return false;}
 }
 if(handles.context)r.context=await attempt('CONTEXT_CLOSE',async()=>{await handles.context.close();return true;})?'CLOSED':'UNKNOWN';
 if(handles.browser)r.client=await attempt('CLIENT_DISCONNECT',async()=>{await handles.browser.close();return handles.browser.isConnected()===false;})?'DISCONNECTED':'UNKNOWN';
 if(handles.browserServer){
  r.server=await attempt('SERVER_CLOSE',async()=>{await handles.browserServer.close();return true;})?'CLOSED':'UNKNOWN';
  const observed=await attempt('SERVER_EXIT_OBSERVE',()=>{const child=handles.browserServer.process();if(Number.isSafeInteger(child.pid)&&child.pid>0)r.pid=child.pid;r.exit_observed=Number.isInteger(child.exitCode)||(typeof child.signalCode==='string'&&child.signalCode.length>0);r.exit_code=Number.isInteger(child.exitCode)?child.exitCode:null;r.signal_observed=typeof child.signalCode==='string'&&child.signalCode.length>0;return r.exit_observed&&r.exit_code===0;});if(!observed)r.server='UNKNOWN';
 }
 if(handles.httpServer)r.http=await attempt('HTTP_CLOSE',()=>new Promise((resolve,reject)=>{handles.httpServer.closeAllConnections();handles.httpServer.close(error=>error?reject(error):resolve(true));}))?'CLOSED':'UNKNOWN';
 const finished=process.hrtime.bigint();r.observed_elapsed_ms=Math.max(0,Number(finished-started)/1000000);if(finished>=deadline)expire('FINAL_CONFIRM',finished);
 r.confirmed=!r.expired&&!r.deadline_expired&&['CLOSED','NOT_ISSUED'].includes(r.context)&&['DISCONNECTED','NOT_ISSUED'].includes(r.client)&&r.server==='CLOSED'&&r.exit_observed&&r.exit_code===0&&['CLOSED','NOT_ISSUED'].includes(r.http);
 return Object.freeze(r);
}
module.exports=Object.freeze({cleanupIssued});

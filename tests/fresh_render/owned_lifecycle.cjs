'use strict';
async function cleanupIssued(handles,telemetry,budgetMs=10000){
 const started=process.hrtime.bigint(),r={context:'NOT_ISSUED',client:'NOT_ISSUED',server:'NOT_ISSUED',http:'NOT_ISSUED',confirmed:false,exit_observed:false,fallback_sdk_kill:false};
 const remaining=()=>Math.max(0,Math.min(5000,budgetMs-Number((process.hrtime.bigint()-started)/1000000n)));
 async function attempt(phase,fn){try{return await telemetry.step(phase,async()=>{const ms=remaining();if(ms<=0)throw Error('DEADLINE');let timer;try{const result=await Promise.race([Promise.resolve().then(fn),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('DEADLINE')),ms);})]);if(result!==true)throw Error('OWNED_CLEANUP_UNCONFIRMED');return true;}finally{clearTimeout(timer);}});}catch{return false;}}
 if(handles.context)r.context=await attempt('CONTEXT_CLOSE',async()=>{await handles.context.close();return true;})?'CLOSED':'UNKNOWN';
 if(handles.browser)r.client=await attempt('CLIENT_DISCONNECT',async()=>{await handles.browser.close();return handles.browser.isConnected()===false;})?'DISCONNECTED':'UNKNOWN';
 if(handles.browserServer){
  r.server=await attempt('SERVER_CLOSE',async()=>{await handles.browserServer.close();return true;})?'CLOSED':'UNKNOWN';
  const observed=await attempt('SERVER_EXIT_OBSERVE',()=>{const child=handles.browserServer.process();if(Number.isSafeInteger(child.pid)&&child.pid>0)r.pid=child.pid;r.exit_observed=Number.isInteger(child.exitCode)||(typeof child.signalCode==='string'&&child.signalCode.length>0);r.exit_code=Number.isInteger(child.exitCode)?child.exitCode:null;r.signal_observed=typeof child.signalCode==='string'&&child.signalCode.length>0;return r.exit_observed&&r.exit_code===0;});if(!observed)r.server='UNKNOWN';
 }
 if(handles.httpServer)r.http=await attempt('HTTP_CLOSE',()=>new Promise((resolve,reject)=>{handles.httpServer.closeAllConnections();handles.httpServer.close(error=>error?reject(error):resolve(true));}))?'CLOSED':'UNKNOWN';
 r.confirmed=['CLOSED','NOT_ISSUED'].includes(r.context)&&['DISCONNECTED','NOT_ISSUED'].includes(r.client)&&r.server==='CLOSED'&&r.exit_observed&&r.exit_code===0&&['CLOSED','NOT_ISSUED'].includes(r.http);
 return Object.freeze(r);
}
module.exports=Object.freeze({cleanupIssued});

/* Session correlation only, never real-source authentication/authority. */
'use strict';
(function(root){
class R4SessionClient {
 constructor({fetcher=fetch,clock=()=>performance.now(),later=setTimeout,cancel=clearTimeout,onState=()=>{}}={}){Object.assign(this,{fetcher,clock,later,cancel,onState});this.closed=false;this.generation=0;this.timer=0;this.controller=null;this.receipt=null;this.failures=0;this.requests=0;this.active=0;this.lastSeen=0;this.state='UNVERIFIED';}
 validate(value){
  const keys=['version','mode','session_id','candidate_sha','epoch','revision','state','lease_ms','poll_ms','end_grace_ms','authority','sources'];
  if(!value||Object.keys(value).sort().join()!==keys.sort().join()||value.version!==1||value.mode!=='SYNTHETIC'||value.authority!=='SYNTHETIC_ONLY'||value.sources!=='DISABLED'||value.candidate_sha!==this.sha||!/^[a-f0-9]{40}$/.test(this.sha)||!/^[a-f0-9]{32}$/.test(value.session_id)||value.epoch!==1||value.lease_ms!==5000||value.poll_ms!==500||value.end_grace_ms!==3000||!((value.state==='ACTIVE'&&value.revision===1)||(value.state==='SESSION_ENDED'&&value.revision===2)))throw Error('RECEIPT_INVALID');
  if(this.receipt&&(value.session_id!==this.receipt.session_id||value.epoch!==this.receipt.epoch||value.revision<this.receipt.revision))throw Error('RECEIPT_IDENTITY');
  return value;
 }
 accept(value){if(this.closed)return false;this.validate(value);this.receipt=value;this.lastSeen=this.clock();if(value.state==='SESSION_ENDED'){this.close();this.state='SESSION_ENDED';this.onState(this.state,true);return false;}return true;}
 start(sha){this.sha=sha;return this.poll();}
 async poll(){
  if(this.closed||this.active)return;
  if(this.receipt&&this.clock()-this.lastSeen>5000){this.close();this.state='DISCONNECTED';this.onState(this.state,true);return;}
  const generation=this.generation,controller=new AbortController();this.controller=controller;this.active=1;this.requests++;
  const timeout=this.later(()=>controller.abort(),1500);let delay=500;
  try{
   const response=await this.fetcher('/api/session'+(this.receipt?'?session_id='+this.receipt.session_id:''),{signal:controller.signal});
   if(!response.ok)throw Error('TRANSPORT');
   const text=await response.text();if(text.length>8192)throw Error('RECEIPT_INVALID');let value;try{value=JSON.parse(text);}catch{throw Error('RECEIPT_INVALID');}
   if(generation!==this.generation||this.closed)return;
   if(!this.accept(value))return;this.failures=0;this.state='ACTIVE';this.onState(this.state,false);
  }catch(error){
   if(generation!==this.generation||this.closed)return;
   if(error.message?.startsWith('RECEIPT_')){this.close();this.state='UNVERIFIED';this.onState(this.state,true);return;}
   this.failures++;this.state='DISCONNECTED';const terminal=this.failures>=5;
   if(terminal)this.close();else delay=[250,500,1000,2000][this.failures-1];
   this.onState(this.state,terminal);
  }finally{
   this.cancel(timeout);this.active=0;this.controller=null;
   if(!this.closed&&generation===this.generation)this.timer=this.later(()=>{this.timer=0;this.poll();},delay);
  }
 }
 close(){this.closed=true;++this.generation;if(this.timer)this.cancel(this.timer);this.timer=0;this.controller?.abort();}
 metrics(){return {state:this.state,retries:this.failures,requests:this.requests,pending:Number(Boolean(this.timer)),active:this.active,closed:this.closed};}
}
root.R4SessionClient=R4SessionClient;if(typeof module!=='undefined')module.exports=R4SessionClient;
})(typeof window!=='undefined'?window:globalThis);

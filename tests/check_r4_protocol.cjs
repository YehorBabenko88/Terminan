const assert=require('node:assert/strict');const Client=require('../terminan/r4_protocol.js');
const receipt={version:1,mode:'SYNTHETIC',session_id:'a'.repeat(32),candidate_sha:'b'.repeat(40),epoch:1,revision:1,state:'ACTIVE',lease_ms:5000,poll_ms:500,end_grace_ms:3000,authority:'SYNTHETIC_ONLY',sources:'DISABLED'};
(async()=>{
 let now=0,jobs=[],calls=0;const later=(fn,delay)=>{const job={fn,delay};jobs.push(job);return job;};const cancel=job=>{jobs=jobs.filter(x=>x!==job);};
 const c=new Client({clock:()=>now,later,cancel,fetcher:async()=>{calls++;throw Error('PRIVATE_RAW_EXCEPTION');}});await c.start('b'.repeat(40));
 while(!c.closed){const j=jobs.shift();assert(j);now+=j.delay;await j.fn();await new Promise(r=>setImmediate(r));}
 assert.equal(calls,5);assert.equal(c.state,'DISCONNECTED');assert.equal(c.timer,0);assert.equal(c.active,0);
 let state='';const a=new Client({onState:s=>state=s});a.sha='b'.repeat(40);a.accept(receipt);a.accept({...receipt,state:'SESSION_ENDED',revision:2});assert.equal(state,'SESSION_ENDED');assert(a.closed);
 const b=new Client();b.sha='b'.repeat(40);b.accept(receipt);assert.throws(()=>b.accept({...receipt,session_id:'c'.repeat(32)}));assert.throws(()=>b.accept({...receipt,mode:'LIVE'}));
 let resolve;const d=new Client({fetcher:()=>new Promise(r=>resolve=r)});const p=d.start('b'.repeat(40));d.close();resolve({ok:true,text:async()=>JSON.stringify(receipt)});await p;assert(d.closed);assert.equal(d.receipt,null);assert.equal(d.timer,0);
 const native=new Client({fetcher:async function(){assert.equal(this,globalThis);return {ok:true,text:async()=>JSON.stringify(receipt)};},later:function(...args){assert.equal(this,globalThis);return setTimeout(...args);},cancel:function(...args){assert.equal(this,globalThis);return clearTimeout(...args);}});await native.start('b'.repeat(40));assert.equal(native.state,'ACTIVE');native.close();
 console.log('R4 protocol finite retry / end / identity / cancellation PASS');
})().catch(()=>{console.error('R4 protocol FAIL');process.exitCode=1;});

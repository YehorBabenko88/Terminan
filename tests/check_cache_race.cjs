const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const code=fs.readFileSync('terminan/saved.js','utf8');
const start=code.includes(' function clearCache(')?code.indexOf(' function clearCache('):code.indexOf(' async function lookupCache(');
const elements={};const el=id=>elements[id]??={textContent:'',rows:[],replaceChildren(){this.rows=[];}};
const pending=[];
let selectedTF='5m';
const ctx=vm.createContext({URLSearchParams,AbortController,setTimeout,clearTimeout,console,
 el,add:(parent,tag,value)=>{const e={textContent:value};parent.rows??=[];parent.rows.push(e);return e;},
 read:(url,signal)=>new Promise(resolve=>pending.push({url,signal,resolve})),source:()=>({source:'grid'}),displayTF:()=>selectedTF,dataset:()=>({name:'candles_1m'}),render:()=>{},aggregated:()=>[],when:String,
 controls:new AbortController()});
vm.runInContext(`let generation=0,closed=false,cacheGeneration=0,cacheController=null,current=null;const $=el;const text=(id,s)=>el(id).textContent=s;`+code.slice(start,code.indexOf(' function options()',start)),ctx);
const payload={state:'READY',authority:'OFFLINE_ONLY',sha256:'a'.repeat(64),preview_sha256:'c'.repeat(64),integrity_scope:'PREVIEW_SHA256_WORKER_VALIDATED_FULL_DIGEST',symbol:'BTCUSDT',timeframe:'5m',source_revision:'b'.repeat(64),from_ms:1767225600000,to_ms:1767225840000,truncated:false,total_candles:1,match:'EXACT_SOURCE_REVISION_AND_RANGE',candles:[{ts:1767225600000,open:100,high:102,low:99,close:101,volume:3,delta:1}]};
(async()=>{
 vm.runInContext(`var page={dataset:'candles_1m',source_sha:'c'.repeat(40),epoch:'b'.repeat(64),symbol:'BTCUSDT',rows:[{ts:1767225600000},{ts:1767225840000}]};`,ctx);
 const lookup=vm.runInContext('lookupCache(page,0)',ctx);
 assert.equal(pending.length,1,'must query data epoch, not reject 40-char code SHA');
 assert.equal(new URLSearchParams(pending[0].url.split('?')[1]).get('revision'),'b'.repeat(64));
 pending.shift().resolve(payload);await lookup;assert.match(el('cache-match-state').textContent,/READY/);
 const old=vm.runInContext(`inspectCache('1'.repeat(32))`,ctx);
 const fresh=vm.runInContext(`inspectCache('2'.repeat(32))`,ctx);
 assert.equal(pending[0].signal.aborted,true,'superseded inspection must abort');
 pending[1].resolve({...payload,symbol:'ETHUSDT'});await fresh;
 pending[0].resolve(payload);await old;assert.match(el('cache-result-state').textContent,/ETHUSDT/);
 const stale=vm.runInContext(`inspectCache('3'.repeat(32))`,ctx);
 vm.runInContext('generation++;clearCache()',ctx);pending[2].resolve(payload);await stale;
 assert.equal(el('cache-result-rows').rows.length,0,'source changes clear stale cache results');
 pending.length=0;selectedTF='15m';vm.runInContext('current=page',ctx);
 const handler=code.match(/on\('saved-timeframe','change',(\(\)=>\{.*?\})\);/)[1];
 vm.runInContext('('+handler+')()',ctx);assert.equal(pending.length,1,'timeframe changes repeat exact cache lookup');
 assert.equal(new URLSearchParams(pending[0].url.split('?')[1]).get('timeframe'),'15m');pending[0].resolve({state:'MISS',authority:'OFFLINE_ONLY'});await new Promise(r=>setImmediate(r));
 assert.match(el('cache-match-state').textContent,/MISS/);
 console.log('cache revision and asynchronous fencing PASS');
})().catch(e=>{console.error(e);process.exitCode=1;});

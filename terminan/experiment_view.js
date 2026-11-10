/* PURE client preparation. No endpoint, fetch, authentication or scientific codec. */
(function(root,factory){'use strict';const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.TerminanExperimentView=api;})(globalThis,function(){
  'use strict';
  const VIEW_LIMITS=Object.freeze({response:2097152,artifact:1048576,descriptor:65536,depth:12,reader_chunks:8192});
  const controllers=new WeakMap();
  const typed=Object.getPrototypeOf(Uint8Array.prototype),byteLength=Object.getOwnPropertyDescriptor(typed,'byteLength').get,bufferOf=Object.getOwnPropertyDescriptor(typed,'buffer').get,arrayBufferLength=Object.getOwnPropertyDescriptor(ArrayBuffer.prototype,'byteLength').get,isView=ArrayBuffer.isView;
  const fail=code=>{throw Error(code);};
  function buildExperimentViewRequest(experimentId){
    if(arguments.length!==1)fail('VIEW_REQUEST_OPTIONS_NOT_ALLOWED');
    if(typeof experimentId!=='string'||experimentId.length<1||experimentId.length>128||!/^[A-Za-z0-9][A-Za-z0-9._-]*$(?![\s\S])/.test(experimentId))fail('VIEW_INVALID_EXPERIMENT_ID');
    return Object.freeze({method:'GET',path:'/api/experiments/'+experimentId+'/view',credentials:'same-origin',cache:'no-store',redirect:'error',referrerPolicy:'no-referrer',headers:Object.freeze({Accept:'application/json'})});
  }
  function checkViewByteLimit(kind,value){
    if(!['response','artifact','descriptor'].includes(kind))fail('VIEW_UNKNOWN_BYTE_PART');
    if(!isView(value)||!(value instanceof Uint8Array))fail('VIEW_BYTES_REQUIRED');
    let size;try{arrayBufferLength.call(bufferOf.call(value));size=byteLength.call(value);}catch{fail('VIEW_BYTES_REQUIRED');}
    if(size>VIEW_LIMITS[kind])fail('VIEW_SIZE_LIMIT');return size;
  }
  function cancelBody(response){try{if(typeof Response==='undefined'||!(response instanceof Response))return;if(response.body&&!response.body.locked)Promise.resolve(response.body.cancel()).catch(()=>{});}catch{}}
  function createExperimentViewController(root){
    if(!root||typeof root.replaceChildren!=='function'||!root.ownerDocument||typeof root.ownerDocument.createElement!=='function')fail('VIEW_ROOT_REQUIRED');
    if(controllers.has(root))return controllers.get(root);
    let current=null;const records=new WeakMap();
    const makeState=(status,reason,id=null)=>Object.freeze({scope:'PURE_CLIENT_NOT_ENDPOINT',status,reason,experiment_id:id,has_scientific_payload:false,transport_bound:false,response_codec_frozen:false});
    let state=makeState('UNAVAILABLE','NOT_BOUND');
    const paint=()=>{const p=root.ownerDocument.createElement('p');p.textContent=state.status+' — '+state.reason+' · PURE client only; no scientific payload or authenticated endpoint acceptance';p.setAttribute('role','status');root.replaceChildren(p);};
    const owns=ticket=>!!ticket&&typeof ticket==='object'&&records.has(ticket)&&current===ticket;
    const stale=()=>Object.freeze({scope:'PURE_CLIENT_NOT_ENDPOINT',status:'SUPERSEDED',reason:'UI_REQUEST_SUPERSEDED',has_scientific_payload:false});
    function stop(){const old=current;current=null;if(old)records.get(old).controller.abort();}
    function finish(ticket,reason){if(!owns(ticket))return stale();stop();state=makeState('UNAVAILABLE',reason);paint();return state;}
    function begin(experimentId){
      stop();state=makeState('UNAVAILABLE','INVALID_REQUEST');paint();
      let request;try{if(arguments.length!==1)fail('VIEW_REQUEST_OPTIONS_NOT_ALLOWED');request=buildExperimentViewRequest(experimentId);}catch(e){throw Error(['VIEW_REQUEST_OPTIONS_NOT_ALLOWED','VIEW_INVALID_EXPERIMENT_ID'].includes(e.message)?e.message:'VIEW_INVALID_EXPERIMENT_ID');}
      const controller=new AbortController(),ticket=Object.freeze({kind:'PURE_UI_REQUEST_TICKET_NOT_AUTHORITY',request,signal:controller.signal});records.set(ticket,{controller});current=ticket;state=makeState('PENDING','WAITING_FOR_OWNER_RESPONSE_CODEC',experimentId);paint();return ticket;
    }
    async function observe(ticket,response){
      if(!owns(ticket)){if(ticket&&typeof ticket==='object'&&records.has(ticket))cancelBody(response);return stale();}
      if(typeof Response==='undefined'||!(response instanceof Response))return finish(ticket,'VIEW_RESPONSE_REQUIRED');
      if(response.status===401||response.status===403){cancelBody(response);return finish(ticket,'HTTP_DENIED');}
      if(response.status!==200){cancelBody(response);return finish(ticket,'HTTP_UNAVAILABLE');}
      let reader=null,onAbort=null;
      try{
        const length=response.headers.get('Content-Length');
        if(length!==null&&(!/^(?:0|[1-9][0-9]*)$(?![\s\S])/.test(length)||length.length>16||BigInt(length)>BigInt(VIEW_LIMITS.response))){cancelBody(response);return finish(ticket,'VIEW_LENGTH_LIMIT');}
        if(!response.body)return finish(ticket,'RESPONSE_CODEC_NOT_FROZEN');
        reader=response.body.getReader();onAbort=()=>{try{Promise.resolve(reader.cancel()).catch(()=>{});}catch{}};ticket.signal.addEventListener('abort',onAbort,{once:true});
        if(!owns(ticket)){onAbort();return stale();}
        let total=0,chunks=0,depth=0,quoted=false,escaped=false;
        while(true){
          const item=await reader.read();if(!owns(ticket))return stale();if(item.done)break;
          if(++chunks>VIEW_LIMITS.reader_chunks)fail('VIEW_CHUNK_LIMIT');const size=checkViewByteLimit('response',item.value);total+=size;if(total>VIEW_LIMITS.response)fail('VIEW_SIZE_LIMIT');
          // Structural guard only: no scientific decoding/schema acceptance.
          for(let index=0;index<size;index++){const b=item.value[index];if(quoted){if(escaped)escaped=false;else if(b===92)escaped=true;else if(b===34)quoted=false;}
            else if(b===34)quoted=true;else if(b===123||b===91){if(++depth>VIEW_LIMITS.depth)fail('VIEW_DEPTH_LIMIT');}else if(b===125||b===93){if(--depth<0)fail('VIEW_FRAMING_INVALID');}}
        }
        if(depth!==0||quoted||escaped)fail('VIEW_FRAMING_INVALID');
        // A bounded200 is NOT authenticated scientific success. Exact owner codec
        // and positive read/storage/job APIs require a separately approved change.
        return finish(ticket,'RESPONSE_CODEC_NOT_FROZEN');
      }catch(error){if(!owns(ticket))return stale();return finish(ticket,['VIEW_SIZE_LIMIT','VIEW_LENGTH_LIMIT','VIEW_CHUNK_LIMIT','VIEW_DEPTH_LIMIT','VIEW_FRAMING_INVALID','VIEW_BYTES_REQUIRED'].includes(error.message)?error.message:'VIEW_READ_FAILED');}
      finally{if(onAbort)ticket.signal.removeEventListener('abort',onAbort);if(reader){try{await reader.cancel();}catch{}try{reader.releaseLock();}catch{}}}
    }
    function reset(){stop();state=makeState('UNAVAILABLE','RESET');paint();return state;}
    function invalidate(reason){
      stop();state=makeState('UNAVAILABLE','INVALIDATION_REQUIRED');paint();
      // Local denial-only UI signals; not backend enums, authorization or recovery.
      if(arguments.length!==1||typeof reason!=='string'||!['READ_UNAVAILABLE','READ_DENIED','SESSION_EXPIRED','AUTHORITY_STALE','REVISION_STALE','GENERATION_CHANGED','OFFLINE','RECONNECTING'].includes(reason))fail('VIEW_INVALIDATION_REASON_REQUIRED');
      state=makeState('UNAVAILABLE',reason);paint();return state;
    }
    const api=Object.freeze({begin,observe,reset,invalidate,snapshot:()=>state});controllers.set(root,api);paint();return api;
  }
  return Object.freeze({VIEW_LIMITS,buildExperimentViewRequest,checkViewByteLimit,createExperimentViewController});
});

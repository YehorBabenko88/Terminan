/* Exact Review4 SSE record framing only. Caller must validate envelope, epochs,
 * ordering, authority and domain before applying any returned opaque C3 token.
 */
(function(root,factory){
  const api=factory(typeof module==='object'?require('./c3.js'):root.TerminanC3);
  if(typeof module==='object')module.exports=api;else root.TerminanMuxStream=api;
})(globalThis,function(C){
  'use strict';
  class MuxRecords {
    constructor(){this.buffer='';this.closed=false;}
    close(){this.closed=true;this.buffer='';}
    finish(){
      if(this.closed)throw Error('STREAM_CLOSED');
      const truncated=this.buffer.length!==0;
      this.close();
      if(truncated)throw Error('TRUNCATED_RECORD');
    }
    feed(fragment){
      if(this.closed)throw Error('STREAM_CLOSED');
      try{
        if(typeof fragment!=='string'||fragment.length>2097152)throw Error('CHUNK_CAP');
        for(let i=0;i<fragment.length;i++){
          const char=fragment[i], code=fragment.charCodeAt(i);
          if((code<32&&char!=='\n')||code>126)throw Error('SSE_ASCII_REQUIRED');
        }
        const records=[], joined=this.buffer+fragment;
        let start=0,end;
        while((end=joined.indexOf('\n\n',start))!==-1){
          if(end+2-start>133128)throw Error('FRAME_CAP');
          if(records.length>=16)throw Error('BATCH_CAP');
          if(joined.slice(start,start+6)!=='data: ')throw Error('SSE_PREFIX');
          records.push(C.parse(joined.slice(start+6,end),133120));
          start=end+2;
        }
        this.buffer=joined.slice(start);
        if(this.buffer.length>133128)throw Error('FRAME_CAP');
        return records;
      }catch(error){this.close();throw error;}
    }
  }
  return Object.freeze({MuxRecords});
});

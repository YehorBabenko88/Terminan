const {test}=require('node:test');
const assert=require('node:assert/strict');
const C=require('../../terminan/sync/c3.js');
const {MuxRecords}=require('../../terminan/sync/mux-stream.js');
test('mux framing survives every byte split without changing canonical bytes',()=>{
  const record='data: {"a":"\\\"","b":null}\n\n';
  for(let i=0;i<=record.length;i++){
    const decoder=new MuxRecords();
    const frames=[...decoder.feed(record.slice(0,i)),...decoder.feed(record.slice(i))];
    assert.deepEqual(frames.map(C.text),['{"a":"\\\"","b":null}']);
    decoder.finish();
  }
});
test('mux rejects SSE aliases, numbers, duplicates, non-ASCII and trailing fragments',()=>{
  for(const raw of ['data:{}\n\n','data: {}\r\n\r\n',': heartbeat\n\n',
    'data: {"a":null,"a":null}\n\n','data: 1\n\n','data: "é"\n\n']){
    const decoder=new MuxRecords();
    assert.throws(()=>decoder.feed(raw));
    assert.throws(()=>decoder.feed('data: {}\n\n'),/CLOSED/);
  }
  const decoder=new MuxRecords();decoder.feed('data: {');
  assert.throws(()=>decoder.finish(),/TRUNCATED/);
});
test('mux bounds incomplete buffer and batch delivery; close fences reconnect fragments',()=>{
  const decoder=new MuxRecords();
  assert.throws(()=>decoder.feed('x'.repeat(133129)));
  assert.throws(()=>new MuxRecords().feed('data: {}\n\n'.repeat(17)),/BATCH_CAP/);
  const old=new MuxRecords();old.feed('data: {');old.close();
  assert.throws(()=>old.feed('}\n\n'),/CLOSED/);
  assert.throws(()=>new MuxRecords().feed('}\n\n'));
});
test('mux does not expose previous frames if later record in same batch is invalid',()=>{
  const decoder=new MuxRecords();
  assert.throws(()=>decoder.feed('data: {}\n\ndata: 1\n\n'));
  assert.throws(()=>decoder.feed('data: {}\n\n'),/CLOSED/);
});

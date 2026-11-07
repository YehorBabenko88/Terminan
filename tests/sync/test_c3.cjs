const { test } = require('node:test');
const assert = require('node:assert/strict');
const C = require('../../terminan/sync/c3.js');

test('C3 preserves exact strings and ASCII numeric-key order', () => {
  const raw = '{"10":"1.0","2":"-0.0","a":[true,false,null,"\\\"\\\\"]}';
  const token = C.parse(raw);
  assert.equal(C.text(token), raw);
  assert.equal(C.value(token)['10'], '1.0');
  assert.equal(Object.getPrototypeOf(C.value(token)), null);
  assert.ok(Object.isFrozen(C.value(token).a));
});
test('C3 rejects noncanonical and numeric aliases before returning data', () => {
  for (const raw of ['1','1.0','-0','1e-7','{"b":null,"a":null}',
    '{"a":null,"a":true}', '{"a":"\\u0061"}', '{"a":"\\/"}',
    '{"a": "x"}', '{}\n', '"é"', '"\u0000"', '', '[true,]', '{"":null}'])
    assert.throws(() => C.parse(raw), undefined, raw);
});
test('C3 treats prototype-looking keys as inert own data', () => {
  const value = C.value(C.parse('{"__proto__":{"constructor":"x"}}'));
  assert.equal(value.__proto__.constructor, 'x');
  assert.equal(Object.getPrototypeOf(value), null);
});
test('C3 counts containers only for depth and every key for nodes', () => {
  assert.doesNotThrow(() => C.parse('{"a":'.repeat(12)+'null'+'}'.repeat(12)));
  assert.throws(() => C.parse('{"a":'.repeat(13)+'null'+'}'.repeat(13)));
  const object = () => Object.fromEntries(Array.from({length:64}, (_,i)=>['k'+String(i).padStart(2,'0'),'']));
  const data = Array.from({length:254},object);
  data[0].k01 = [''];
  assert.doesNotThrow(() => C.parse(JSON.stringify(data)));
  data[0].k02 = [''];
  assert.throws(() => C.parse(JSON.stringify(data)), /NODE_CAP/);
});
test('C3 enforces each size bound and narrower route byte bounds', () => {
  assert.doesNotThrow(() => C.parse('"'+'a'.repeat(16384)+'"'));
  assert.throws(() => C.parse('"'+'a'.repeat(16385)+'"'));
  assert.throws(() => C.parse('['+Array(1001).fill('null').join(',')+']'));
  assert.throws(() => C.parse('{"'+'a'.repeat(129)+'":null}'));
  assert.throws(() => C.parse(JSON.stringify(Object.fromEntries(Array.from({length:65},(_,i)=>['k'+String(i).padStart(2,'0'),null])))));
  assert.throws(() => C.parse('{}', 1));
  assert.throws(() => C.parse('{}', 2097153));
});
test('C3 does not reflect, coerce or invoke hostile host objects', () => {
  let calls=0;
  const hostile=new Proxy({}, {get(){calls++;throw Error('trap');},ownKeys(){calls++;throw Error('trap');}});
  assert.throws(() => C.parse(hostile));
  assert.throws(() => C.text(hostile));
  assert.throws(() => C.value({}));
  assert.equal(calls,0);
});
test('C3 is executable in a browser-like runtime without require or Buffer', () => {
  const vm=require('node:vm');
  const fs=require('node:fs');
  const context=vm.createContext({});
  vm.runInContext(fs.readFileSync(require.resolve('../../terminan/sync/c3.js'),'utf8'),context);
  assert.equal(vm.runInContext('TerminanC3.text(TerminanC3.parse("{}"))',context),'{}');
});

const fs = require('node:fs'), crypto = require('node:crypto');
const vectorBytes=fs.readFileSync(require.resolve('./c3-review4-vectors.json'));
assert.equal(crypto.createHash('sha256').update(vectorBytes).digest('hex'),
  'c83dd5a0ac22bc9e3d29151774e560b6a7a2fc0879ef7579dbbde166c9565d81');
function materialize(vector){
  if('raw' in vector)return vector.raw;
  const {kind,n:rawN}=vector.recipe,n=Number(rawN);
  if(kind==='depth')return '{"k":'.repeat(n)+'"x"'+'}'.repeat(n);
  if(kind==='array')return '['+Array(n).fill('"x"').join(',')+']';
  if(kind==='string')return '{"x":"'+'a'.repeat(n)+'"}';
  if(kind==='key_length')return '{"'+'k'.repeat(n)+'":"x"}';
  if(kind==='members')return JSON.stringify(Object.fromEntries(Array.from({length:n},(_,i)=>['k'+String(i).padStart(2,'0'),'x'])));
  if(kind==='nodes'){
    const data=Array.from({length:254},()=>Object.fromEntries(Array.from({length:64},(_,i)=>['k'+String(i).padStart(2,'0'),''])));
    for(let i=0;i<n;i++)data[0]['k'+String(i).padStart(2,'0')]=[''];
    return JSON.stringify(data);
  }
  if(kind==='bytes')return JSON.stringify([...Array(127).fill('a'.repeat(16384)),'a'.repeat(15999+n)]);
  throw Error('UNKNOWN_VECTOR_RECIPE');
}
JSON.parse(vectorBytes).vectors.forEach((vector,index)=>{
  test('pinned Review4 raw vector '+index,()=>{
    const raw=materialize(vector);
    if(!vector.accept){assert.throws(()=>C.parse(raw));return;}
    const token=C.parse(raw);
    assert.equal(crypto.createHash('sha256').update(C.text(token),'ascii').digest('hex'),vector.sha256_ascii);
  });
});

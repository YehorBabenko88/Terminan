const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
test('overlay script parses before browsers load its file import handler',()=>{
 assert.doesNotThrow(()=>new vm.Script(fs.readFileSync('terminan/history_overlay.js','utf8')));
});

const fs = require('node:fs');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const html = fs.readFileSync('terminan/index.html', 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const drawSource = script.slice(script.indexOf('function draw('), script.indexOf('function list('));
const calls = {allocations:0, transforms:[], clears:0};
const context2d = new Proxy({}, {get(_target, name) {
  if (name === 'setTransform') return (...args) => calls.transforms.push(args);
  if (name === 'clearRect') return () => calls.clears++;
  return () => {};
}});
const canvas = {clientWidth:500, clientHeight:320, _width:0, _height:0,
  get width(){return this._width}, set width(v){this._width=v;calls.allocations++},
  get height(){return this._height}, set height(v){this._height=v;calls.allocations++},
  getContext(){return context2d}};
const elements = {chart:canvas,chartmsg:{textContent:''},showlevels:{checked:true}};
const document = {getElementById(id){return elements[id]}};
const ctx = vm.createContext({document,devicePixelRatio:1.5,Math,Number});
vm.runInContext('let currentLevels=[];'+drawSource,ctx);
vm.runInContext('draw([])',ctx);
assert.equal(calls.allocations,2);
vm.runInContext('draw([])',ctx);
assert.equal(calls.allocations,2,'same dimensions must reuse backing store');
assert.equal(calls.clears,2);
assert.deepEqual(calls.transforms[1],[1.5,0,0,1.5,0,0]);
canvas.clientWidth=501;
vm.runInContext('draw([])',ctx);
assert.equal(calls.allocations,3,'resize must update only changed backing dimension');
assert.equal(canvas.width,752,'fractional DPR rounds pixel width');
console.log('offline canvas DPR and allocation regression PASS');

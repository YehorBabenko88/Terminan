const fs = require('node:fs');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const html = fs.readFileSync('terminan/index.html', 'utf8');
let script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
script = script.slice(0, script.indexOf("el('search').oninput"));
const elements = {};
const document = {getElementById(id) { return elements[id] ||= {textContent:'', value:'1m', checked:true, style:{}}; }};
const pending = [];
const ctx = vm.createContext({document, console, URLSearchParams, fetch(path) {
  return new Promise(resolve => pending.push({path, resolve(value) {resolve({ok:true,json:async()=>value});}}));
}});
vm.runInContext(script, ctx);
vm.runInContext('draw = rows => { document.getElementById("chartmsg").textContent = rows[0]?.symbol || "empty"; }', ctx);
(async () => {
  const old = vm.runInContext("symbol='BTCUSDT'; refresh()", ctx);
  const newer = vm.runInContext("symbol='ETHUSDT'; refresh()", ctx);
  const take = path => pending.find(p => p.path === path && !p.used);
  async function reply(path, value) {const p=take(path); if(!p)throw Error('missing '+path);p.used=true;p.resolve(value);await new Promise(r=>setImmediate(r));}
  await reply('/api/levels?symbol=ETHUSDT', []);
  await reply('/api/logs?symbol=ETHUSDT', {events:[]});
  await reply('/api/candles?symbol=ETHUSDT&timeframe=1m', [{symbol:'ETHUSDT'}]);
  await reply('/api/grid/footprint?symbol=ETHUSDT', []);
  await reply('/api/research?symbol=ETHUSDT', []);
  await newer;
  await reply('/api/levels?symbol=BTCUSDT', [{price:100,timeframe:'1h',side:'high'}]);
  assert.equal(vm.runInContext('currentLevels.length', ctx), 0, 'stale BTC refresh must not overwrite ETH levels');
})();

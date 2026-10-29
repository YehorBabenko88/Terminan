const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync('terminan/index.html','utf8');
const script=html.match(/<script>([\s\S]*?)<\/script>/)[1];
assert(script.includes('const controller=new AbortController();refreshController=controller;'),
       'refresh must capture per-generation controller');
assert(script.includes("el('showlevels').onchange=()=>draw(lastCandles)"),
       'level toggle must redraw without network');
const handlers={};let aborts=0;
class Controller{constructor(){this.signal={aborted:false,addEventListener(){},removeEventListener(){}}}abort(){this.signal.aborted=true;aborts++}}
const els={};const make=id=>els[id]||=({id,value:id==='tf'?'1m':'',checked:true,clientWidth:400,clientHeight:250,
 textContent:'',style:{},replaceChildren(){},append(){},getContext(){return {scale(){},clearRect(){},stroke(){},beginPath(){},moveTo(){},lineTo(){},fillRect(){},fillText(){},setLineDash(){}}}});
const ctx={document:{getElementById:make,createElement:()=>({})},AbortController:Controller,
 devicePixelRatio:1,fetch:async(path,{signal})=>({ok:true,json:async()=>path==='/api/instruments'?['BTCUSDT']:path.startsWith('/api/levels')?[]:path.startsWith('/api/logs')?{events:[]}:path.startsWith('/api/research')?[]:path.startsWith('/api/sources')?{}:path.startsWith('/api/consumer')?{}:[]}),
 setTimeout(){return 1},clearTimeout(){},console};
vm.createContext(ctx);vm.runInContext(script,ctx);
setImmediate(async()=>{try{assert.equal(typeof make('refresh').onclick,'function');assert.equal(typeof make('search').oninput,'function');assert.equal(typeof make('tf').onchange,'function');assert.equal(typeof make('showlevels').onchange,'function');
make('refresh').onclick();make('refresh').onclick();assert(aborts>=1,'refresh must abort previous generation');
make('showlevels').onchange();console.log('UI_BUTTON_HANDLERS_PASS');}catch(error){console.error(error);process.exitCode=1;}});

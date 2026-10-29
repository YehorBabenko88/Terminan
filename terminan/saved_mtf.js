'use strict';
/* Pure, bounded offline minute-to-period aggregation. No network, source authority or execution. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.SavedMTF=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
 const periods=Object.freeze({'1m':1,'5m':5,'15m':15,'1h':60,'4h':240,'1d':1440});
 const finite=n=>typeof n==='number'&&Number.isFinite(n);
 function aggregate(candles,levels,tf){
  const minutes=periods[tf];if(!minutes)throw Error('UNSUPPORTED_TIMEFRAME');
  if(!Array.isArray(candles)||!Array.isArray(levels)||candles.length>200||levels.length>200)throw Error('RESOURCE_LIMIT');
  const ms=minutes*60000,byTime=new Map(),foot=new Map();
  for(const c of candles){
   if(!Number.isSafeInteger(c.ts)||c.ts%60000!==0||byTime.has(c.ts)||
      !['open','high','low','close','buy_volume','sell_volume'].every(k=>finite(c[k]))||
      c.low>Math.min(c.open,c.close)||c.high<Math.max(c.open,c.close)||
      c.buy_volume<0||c.sell_volume<0)throw Error('INVALID_CANDLE');
   byTime.set(c.ts,c);
  }
  for(const r of levels){
   if(!Number.isSafeInteger(r.ts)||r.ts%60000!==0||!finite(r.price)||
      !['buy_volume','sell_volume'].every(k=>finite(r[k]))||
      r.buy_volume<0||r.sell_volume<0)throw Error('INVALID_FOOTPRINT');
   const bucket=Math.floor(r.ts/ms)*ms;
   if(!foot.has(bucket))foot.set(bucket,[]);
   foot.get(bucket).push(r);
  }
  const buckets=new Map();
  for(const c of candles){
   const t=Math.floor(c.ts/ms)*ms;
   if(!buckets.has(t))buckets.set(t,[]);
   buckets.get(t).push(c);
  }
  const output=[];
  for(const [ts,items] of [...buckets].sort((a,b)=>a[0]-b[0])){
   items.sort((a,b)=>a.ts-b.ts);
   const complete=items.length===minutes&&items.every((c,i)=>c.ts===ts+i*60000);
   const buy=items.reduce((v,c)=>v+c.buy_volume,0),sell=items.reduce((v,c)=>v+c.sell_volume,0);
   const perPrice=new Map();
   for(const r of foot.get(ts)||[]){
    if(!byTime.has(r.ts))continue;
    const key=String(r.price);
    if(!perPrice.has(key))perPrice.set(key,{price:r.price,buy_volume:0,sell_volume:0});
    const x=perPrice.get(key);x.buy_volume+=r.buy_volume;x.sell_volume+=r.sell_volume;
   }
   const rows=[...perPrice.values()].map(x=>({...x,volume:x.buy_volume+x.sell_volume,delta:x.buy_volume-x.sell_volume})).sort((a,b)=>b.price-a.price);
   const max=rows.length?Math.max(...rows.map(x=>x.volume)):null;
   const poc=max===null?null:rows.find(x=>x.volume===max).price;
   output.push({ts,timeframe:tf,complete,observed_minutes:items.length,required_minutes:minutes,
    open:items[0].open,high:Math.max(...items.map(c=>c.high)),low:Math.min(...items.map(c=>c.low)),
    close:items[items.length-1].close,buy_volume:buy,sell_volume:sell,volume:buy+sell,delta:buy-sell,
    levels:rows,poc_price:complete&&rows.length?poc:null,
    footprint_complete:complete&&items.every(c=>(foot.get(ts)||[]).some(r=>r.ts===c.ts))});
  }
  return output;
 }
 return Object.freeze({periods,aggregate});
});

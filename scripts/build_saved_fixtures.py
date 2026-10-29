import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'terminan/fixtures';cat=json.loads((p/'saved-catalog-v1.json').read_text());base=1767225600000

def row(src,table,values):
 spec=cat[src]['datasets'][table];r={}
 for k in spec['projection']:
  c=spec['columns'][k];r[k]=None if c['nullable'] else 0 if c['type'] in ('integer','bigint','bigserial','numeric','real','double precision') else {} if c['type'] in ('json','jsonb') else False if c['type']=='boolean' else ''
 r.update(values);return r

grid={'candles_1m':[],'footprint_1m':[],'derivatives_metrics':[]}
for symbol,mult in [('BTCUSDT',1),('ETHUSDT',.06)]:
 for i in range(48):
  price=round((60000+i*3)*mult,2);t=base+i*60000
  grid['candles_1m'].append(row('grid','candles_1m',dict(symbol=symbol,ts=t,open=price,high=price+20*mult,low=price-20*mult,close=price+10*mult,buy_volume=10+i,sell_volume=6+i,delta=4,trade_count=100+i,poc_price=price,quality_status='COMPLETE',quality_reasons=[])))
  if i<12:
   for level in range(6):
    buy=3+level;sell=2+level
    grid['footprint_1m'].append(row('grid','footprint_1m',dict(symbol=symbol,ts=t,price=price+(level-3)*mult,buy_volume=buy,sell_volume=sell,delta=buy-sell,volume=buy+sell,buy_count=buy,sell_count=sell)))
 grid['derivatives_metrics'].append(row('grid','derivatives_metrics',dict(symbol=symbol,ts=base,open_interest=1000,funding_rate=.0001,mark_price=60000*mult,index_price=59999*mult,basis=1*mult)))
market={}
for table,spec in cat['strattester']['datasets'].items():
 if spec['schema_id']!='market2' or not spec['supported']:continue
 values=[]
 for symbol in ('BTCUSDT','ETHUSDT'):
  for i in range(12):
   x=dict(symbol=symbol)
   for k in spec['projection']:
    if k=='timeframe':x[k]='1m'
    elif k in ('open_time','funding_time'):x[k]=base+i*60000
    elif k in ('open','close'):x[k]=100+i
    elif k=='high':x[k]=102+i
    elif k=='low':x[k]=99+i
    elif k=='complete':x[k]=1
    elif k in ('volume','buy_volume','sell_volume','trade_count','turnover','value'):x[k]=10
   values.append(row('strattester',table,x))
 market[table]=values
research={'research_results':[]}
for i in range(6):
 research['research_results'].append(row('strattester','research_results',dict(run_id=f'run-{i:03}',symbol='BTCUSDT',strategy_id='poc-reversion' if i%2 else 'smc-breakout',strategy_version='1.2',created_at=base+i*60000,metrics=dict(trades=40,wins=24,losses=16,win_rate=.6,net_pnl=120.5-i,gross_pnl=140,fees=19.5,max_drawdown=35,profit_factor=1.7,expectancy=3.01,avg_mae=1.5,avg_mfe=3.2,avg_r_multiple=.6,avg_holding_ms=120000,max_consecutive_losses=3,coverage='COMPLETE_HISTORY',fingerprint='synthetic-fixture-v1'),job_id=None,node_generation=0)))
for source,schema,file,data in [('grid','grid46','saved-grid-v1.json',grid),('strattester','market2','saved-market-v1.json',market),('strattester','results1','saved-research-v1.json',research)]:
 x=dict(version=1,source=source,schema_id=schema,source_sha=cat[source]['sha'],as_of_ms=base+60*60000,mode='SYNTHETIC',symbols=['BTCUSDT','ETHUSDT'],datasets=data)
 (p/file).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n',encoding='utf8')

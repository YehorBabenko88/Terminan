import copy, hashlib, json, unittest
from pathlib import Path
from terminan.analytics.ohlcv_research import analyze_ohlcv_research
from terminan.analytics.market_history import analyze_market_history

def digest(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def ohlcv():
 p=dict(schema='terminan.ohlcv.research.request.v1',venue='bybit',market_type='linear',symbol='ETHUSDT',timeframe='1m',units={'price':'USDT/ETH','volume':'ETH'},start_ms=0,end_ms=180000,as_of_ms=300000,evidence_class='SYNTHETIC',source=dict(kind='HISTORICAL_BACKFILL',identity='SYNTHETIC_TEST_INPUT',source_revision='a'*40,retrieval_id='SYNTHETIC_TEST_INPUT',retrieved_at_ms=240000,raw_sha256='b'*64),rows=[dict(event_start_ms=i*60000,event_end_ms=(i+1)*60000,open=o,high=h,low=l,close=c,volume=v) for i,(o,h,l,c,v) in enumerate(((10,12,8,11,3),(10,11,9,10,2),(11,12,10,12,4)))])
 seal_ohlcv(p);return p
def seal_ohlcv(p):
 fields=('venue','market_type','symbol','timeframe','units','start_ms','end_ms','source','evidence_class','rows')
 p['dataset_id']=digest(dict(schema='terminan.ohlcv.dataset.v1',**{k:p[k] for k in fields}))
def history():
 return json.loads((Path(__file__).parent/'fixtures/market_history/synthetic-v11.json').read_text())
def seal_history(p):
 q=p['request'];p['dataset_id']=digest(dict(schema='market_data.dataset.v1.1',source=p['source'],identity={k:q[k] for k in ('venue','market_type','symbol','units')},timeframe='1m',representation='historical_aggregate',evidence_class=p['evidence_class'],rows=p['rows'],source_receipts=p['source_receipts']))
 p['dataset_fingerprint']=digest({k:v for k,v in p.items() if k!='dataset_fingerprint'})
class HistoricalAnalyticsTests(unittest.TestCase):
 def test_hand_calculated_levels_and_immutable_inputs(self):
  p=ohlcv();before=copy.deepcopy(p);out=analyze_ohlcv_research(p,decision_ms=300000,now_ms=360000)
  self.assertEqual([(r['kind'],r['price'],r['source_start_ms']) for r in out['levels']],[('low','8',0),('low','9',60000),('high','12',120000),('low','10',120000)])
  self.assertEqual(out['schema'],'terminan.ohlcv.research.result.v1');self.assertEqual(out['quality_status'],'UNKNOWN')
  self.assertEqual(out['source_authenticity'],'NOT_EVALUATED')
  for key in ('execution_authority','trading_authorized','training_authorized','h_b_eligible'):self.assertIs(out[key],False)
  out['rows'][0]['close']=99;self.assertEqual(p,before)
 def test_resealed_invalid_ohlcv_is_refused(self):
  mutations=[lambda p:p.update(schema='meta.ohlcv.research.request.v1'),lambda p:p.update(as_of_ms=360001),lambda p:p['source'].update(retrieved_at_ms=179999),lambda p:p['rows'][0].update(close=True),lambda p:p['rows'][0].update(volume=-1),lambda p:p['rows'][0].update(high=9),lambda p:p['rows'][0].update(event_end_ms=60001),lambda p:p['rows'].reverse(),lambda p:p['rows'].pop(),lambda p:p.update(training_authorized=True),lambda p:p['rows'][0].update(available_at_ms=60000)]
  for mutate in mutations:
   p=ohlcv();mutate(p);seal_ohlcv(p)
   with self.subTest(mutate=mutate),self.assertRaises(ValueError):analyze_ohlcv_research(p,decision_ms=300000,now_ms=360000)
 def test_cannot_use_backfill_before_retrieval_or_future(self):
  for decision in (-1,True,239999,300001,360001):
   with self.subTest(decision=decision),self.assertRaises(ValueError):analyze_ohlcv_research(ohlcv(),decision_ms=decision,now_ms=360000)
 def test_history_as_of_excludes_future_and_delayed_rows(self):
  p=history();before=copy.deepcopy(p);out=analyze_market_history(p,decision_ms=60000)
  self.assertEqual(len(out['rows']),1);self.assertEqual(out['coverage_status'],'PARTIAL')
  self.assertEqual(p,before);p['rows'][-1]['low']=1;seal_history(p)
  later=analyze_market_history(p,decision_ms=60000)
  self.assertEqual(out['candles'],later['candles']);self.assertEqual(out['levels'],later['levels'])
 def test_gap_suppresses_levels(self):
  p=history();p['rows'][0]['available_at_ms']=170000;seal_history(p)
  out=analyze_market_history(p,decision_ms=120000)
  self.assertEqual(out['coverage_status'],'GAP');self.assertEqual(out['levels'],[])
 def test_retired_schema_and_corruption_are_refused(self):
  for schema in ('grid.history.v1.1','meta.grid.history.analysis.v1'):
   p=history();p['schema']=schema;seal_history(p)
   with self.subTest(schema=schema),self.assertRaises(ValueError):analyze_market_history(p,decision_ms=180000)
  p=history();p['rows'][0]['close']=100.5
  with self.assertRaises(ValueError):analyze_market_history(p,decision_ms=180000)
 def test_receipt_integrity_never_promotes_authority(self):
  p=history();p['evidence_class']='HISTORICAL';seal_history(p);out=analyze_market_history(p,decision_ms=180000)
  self.assertEqual(out['quality_status'],'UNKNOWN');self.assertEqual(out['source_authenticity'],'NOT_EVALUATED');self.assertEqual(out['coverage_status'],'DECLARED_COMPLETE_UNVERIFIED')
  for key in ('execution_authority','trading_authorized','training_authorized'):self.assertIs(out[key],False)

 def test_canonical_historical_api_and_fake_http_handler(self):
  from terminan.analytics.api import analyze_historical
  request=dict(schema='terminan.analytics.historical.v1',mode='market_history',payload=history(),decision_ms=180000)
  self.assertEqual(analyze_historical(request)['schema'],'terminan.market.history.analysis.v1')
  with self.assertRaises(ValueError):analyze_historical({**request,'now_ms':999999})
  from terminan.server import Handler
  from email.message import Message
  from io import BytesIO
  from types import SimpleNamespace
  raw=json.dumps(request).encode();h=Handler.__new__(Handler)
  h.path='/api/analytics/historical';h.connection=SimpleNamespace(settimeout=lambda value:None)
  h.rfile=BytesIO(raw);h.wfile=BytesIO();h.headers=Message()
  for name,value in [('Content-Length',str(len(raw))),('Content-Type','application/json'),('Host','127.0.0.1:18765')]:h.headers[name]=value
  statuses=[];h.send_response=statuses.append;h.send_header=lambda *args:None;h.end_headers=lambda:None;h.send_error=lambda code:statuses.append(code)
  h.do_POST();self.assertEqual(statuses,[200]);self.assertEqual(json.loads(h.wfile.getvalue())['schema'],'terminan.market.history.analysis.v1')

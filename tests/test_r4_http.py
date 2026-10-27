import json,socket,threading,time,unittest
from urllib.request import urlopen,Request
from urllib.error import HTTPError
from terminan.r4_server import R4Server,R4Handler
class R4HTTP(unittest.TestCase):
 def setUp(self):
  self.server=R4Server(('127.0.0.1',0),R4Handler);self.server.candidate_sha='a'*40;self.server.source_clean=True;self.thread=threading.Thread(target=self.server.serve_forever);self.thread.start();self.url='http://127.0.0.1:'+str(self.server.server_port)
 def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join()
 def get(self,path):
  with urlopen(self.url+path,timeout=2) as r:return json.load(r)
 def test_identity_contracts_and_no_source_routes(self):
  for symbol in ('BTCUSDT','ETHUSDT','SOLUSDT'):
   for tf in ('1m','5m','15m','1h'):
    value=self.get('/api/synthetic/contracts?symbol='+symbol+'&timeframe='+tf)
    self.assertEqual((value['symbol'],value['timeframe']),(symbol,tf));self.assertTrue(all(v['symbol']==symbol and v['runtime_source']=='NONE' for v in value['sources']))
    for v in value['sources']:
     if v['source']=='grid' and tf!='1m':self.assertEqual(v['state'],'UNSUPPORTED_TIMEFRAME');self.assertEqual(v['rows'],[])
     else:self.assertEqual(v['timeframe'],tf);self.assertEqual(v['state'],'HISTORICAL_ONLY')
  for path in ('/api/levels','/api/grid/footprint','/api/research'):
   with self.assertRaises(HTTPError) as error:self.get(path)
   self.assertEqual(error.exception.code,404)
 def test_end_receipt_not_connection_refusal(self):
  a=self.get('/api/session');self.server.session.end();b=self.get('/api/session?session_id='+a['session_id']);self.assertEqual(b['state'],'SESSION_ENDED')
  with self.assertRaises(HTTPError) as error:self.get('/api/synthetic/frame')
  self.assertEqual(error.exception.code,410)
  with self.assertRaises(HTTPError) as error:self.get('/api/session?session_id='+'b'*32)
  self.assertEqual(error.exception.code,400)
 def test_reject_invalid_queries_and_origin(self):
  for query in ('step=601','symbol=OTHER','seed=-1','seed=1&seed=2','timeframe=0','dsn=PRIVATE_NEVER_ECHO'):
   with self.assertRaises(HTTPError) as error:self.get('/api/synthetic/frame?'+query)
   self.assertEqual(error.exception.code,400);self.assertNotIn(b'PRIVATE_NEVER_ECHO',error.exception.read())
  with self.assertRaises(HTTPError) as error:urlopen(Request(self.url+'/api/session',headers={'Origin':'https://not-local.example'}),timeout=2)
  self.assertEqual(error.exception.code,403)

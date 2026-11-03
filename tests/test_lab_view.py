import copy,json,os,tempfile,time,unittest,threading
from pathlib import Path
from unittest.mock import patch
from urllib.request import urlopen,Request
from urllib.error import HTTPError
from terminan import lab_view

def sample(now):
 return dict(schema='unified.lab.market-paper.v1',mode='LAB_SIMULATION',trading_authorized=False,release_id='lab-1',run_id='run-1',sequence=1,generated_at_ms=now,quotes=[dict(symbol=f'COIN{i}USDT',last_price=10,bid=9,ask=11,event_ts_ms=now,source='BYBIT_PUBLIC') for i in range(10)],trades=[],strategies=[dict(id='strategy1',status='READY',trades=0,error_code=None)],nodes=[dict(node_id=n,role='CONTROL' if n=='LS5' else 'WORKER',state='READY',last_heartbeat_ms=now,error_code=None) for n in ('LS5','PC1','PC2','PC3','PC4','LS7')],errors=[])
class LabTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)/'snapshot.json';self.now=int(time.time()*1000);self.data=sample(self.now)
 def read(self,data=None):
  self.path.write_text(json.dumps(self.data if data is None else data),encoding='utf-8')
  os.utime(self.path,(self.now/1000,)*2)
  return lab_view.overview(str(self.path),now_ms=self.now)
 def test_reported_and_freshness(self):
  out=self.read();self.assertEqual(out['state'],'AVAILABLE');self.assertEqual(out['authority'],'REPORTED_UNATTESTED');self.assertFalse(out['trading_authorized']);self.assertEqual(len(out['quotes']),10)
  self.data['quotes'][0]['event_ts_ms']-=16000;self.assertEqual(self.read()['state'],'STALE')
  self.data=sample(self.now);self.data['nodes'][0]['last_heartbeat_ms']-=31000;self.assertEqual(self.read()['nodes'][0]['state'],'STALE')
 def test_fail_closed_inputs(self):
  for mutate in [lambda d:d.update(extra='private'),lambda d:d['quotes'][0].update(last_price=float('nan')),lambda d:d['quotes'][0].update(bid=12),lambda d:d['quotes'][0].update(event_ts_ms=self.now+1),lambda d:d['nodes'][0].update(node_id='ADMINIT'),lambda d:d.update(run_id='postgres://secret'),lambda d:d['quotes'].pop(),lambda d:d['strategies'][0].update(error_code='private/path')]:
   data=sample(self.now);mutate(data);out=self.read(data);self.assertEqual(out['state'],'UNAVAILABLE');self.assertEqual(out['quotes'],[])
  self.path.write_text('{"mode":1,"mode":2}');self.assertEqual(lab_view.overview(str(self.path))['state'],'UNAVAILABLE')
  self.assertEqual(lab_view.overview('relative.json')['state'],'UNAVAILABLE')
  self.assertEqual(lab_view.overview('')['state'],'UNAVAILABLE')
 def test_hardlink_and_limit(self):
  self.read();link=Path(self.tmp.name)/'linked';os.link(self.path,link);self.assertEqual(lab_view.overview(str(self.path))['state'],'UNAVAILABLE');link.unlink()
  self.path.write_bytes(b' '*1048577);self.assertEqual(lab_view.overview(str(self.path))['state'],'UNAVAILABLE')
 def test_loopback_routes_and_gates(self):
  from terminan.unified_server import UnifiedServer,UnifiedHandler
  server=UnifiedServer(('127.0.0.1',0),UnifiedHandler);server.candidate_sha='a'*40
  worker=threading.Thread(target=server.serve_forever);worker.start()
  try:
   self.read();base='http://127.0.0.1:'+str(server.server_port)
   with patch.dict(os.environ,TERMINAN_LAB_SNAPSHOT=str(self.path)):
    with urlopen(base+'/api/lab/overview',timeout=3) as r:self.assertEqual(json.load(r)['state'],'AVAILABLE')
    with urlopen(base+'/lab',timeout=3) as r:self.assertIn(b'REPORTED_UNATTESTED',r.read())
    for path,headers,code in [('/lab',{'Origin':'https://evil.invalid'},403),('/api/lab/overview?path=secret',{},400)]:
     with self.assertRaises(HTTPError) as e:urlopen(Request(base+path,headers=headers),timeout=3)
     self.assertEqual(e.exception.code,code)
    server.session.end()
    with self.assertRaises(HTTPError) as e:urlopen(base+'/api/lab/overview',timeout=3)
    self.assertEqual(e.exception.code,410)
  finally:server.shutdown();server.server_close();worker.join(5)
 def test_trade_causality_closed_schema_and_stale_file(self):
  self.data['trades']=[dict(trade_id='t1',symbol='COIN0USDT',strategy='strategy1',side='BUY',entry_ts_ms=self.now-100,exit_ts_ms=self.now,entry_price=10,exit_price=11,qty=2,fees=.1,funding=0,slippage=.01,pnl=1.89,status='CLOSED')]
  self.assertEqual(self.read()['trades'][0]['pnl'],1.89)
  self.data['trades'][0]['exit_ts_ms']=self.now-101;self.assertEqual(self.read()['state'],'UNAVAILABLE')
  self.data=sample(self.now);self.read();os.utime(self.path,((self.now-16000)/1000,)*2);self.assertEqual(lab_view.overview(str(self.path),now_ms=self.now)['state'],'STALE')
  self.data['quotes'][1]=self.data['quotes'][0];self.assertEqual(self.read()['state'],'UNAVAILABLE')
 def test_symlink_if_platform_allows(self):
  self.read();link=Path(self.tmp.name)/'symlink'
  try:link.symlink_to(self.path)
  except OSError:self.skipTest('Windows symlink privilege unavailable')
  self.assertEqual(lab_view.overview(str(link))['state'],'UNAVAILABLE')
 def test_reserved_node_labels_and_alternate_stream_paths(self):
  self.data['release_id']='ADMINIT';self.assertEqual(self.read()['state'],'UNAVAILABLE')
  self.assertEqual(lab_view.overview(str(self.path)+':stream')['state'],'UNAVAILABLE')


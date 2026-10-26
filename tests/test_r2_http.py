import http.client
import json
import os
import threading
import unittest
from unittest.mock import patch
from terminan.r2_server import R2Handler, R2Server

class SyntheticHTTP(unittest.TestCase):
    def setUp(self):
        self.server=R2Server(('127.0.0.1',0),R2Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.close)
    def close(self):
        self.server.shutdown();self.server.server_close();self.thread.join(3)
    def get(self,path,headers=None):
        c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        try:
            c.request('GET',path,headers=headers or {});r=c.getresponse()
            return r.status,r.read()
        finally:c.close()
    def test_synthetic_end_to_end_and_contract_faults(self):
        status,body=self.get('/api/synthetic/frame?seed=17&step=24&scenario=gap&symbol=ETHUSDT&timeframe=5m')
        self.assertEqual(status,200);data=json.loads(body)
        self.assertEqual(data['mode'],'SYNTHETIC');self.assertEqual(data['dom']['status'],'GAP')
        self.assertEqual(data['symbol'],'ETHUSDT')
        status,body=self.get('/api/synthetic/contracts?scenario=future')
        self.assertEqual(status,200)
        self.assertTrue(all(v['state']=='FUTURE_LEAKAGE' for v in json.loads(body)['sources']))
    def test_never_dispatches_to_real_sources(self):
        with patch.dict(os.environ,{'TERMINAN_GRID_DSN':'SECRET','TERMINAN_STRATTESTER_DB':'SECRET'}), patch('terminan.g0_sources.grid_rows',side_effect=AssertionError('DB access')),patch('terminan.g0_sources.sqlite_rows',side_effect=AssertionError('DB access')):
            self.assertEqual(self.get('/api/synthetic/frame')[0],200)
            self.assertEqual(self.get('/api/candles')[0],404)
            self.assertEqual(self.get('/api/monitor')[0],404)
    def test_negative_query_and_rebinding(self):
        for path in ['/api/synthetic/frame?step=601','/api/synthetic/frame?step=NaN','/api/synthetic/frame?seed=1&seed=2','/api/synthetic/frame?dsn=secret','/api/synthetic/frame?symbol=BAD','/api/synthetic/frame?timeframe=1w']:
            self.assertEqual(self.get(path)[0],400,path)
        self.assertEqual(self.get('/api/status',{'Host':'evil.example'})[0],403)

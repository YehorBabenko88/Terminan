import http.client
import json
import threading
import unittest
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch
from terminan import server

class HTTPContract(unittest.TestCase):
    def setUp(self):
        self.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        self.thread=threading.Thread(target=self.http.serve_forever,daemon=True); self.thread.start()
        self.addCleanup(self.close)
    def close(self):
        self.http.shutdown();self.http.server_close();self.thread.join(3)
    def request(self,path,headers=None):
        con=http.client.HTTPConnection('127.0.0.1',self.http.server_port,timeout=3)
        try:
            con.request('GET',path,headers=headers or {})
            res=con.getresponse();return res.status,res.read()
        finally:con.close()
    def test_versioned_disconnected_sources(self):
        status,body=self.request('/api/sources?symbol=BTCUSDT')
        self.assertEqual(status,200);self.assertEqual(json.loads(body)['l2'],'UNAVAILABLE')
    def test_levels_cannot_bypass_schema_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'synthetic.sqlite'
            con=sqlite3.connect(path)
            try:
                con.executescript("CREATE TABLE schema_meta(key TEXT,value TEXT); INSERT INTO schema_meta VALUES('schema_version','99'); CREATE TABLE candles(symbol TEXT,timeframe TEXT,open_time INTEGER,open REAL,high REAL,low REAL,close REAL,volume REAL,complete INTEGER);")
                con.commit()
            finally:con.close()
            with patch.dict(os.environ,{'TERMINAN_STRATTESTER_DB':str(path)}):
                self.assertEqual(self.request('/api/levels?diagnostics=1')[0],503)
    def test_invalid_and_duplicate_query_rejected(self):
        for path in ('/api/candles?symbol=bad','/api/candles?symbol=BTCUSDT&symbol=ETHUSDT','/api/candles?timeframe=1w'):
            self.assertEqual(self.request(path)[0],400)
    def test_rebinding_host_and_cross_origin_rejected(self):
        self.assertEqual(self.request('/api/status',{'Host':'evil.example'})[0],403)
        self.assertEqual(self.request('/api/status',{'Origin':'https://evil.example'})[0],403)


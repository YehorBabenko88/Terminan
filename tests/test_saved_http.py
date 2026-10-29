import json, threading, unittest
from urllib.request import urlopen
from urllib.error import HTTPError
from terminan.saved_server import SavedServer, SavedHandler
from terminan.saved_sources import SavedSources, demo_config

class SavedHTTPTests(unittest.TestCase):
 def setUp(self):
  self.server=SavedServer(('127.0.0.1',0),SavedHandler);self.server.saved=SavedSources(demo_config());self.server.candidate_sha='a'*40
  self.thread=threading.Thread(target=self.server.serve_forever);self.thread.start();self.url=f'http://127.0.0.1:{self.server.server_port}'
 def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join()
 def test_pages_and_errors(self):
  with urlopen(self.url+'/saved') as r:self.assertIn(b'Historical workspace',r.read())
  with urlopen(self.url+'/api/saved/page?source=grid-demo&dataset=candles_1m&limit=2') as r:self.assertEqual(len(json.load(r)['rows']),2)
  for query in ('limit=-1','limit=2&limit=3','path=secret','limit=9999'):
   with self.assertRaises(HTTPError) as e:urlopen(self.url+'/api/saved/page?source=grid-demo&dataset=candles_1m&'+query)
   try:
    body=e.exception.read();self.assertNotIn(b'Traceback',body);self.assertNotIn(b'Users',body)
   finally:e.exception.close()

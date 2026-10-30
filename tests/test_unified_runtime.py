import json, threading, unittest
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from terminan.unified_server import UnifiedServer, UnifiedHandler

class UnifiedRuntimeTests(unittest.TestCase):
 def setUp(self):
  self.server=UnifiedServer(('127.0.0.1',0),UnifiedHandler);self.server.candidate_sha='a'*40;self.server.source_clean=True
  self.thread=threading.Thread(target=self.server.serve_forever);self.thread.start();self.url='http://127.0.0.1:'+str(self.server.server_port)
 def tearDown(self):
  self.server.session.end();self.server.shutdown();self.server.server_close();self.thread.join(5)
  self.assertFalse(self.thread.is_alive());self.assertEqual(self.server.diagnostics.snapshot()['active_workers'],0)
 def get(self,path,headers=None):
  try:
   with urlopen(Request(self.url+path,headers=headers or {}),timeout=5) as r:return r.status,r.read(),r.headers
  except HTTPError as e:return e.code,e.read(),e.headers
 def test_six_real_pages_and_assets(self):
  for path in ('/','/saved','/math','/history-overlay','/monitor','/cache'):
   code,body,headers=self.get(path);self.assertEqual(code,200);self.assertIn(b'unified.js',body)
  for path,marker in (('/workspace/terminal',b'chart'),('/workspace/saved',b'saved-chart'),('/workspace/math',b'workspace'),('/workspace/history-overlay',b'overlay.js'),('/workspace/monitor',b'nodes'),('/workspace/cache',b'cache')):
   code,body,headers=self.get(path);self.assertEqual(code,200,path);self.assertIn(marker.lower(),body.lower(),path)
 def test_sources_disabled_and_session_end(self):
  self.assertEqual(json.loads(self.get('/api/status')[1])['mode'],'SYNTHETIC')
  self.assertEqual(json.loads(self.get('/api/infrastructure')[1])['state'],'UNAVAILABLE')
  self.assertEqual(json.loads(self.get('/api/cache/status')[1])['mode'],'DISABLED')
  self.server.session.end()
  self.assertEqual(self.get('/api/saved/catalog')[0],410)
  self.assertEqual(self.get('/api/synthetic/frame')[0],410)
  self.assertEqual(json.loads(self.get('/api/session')[1])['state'],'SESSION_ENDED')
 def test_post_is_fenced_before_and_after_body_read(self):
  import http.client
  from unittest.mock import patch
  port=self.server.server_port
  c=http.client.HTTPConnection('127.0.0.1',port,timeout=2)
  c.putrequest('POST','/api/history-overlay/validate');c.putheader('Origin',self.url);c.putheader('Content-Type','application/json');c.putheader('Content-Length','2');c.endheaders()
  self.server.session.end()
  with patch('terminan.history_overlay.admit',side_effect=AssertionError('MUST_NOT_EXECUTE')):
   c.send(b'{}');self.assertEqual(c.getresponse().status,410)
  c.close()
 def test_trickled_body_has_absolute_deadline(self):
  import socket,time
  self.server.request_budget_seconds=.25
  s=socket.create_connection(('127.0.0.1',self.server.server_port),timeout=2)
  s.sendall(('POST /api/history-overlay/validate HTTP/1.0\r\nHost: 127.0.0.1:'+str(self.server.server_port)+'\r\nOrigin: '+self.url+'\r\nContent-Type: application/json\r\nContent-Length: 200\r\n\r\n{').encode())
  time.sleep(.5)
  self.assertEqual(s.recv(1),b'');s.close()
 def test_occupied_listener_is_never_shared(self):
  other=None
  try:
   with self.assertRaises(OSError):other=UnifiedServer(('127.0.0.1',self.server.server_port),UnifiedHandler)
  finally:
   if other:other.server_close()
 def test_gates_and_no_execution(self):
  self.assertEqual(self.get('/saved',{'Host':'evil.invalid'})[0],403)
  self.assertEqual(self.get('/math',{'Origin':'https://evil.invalid'})[0],403)
  self.assertEqual(self.get('/workspace/../math')[0],404)
  self.assertEqual(self.get('/api/session?x='+('a'*2100))[0],414)
  self.assertEqual(self.get('/api/trade')[0],404)
if __name__=='__main__':unittest.main()

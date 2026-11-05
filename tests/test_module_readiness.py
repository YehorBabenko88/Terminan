"""Real loopback HTTP with explicit test snapshots; no physical qualification."""
import copy,json,os,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from terminan.unified_server import UnifiedServer,UnifiedHandler
from tests.test_runtime_v2 import fixture

class ModuleReadinessTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.path=Path(self.temp.name)/'snapshot.json';self.snapshot=fixture()
  # The core aggregate is deliberately false: no startup dependency cycle.
  self.snapshot['modules']['terminan'].update(state='STARTING',ready=False)
  self.snapshot['ready']=False;self.path.write_text(json.dumps(self.snapshot))
  self.token='a'*64
  self.env=patch.dict(os.environ,dict(UNIFIED_MODULE_ID='terminan',UNIFIED_MODULE_VERSION='1.0.0',UNIFIED_RELEASE_ID='test:1',UNIFIED_INSTANCE_TOKEN=self.token,TERMINAN_RUNTIME_V2_SNAPSHOT=str(self.path)))
  self.env.start();self.addCleanup(self.env.stop)
  self.server=UnifiedServer(('127.0.0.1',0),UnifiedHandler);self.server.candidate_sha='b'*40;self.server.source_clean=True
  self.thread=threading.Thread(target=self.server.serve_forever);self.thread.start();self.base='http://127.0.0.1:'+str(self.server.server_port)
  self.addCleanup(self.close)
 def close(self):
  self.server.session.end();self.server.shutdown();self.server.server_close();self.thread.join(3)
  self.assertFalse(self.thread.is_alive())
 def get(self,token=True,path='/internal/v2/module/health',extra=None):
  headers={} if not token else {'Authorization':'Bearer '+self.token}
  headers.update(extra or {})
  try:
   with urlopen(Request(self.base+path,headers=headers),timeout=3) as r:return r.status,json.load(r)
  except HTTPError as e:
   raw=e.read()
   try:body=json.loads(raw)
   except ValueError:body={}
   return e.code,body
 def test_real_http_readiness_binds_nonce_and_local_release_without_global_ready(self):
  before=self.path.read_bytes();code,body=self.get()
  self.assertEqual(code,200);self.assertEqual(body,dict(module_id='terminan',version='1.0.0',release_id='test:1',instance_token=self.token,ready=True))
  self.assertEqual(self.path.read_bytes(),before)
 def test_missing_or_wrong_bearer_never_discloses_instance(self):
  for headers in ({},{'Authorization':'Bearer wrong'}):
   code,body=self.get(token=False,extra=headers);self.assertEqual(code,403);self.assertNotIn(self.token,str(body))
 def test_missing_identity_is_unavailable_and_query_is_forbidden(self):
  for key in ('UNIFIED_MODULE_ID','UNIFIED_MODULE_VERSION','UNIFIED_RELEASE_ID','UNIFIED_INSTANCE_TOKEN'):
   with patch.dict(os.environ,{key:''}),self.subTest(key=key):self.assertEqual(self.get()[0],503)
  for suffix in ('?ready=1','?'):
   self.assertEqual(self.get(path='/internal/v2/module/health'+suffix)[0],400)
 def test_dirty_source_invalid_candidate_and_ended_session_never_ready(self):
  self.server.source_clean=False;self.assertIs(self.get()[1]['ready'],False)
  self.server.source_clean=True;self.server.candidate_sha='invalid';self.assertIs(self.get()[1]['ready'],False)
  self.server.candidate_sha='b'*40;self.server.session.end();self.assertIs(self.get()[1]['ready'],False)
 def test_missing_snapshot_version_release_and_physical_forgery_fail_closed(self):
  for fault in ('missing','version','release','physical'):
   p=copy.deepcopy(self.snapshot)
   if fault=='version':p['modules']['terminan']['version']='2.0.0'
   if fault=='release':p['release_id']='other'
   if fault=='physical':p['physical']='PASS'
   if fault=='missing':self.path.unlink(missing_ok=True)
   else:self.path.write_text(json.dumps(p))
   with self.subTest(fault=fault):self.assertIs(self.get()[1]['ready'],False)
 def test_origin_and_host_gate_remain_authoritative(self):
  self.assertEqual(self.get(extra={'Host':'elsewhere.invalid'})[0],403)
  self.assertEqual(self.get(extra={'Origin':'https://elsewhere.invalid'})[0],403)

import copy,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch

CORE=('unified-system','grid','strattester','math','meta_analyse','terminan')
def fixture():
 return dict(schema='unified.runtime.v2',api_version={'major':2,'minor':0},producer='unified-system',node_id='local',release_id='test:1',release_sha256='a'*64,revision=1,mode='LOCAL_RUNTIME_PREDEPLOYMENT',modules={n:dict(version='1.0.0',api_major=1,dependencies=[],state='READY',ready=True,attempt=0,reason='NONE',administrative_stop=False) for n in CORE},ready=True,fleet_authority='grid',trading_authorized=False,physical='NOT_RUN',physical_deployment_allowed=False)
class RuntimeV2Tests(unittest.TestCase):
 def test_independent_contract_and_mutation_rejections(self):
  from terminan.runtime_v2 import validate_runtime
  p=fixture();self.assertEqual(validate_runtime(p),p)
  mutations=[lambda p:p.update(ready=False),lambda p:p.update(revision=True),lambda p:p.update(physical='PASS'),lambda p:p['modules']['grid'].update(ready=False),lambda p:p['modules']['grid'].update(api_major=True),lambda p:p['modules']['grid'].update(reason='SECRET'),lambda p:p['modules']['grid'].update(dependencies=['grid']),lambda p:p['modules'].pop('math'),lambda p:p.update(cpu=100),lambda p:p['api_version'].update(minor=True)]
  for mutate in mutations:
   q=copy.deepcopy(p);mutate(q)
   with self.subTest(q=q),self.assertRaises(ValueError):validate_runtime(q)
  q=copy.deepcopy(p);q['modules']['grid']['dependencies']=['math'];q['modules']['math']['dependencies']=['grid']
  with self.assertRaises(ValueError):validate_runtime(q)
 def test_local_reader_rejects_duplicates_nonfinite_and_symlinks(self):
  from terminan.runtime_v2 import runtime_snapshot
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'view.json'
   with patch.dict(os.environ,{'TERMINAN_RUNTIME_V2_SNAPSHOT':str(p)}):
    self.assertEqual(runtime_snapshot()['state'],'UNAVAILABLE')
    p.write_text(json.dumps(fixture()));self.assertEqual(runtime_snapshot()['schema'],'unified.runtime.v2')
    for raw in ('{"schema":1,"schema":2}','{"x":NaN}','[]'):
     p.write_text(raw);self.assertEqual(runtime_snapshot()['state'],'UNAVAILABLE')
    p.write_text(json.dumps(fixture()));link=Path(d)/'link.json'
    try:link.symlink_to(p)
    except OSError:return
    with patch.dict(os.environ,{'TERMINAN_RUNTIME_V2_SNAPSHOT':str(link)}):self.assertEqual(runtime_snapshot()['state'],'UNAVAILABLE')
 def test_real_http_runtime_page_and_api(self):
  import threading,urllib.request
  from http.server import ThreadingHTTPServer
  from terminan.server import Handler
  with patch.dict(os.environ,{'TERMINAN_RUNTIME_V2_SNAPSHOT':''}):
   server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
   try:
    base='http://127.0.0.1:'+str(server.server_port)
    with urllib.request.urlopen(base+'/api/runtime-v2') as r:self.assertEqual(json.load(r)['state'],'UNAVAILABLE')
    with urllib.request.urlopen(base+'/runtime') as r:self.assertIn(b'Node-local runtime',r.read())
   finally:server.shutdown();server.server_close();thread.join()
 def test_linked_ancestor_rejected_before_leaf_metadata(self):
  from terminan.runtime_v2 import runtime_snapshot
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);target=root/'actual';target.mkdir();(target/'runtime.json').write_text(json.dumps(fixture()));link=root/'linked'
   try:link.symlink_to(target,target_is_directory=True)
   except OSError:return
   leaf=link/'runtime.json';seen=[];original=Path.lstat
   def observe(path,*a,**kw):seen.append(path);return original(path,*a,**kw)
   with patch.dict(os.environ,{'TERMINAN_RUNTIME_V2_SNAPSHOT':str(leaf)}),patch.object(Path,'lstat',observe):
    self.assertEqual(runtime_snapshot()['state'],'UNAVAILABLE')
   self.assertNotIn(leaf,seen,'must reject linked parent before inspecting its child')

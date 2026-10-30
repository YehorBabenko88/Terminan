import json,os,tempfile,unittest
from unittest.mock import patch
from terminan.infrastructure import infrastructure_snapshot,validate,STAGES

def fixture(n=0):
 return dict(schema='unified.lifecycle.v1',api_version={'major':1,'minor':0},producer='unified-system',mode='PLAN_ONLY',epoch='00000000-0000-0000-0000-000000000001',sequence=0,execution_authorized=False,trading_authorized=False,stages=[dict(stage=s,status='NOT_STARTED',completed=0,total=0) for s in STAGES],fleet={'nodes':[{'id':str(i),'cpu':None} for i in range(n)],'links':[]})
class Infrastructure(unittest.TestCase):
 def test_dynamic_fleet_and_module_absence(self):
  for n in (0,1,5,6,7):
   for modules in range(6):
    f=fixture(n);f['available_modules']=['unified-system','terminan','strattester','grid','math'][:modules]
    self.assertEqual(len(validate(f)['nodes']),n)
 def test_invalid_authority_sequence_duplicates(self):
  for delta in ({'execution_authorized':True},{'sequence':-1},{'epoch':'bad'},{'stages':[{'stage':'INFRA_READY','status':'RUNNING','completed':2,'total':1}]}):
   with self.assertRaises((ValueError,TypeError)):validate({**fixture(),**delta})
 def test_reader_fail_closed(self):
  with patch.dict(os.environ,{'TERMINAN_LIFECYCLE_SNAPSHOT':'missing-file'}):self.assertEqual(infrastructure_snapshot()['state'],'UNAVAILABLE')
  with tempfile.NamedTemporaryFile(mode='w',delete=False) as f:json.dump(fixture(6),f);name=f.name
  try:
   with patch.dict(os.environ,{'TERMINAN_LIFECYCLE_SNAPSHOT':name}):self.assertEqual(len(infrastructure_snapshot()['nodes']),6)
  finally:os.unlink(name)
if __name__=='__main__':unittest.main()

class HttpInfrastructure(unittest.TestCase):
 def test_read_only_http_route(self):
  import threading
  from urllib.request import urlopen
  from terminan.server import Handler,ThreadingHTTPServer
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   with patch.dict(os.environ,{'TERMINAN_LIFECYCLE_SNAPSHOT':'missing-fixture'}):
    with urlopen('http://127.0.0.1:'+str(server.server_port)+'/api/infrastructure') as response:self.assertEqual(json.load(response)['state'],'UNAVAILABLE')
    with urlopen('http://127.0.0.1:'+str(server.server_port)+'/infrastructure') as response:self.assertIn(b'Read-only infrastructure',response.read())
  finally:server.shutdown();server.server_close();thread.join()

class AdversarialInfrastructure(unittest.TestCase):
 def test_version_exact_and_stage_order(self):
  for version in (None,{'major':True,'minor':0},{'major':1.0,'minor':0},{'major':1,'minor':1}):
   f=fixture();f['api_version']=version
   with self.assertRaises(ValueError):validate(f)
  for stages in ([],list(reversed(fixture()['stages'])),[fixture()['stages'][0]]*7):
   f=fixture();f['stages']=stages
   with self.assertRaises(ValueError):validate(f)
 def test_claimed_verified_edge_never_becomes_topology(self):
  f=fixture(2);f['fleet']['links']=[{'source':'0','target':'1','verified':True}]
  self.assertEqual(validate(f)['links'],[])
  self.assertEqual(validate(f)['link_status'],'UNVERIFIED')
 def test_local_regular_bounded_and_deep_json(self):
  import tempfile
  with tempfile.TemporaryDirectory() as folder:
   p=os.path.join(folder,'nested.json')
   with open(p,'w') as stream:stream.write('['*2000+'0'+']'*2000)
   for path in (p,folder,r'\\server\share\file',r'\\.\pipe\test'):
    with patch.dict(os.environ,{'TERMINAN_LIFECYCLE_SNAPSHOT':path}):self.assertEqual(infrastructure_snapshot()['state'],'UNAVAILABLE')

class NestedBoundary(unittest.TestCase):
 def test_unqualified_nested_claims_rejected(self):
  for key,value in [('identity_verified',True),('execution_authorized',True),('db_sizes',{'main':123}),('cpu',12),('memory',float('nan')),('telemetry',{'verified':True})]:
   f=fixture(1);f['fleet']['nodes'][0][key]=value
   with self.subTest(key=key),self.assertRaises(ValueError):validate(f)
 def test_fleet_claims_rejected(self):
  for key,value in [('execution_authorized',True),('databases',[{'bytes':123}]),('source_provenance','VERIFIED')]:
   f=fixture();f['fleet'][key]=value
   with self.subTest(key=key),self.assertRaises(ValueError):validate(f)
 def test_missing_metrics_project_unavailable_identity_unattested(self):
  n=validate(fixture(1))['nodes'][0]
  self.assertIsNone(n['db_sizes']);self.assertIs(n['identity_verified'],False)

class ProducerV1Boundary(unittest.TestCase):
 def full(self):
  f=fixture();f['fleet']=dict(mode='PLAN_ONLY',status='PLAN_ONLY',execution_authorized=False,links=[],databases=[],alerts=[],source_provenance='NOT_EVALUATED',physical='NOT_RUN',production='NO_GO',nodes=[dict(id='owned-source-fixture',epoch=1,sequence=0,state='ACTIVE',zone='fixture-zone',modules=[],last_heartbeat_ms=None,cpu=None,memory=None,disk=None,available_resources={'cpu':4,'memory':8,'disk':16},db_sizes=None,identity_verified=False)])
  return f
 def test_exact_producer_projection_preserves_capacity_not_utilization(self):
  f=self.full();n=validate(f)['nodes'][0]
  self.assertEqual(n['available_resources'],{'cpu':4,'memory':8,'disk':16});self.assertIsNone(n['cpu']);self.assertEqual(n['observation_status'],'UNATTESTED')
 def test_each_producer_nested_claim_and_bounds_fail_closed(self):
  for key,bad in [('cpu',0.5),('db_sizes',123),('identity_verified',True),('modules',['grid']),('sequence',True),('last_heartbeat_ms',-1),('available_resources',{'cpu':float('inf'),'memory':1,'disk':1}),('available_resources',{'cpu':True,'memory':1,'disk':1}),('execution_authorized',True)]:
   f=self.full();f['fleet']['nodes'][0][key]=bad
   with self.subTest(key=key),self.assertRaises(ValueError):validate(f)
 def test_unknown_nested_stage_module_and_top_level_fields(self):
  for mutate in (lambda f:f.update(extra={'execution_authorized':True}),lambda f:f['stages'][0].update(identity_verified=True),lambda f:f.update(math={'status':'RUNNING','reason':'x','execution_authorized':True})):
   f=fixture();mutate(f)
   with self.assertRaises(ValueError):validate(f)

class HugeIntegerReaderBoundary(unittest.TestCase):
 def test_huge_capacity_integer_reader_returns_unavailable(self):
  f=ProducerV1Boundary().full();f['fleet']['nodes'][0]['available_resources']['cpu']=10**400
  with tempfile.NamedTemporaryFile(mode='w',delete=False) as stream:json.dump(f,stream);name=stream.name
  try:
   with patch.dict(os.environ,{'TERMINAN_LIFECYCLE_SNAPSHOT':name}):
    self.assertEqual(infrastructure_snapshot()['state'],'UNAVAILABLE')
  finally:os.unlink(name)
 def test_huge_capacity_integer_actual_http_is_unavailable(self):
  import threading
  from urllib.request import urlopen
  from terminan.server import Handler,ThreadingHTTPServer
  f=ProducerV1Boundary().full();f['fleet']['nodes'][0]['available_resources']['cpu']=10**400
  with tempfile.NamedTemporaryFile(mode='w',delete=False) as stream:json.dump(f,stream);name=stream.name
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   with patch.dict(os.environ,{'TERMINAN_LIFECYCLE_SNAPSHOT':name}):
    with urlopen('http://127.0.0.1:'+str(server.server_port)+'/api/infrastructure') as response:
     result=json.load(response);self.assertEqual(result['state'],'UNAVAILABLE');self.assertIs(result['execution_authorized'],False);self.assertEqual(result['nodes'],[])
  finally:server.shutdown();server.server_close();thread.join();os.unlink(name)

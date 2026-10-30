import json,os,tempfile,unittest
from unittest.mock import patch
from terminan.infrastructure import infrastructure_snapshot,validate

def fixture(n=0):
 return dict(schema='unified.lifecycle.v1',producer='unified-system',mode='PLAN_ONLY',epoch='00000000-0000-0000-0000-000000000001',sequence=0,execution_authorized=False,trading_authorized=False,stages=[],fleet={'nodes':[{'id':str(i),'cpu':None} for i in range(n)],'links':[]})
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

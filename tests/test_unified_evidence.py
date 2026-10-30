import copy,unittest
from terminan.unified_evidence import validate_browser
class BrowserGate(unittest.TestCase):
 def fixture(self):
  return dict(metadata=dict(invocation='a'*32,source_sha='b'*40,tree='c'*40),errors=[],stats=dict(expected=3,unexpected=0,skipped=0,flaky=0),suites=[dict(specs=[dict(title='six workspaces preserve chart state and fail closed without engines',tests=[dict(projectName='chromium-dpr'+str(d),expectedStatus='passed',status='expected',results=[dict(status='passed',errors=[])]) for d in (1,1.5,2)])])])
 def test_complete(self):self.assertEqual(validate_browser(self.fixture(),'b'*40,'c'*40,'a'*32),3)
 def test_partial_interrupted_stale_and_false_zero(self):
  for mode in ('missing','skip','interrupt','stale','wrong_sha','wrong_tree','duplicate','error','flaky','empty'):
   p=self.fixture()
   if mode=='missing':p['suites'][0]['specs'][0]['tests'].pop()
   if mode=='skip':p['stats']['skipped']=1
   if mode=='interrupt':p['suites'][0]['specs'][0]['tests'][1]['results'][0]['status']='interrupted'
   if mode=='stale':p['metadata']['invocation']='0'*32
   if mode=='wrong_sha':p['metadata']['source_sha']='0'*40
   if mode=='wrong_tree':p['metadata']['tree']='0'*40
   if mode=='duplicate':p['suites'][0]['specs'][0]['tests'][1]['projectName']='chromium-dpr1'
   if mode=='error':p['errors']=[{}]
   if mode=='flaky':p['suites'][0]['specs'][0]['tests'][0]['results']*=2
   if mode=='empty':p={}
   with self.subTest(mode=mode),self.assertRaises(ValueError):validate_browser(p,'b'*40,'c'*40,'a'*32)
if __name__=='__main__':unittest.main()

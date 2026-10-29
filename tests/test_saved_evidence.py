import copy,unittest
from terminan.saved_evidence import check_report

class SavedEvidenceTests(unittest.TestCase):
 def test_fail_closed_report(self):
  projects=['chromium-dpr1','chromium-dpr1.5','chromium-dpr2'];sha='a'*40;inv='b'*32
  raw=dict(config=dict(metadata=dict(invocation=inv,source_sha=sha)),errors=[],stats=dict(expected=3,skipped=0,unexpected=0,flaky=0),suites=[dict(specs=[dict(title='saved history controls identity clusters research and cancellation',file='saved.spec.cjs',ok=True,tests=[dict(projectName=n,projectId=n,expectedStatus='passed',status='expected',results=[dict(status='passed',retry=0,errors=[],attachments=[])]) for n in projects])])])
  raw['config']['metadata']['started_ms']=1767225600000;raw['stats']['startTime']='2026-01-01T00:00:01Z'
  self.assertEqual(len(check_report(raw,sha,inv,projects)),3)
  hosted=copy.deepcopy(raw);hosted['config']['metadata']['ci']={'commitHash':'c'*40,'buildHref':'https://github.com/example/actions/runs/1'}
  self.assertEqual(len(check_report(hosted,sha,inv,projects)),3)
  for fault in ('missing','skip','interrupt','false-zero','stale','identity','retry'):
   x=copy.deepcopy(raw)
   if fault=='missing':x.pop('stats')
   if fault=='skip':x['stats'].update(expected=1,skipped=2)
   if fault=='interrupt':x['suites'][0]['specs'][0]['tests'][1]['results'][0]['status']='interrupted'
   if fault=='false-zero':x['stats']['expected']=True
   if fault=='stale':x['config']['metadata']['invocation']='c'*32
   if fault=='identity':x['suites'][0]['specs'][0]['tests'][1]['projectName']='chromium-dpr1'
   if fault=='retry':x['suites'][0]['specs'][0]['tests'][1]['results'][0]['retry']=1
   with self.subTest(fault=fault),self.assertRaises(ValueError):check_report(x,sha,inv,projects)

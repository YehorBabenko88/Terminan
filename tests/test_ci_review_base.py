import json,os,subprocess,sys,unittest
from pathlib import Path

class ReviewBaseTests(unittest.TestCase):
 def test_exact_authorized_stack_and_legacy_default(self):
  from scripts.ci_review_base import select_policy,LEGACY_BASE,STACK_BASE,STACK_HEAD,STACK_REF
  self.assertEqual(select_policy('pull_request',STACK_HEAD,STACK_REF,STACK_BASE)['policy'],'MISSION3_STACK_EXACT_7F')
  self.assertEqual(select_policy('pull_request','legacy-feature','main',LEGACY_BASE)['policy'],'LEGACY_EXACT_C08')
  for head,base,sha in ((STACK_HEAD,STACK_REF,'f'*40),(STACK_HEAD,'main',STACK_BASE),('other',STACK_REF,STACK_BASE),(STACK_HEAD,STACK_REF,LEGACY_BASE),('other','main','f'*40)):
   with self.subTest(head=head,base=base,sha=sha),self.assertRaises(ValueError):select_policy('pull_request',head,base,sha)
 def test_push_keeps_no_pr_gate_and_unknown_events_fail_closed(self):
  from scripts.ci_review_base import select_policy
  self.assertEqual(select_policy('push','','','')['policy'],'NON_PR_NO_BASE')
  for event in ('pull_request_target','unknown'):
   with self.assertRaises(ValueError):select_policy(event,'','','')
 def test_real_script_records_selected_policy_and_returns_nonzero_on_drift(self):
  from scripts.ci_review_base import STACK_BASE,STACK_HEAD,STACK_REF
  script=Path(__file__).resolve().parents[1]/'scripts/ci_review_base.py'
  env=dict(os.environ,GITHUB_EVENT_NAME='pull_request',GITHUB_HEAD_REF=STACK_HEAD,GITHUB_BASE_REF=STACK_REF,TERMINAN_REVIEW_BASE_SHA=STACK_BASE)
  result=subprocess.run([sys.executable,str(script)],env=env,capture_output=True,text=True,timeout=5)
  self.assertEqual(result.returncode,0,result.stderr);body=json.loads(result.stdout)
  self.assertEqual(body['base_sha'],STACK_BASE);self.assertEqual(body['base_ref'],STACK_REF);self.assertEqual(body['schema'],'terminan.review-base-policy.v1')
  result=subprocess.run([sys.executable,str(script)],env=dict(env,TERMINAN_REVIEW_BASE_SHA='f'*40),capture_output=True,text=True,timeout=5)
  self.assertNotEqual(result.returncode,0);self.assertEqual(result.stdout,'')

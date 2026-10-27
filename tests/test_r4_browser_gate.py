"""Deterministic browser report integrity regressions; metrics stay at existing budgets."""
import copy,json,os,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from test_r4_evidence import valid,SHA
from terminan.r4_evidence import bundle,verify
NONCE='a'*32
PROJECTS=['chromium-dpr1','chromium-dpr1.5','chromium-dpr2']
TITLE='R4 bounded workloads contracts and session lifecycle'
def report():
    return dict(config=dict(metadata=dict(r4_invocation=NONCE,r4_source_sha=SHA)),errors=[],stats=dict(expected=3,skipped=0,unexpected=0,flaky=0),suites=[dict(file='r4.spec.cjs',specs=[dict(title=TITLE,file='r4.spec.cjs',ok=True,tests=[dict(projectName=p,projectId=p,status='expected',expectedStatus='passed',results=[dict(status='passed',retry=0,errors=[])]) for p in PROJECTS])])])
class BrowserGateTests(unittest.TestCase):
    def fixture(self,root,raw):
        repo=Path(__file__).resolve().parents[1]
        shutil.copyfile(repo/'contracts.lock.json',root/'contracts.lock.json')
        (root/'terminan/fixtures').mkdir(parents=True)
        shutil.copyfile(repo/'terminan/fixtures/r4-negative-v1.json',root/'terminan/fixtures/r4-negative-v1.json')
        for p in PROJECTS:
            folder=root/'r4-test-results'/p;folder.mkdir(parents=True)
            data=valid();data.update(project=p,invocation=NONCE,run_id='LOCAL',attempt='1')
            (folder/'r4-performance.json').write_text(json.dumps(data))
            (folder/'r4-preview.png').write_bytes(b'\x89PNG\r\n\x1a\nsynthetic-fixture')
        (root/'report.json').write_text(json.dumps(raw))
    def run_bundle(self,raw,mutate=None):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);self.fixture(root,raw)
            if mutate:mutate(root)
            old=Path.cwd()
            try:
                os.chdir(root)
                with patch.dict(os.environ,dict(R4_INVOCATION=NONCE,GITHUB_RUN_ID='LOCAL',GITHUB_RUN_ATTEMPT='1')):
                    return bundle(Path('report.json'),Path('out'),SHA,'chromium')
            finally:os.chdir(old)
    def test_complete_report_pass(self):self.assertEqual(self.run_bundle(report()),0)
    def test_inconsistent_stats_fail_even_with_pass_results(self):
        for key,value in [('expected',1),('skipped',2),('unexpected',1),('flaky',1),('expected',True)]:
            raw=report();raw['stats'][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):self.run_bundle(raw)
    def test_missing_stats_fail(self):
        raw=report();del raw['stats']
        with self.assertRaises(ValueError):self.run_bundle(raw)
    def test_interrupted_cancelled_partial(self):
        for status in ('interrupted','skipped','timedOut','failed'):
            raw=report();raw['suites'][0]['specs'][0]['tests'][1]['results'][0]['status']=status
            with self.subTest(status=status),self.assertRaises(ValueError):self.run_bundle(raw)
        raw=report();raw['suites'][0]['specs'][0]['tests'].pop()
        with self.assertRaises(ValueError):self.run_bundle(raw)
    def test_stale_source_or_invocation(self):
        for key,value in [('r4_invocation','b'*32),('r4_source_sha','b'*40)]:
            raw=report();raw['config']['metadata'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.run_bundle(raw)
    def test_wrong_test_identity_and_expected_failure(self):
        for field,value in [('title','some other test'),('file','other.spec.cjs'),('ok',False)]:
            raw=report();raw['suites'][0]['specs'][0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):self.run_bundle(raw)
        raw=report();raw['suites'][0]['specs'][0]['tests'][0]['expectedStatus']='failed'
        with self.assertRaises(ValueError):self.run_bundle(raw)
    def test_missing_report_or_artifact(self):
        for target in ('report.json','r4-test-results/chromium-dpr2/r4-performance.json','r4-test-results/chromium-dpr2/r4-preview.png'):
            with self.subTest(target=target),self.assertRaises((ValueError,OSError)):self.run_bundle(report(),lambda root:(root/target).unlink())
    def test_malformed_report(self):
        for value in ([],{},None):
            with self.subTest(value=value),self.assertRaises((ValueError,KeyError,TypeError)):self.run_bundle(value)


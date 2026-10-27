"""Deterministic browser report integrity regressions; metrics stay at existing budgets."""
import copy,json,os,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from test_r3_evidence import valid,SHA
from terminan.r3_evidence import bundle,verify
NONCE='a'*32
PROJECTS=['chromium-dpr1','chromium-dpr1.5','chromium-dpr2']
TITLE='R3 bounded 10k 100k renderer workloads and cancellation'
def report():
    return dict(config=dict(metadata=dict(r3_invocation=NONCE,r3_source_sha=SHA)),errors=[],stats=dict(expected=3,skipped=0,unexpected=0,flaky=0),suites=[dict(file='r3.spec.cjs',specs=[dict(title=TITLE,file='r3.spec.cjs',ok=True,tests=[dict(projectName=p,projectId=p,status='expected',expectedStatus='passed',results=[dict(status='passed',retry=0,errors=[])]) for p in PROJECTS])])])
class BrowserGateTests(unittest.TestCase):
    def fixture(self,root,raw):
        repo=Path(__file__).resolve().parents[1]
        shutil.copyfile(repo/'contracts.lock.json',root/'contracts.lock.json')
        (root/'terminan/fixtures').mkdir(parents=True)
        shutil.copyfile(repo/'terminan/fixtures/r3-negative-v1.json',root/'terminan/fixtures/r3-negative-v1.json')
        for p in PROJECTS:
            folder=root/'r3-test-results'/p;folder.mkdir(parents=True)
            data=valid();data.update(project=p,invocation=NONCE,run_id='LOCAL',attempt='1')
            (folder/'r3-performance.json').write_text(json.dumps(data))
            (folder/'r3-preview.png').write_bytes(b'\x89PNG\r\n\x1a\nsynthetic-fixture')
        (root/'report.json').write_text(json.dumps(raw))
    def run_bundle(self,raw,mutate=None):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);self.fixture(root,raw)
            if mutate:mutate(root)
            old=Path.cwd()
            try:
                os.chdir(root)
                with patch.dict(os.environ,dict(R3_INVOCATION=NONCE,GITHUB_RUN_ID='LOCAL',GITHUB_RUN_ATTEMPT='1')):
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
        for key,value in [('r3_invocation','b'*32),('r3_source_sha','b'*40)]:
            raw=report();raw['config']['metadata'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.run_bundle(raw)
    def test_wrong_test_identity_and_expected_failure(self):
        for field,value in [('title','some other test'),('file','other.spec.cjs'),('ok',False)]:
            raw=report();raw['suites'][0]['specs'][0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):self.run_bundle(raw)
        raw=report();raw['suites'][0]['specs'][0]['tests'][0]['expectedStatus']='failed'
        with self.assertRaises(ValueError):self.run_bundle(raw)
    def test_missing_report_or_artifact(self):
        for target in ('report.json','r3-test-results/chromium-dpr2/r3-performance.json','r3-test-results/chromium-dpr2/r3-preview.png'):
            with self.subTest(target=target),self.assertRaises((ValueError,OSError)):self.run_bundle(report(),lambda root:(root/target).unlink())
    def test_malformed_report(self):
        for value in ([],{},None):
            with self.subTest(value=value),self.assertRaises((ValueError,KeyError,TypeError)):self.run_bundle(value)

class AggregateGateTests(unittest.TestCase):
    def make(self,root):
        from terminan import r3_gate as gate
        from terminan.r2_harness import Harness
        from test_harness_failclosed import FakeRuntime
        with patch.object(gate,'source'):
            gate.begin(root,SHA,NONCE)
        h=Harness(expected_sha=SHA,evidence_root=root/'lifecycle',runtime=FakeRuntime())
        self.assertEqual(h.run(),0)
        BrowserGateTests().fixture(root,report())
        old=Path.cwd()
        try:
            os.chdir(root)
            with patch.dict(os.environ,dict(R3_INVOCATION=NONCE,GITHUB_RUN_ID='LOCAL',GITHUB_RUN_ATTEMPT='1')):
                bundle(Path('report.json'),Path('browser'),SHA,'chromium')
        finally:os.chdir(old)
        # Inputs/workspace are not part of published aggregate.
        for p in ('contracts.lock.json','report.json'): (root/p).unlink()
        shutil.rmtree(root/'terminan');shutil.rmtree(root/'r3-test-results')
        return gate
    def test_complete_aggregate_and_tampering(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'run';gate=self.make(root)
            with patch.object(gate,'source'):gate.complete(root,SHA,NONCE)
            self.assertEqual(gate.verify(root,SHA,NONCE),0)
            for wrong in ('b'*32,''):
                with self.assertRaises(ValueError):gate.verify(root,SHA,wrong)
            (root/'browser/tests.json').write_text('[]')
            with self.assertRaises(ValueError):gate.verify(root,SHA,NONCE)
    def test_lifecycle_only_and_incomplete_never_pass(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'run';gate=self.make(root)
            with self.assertRaises((ValueError,OSError)):gate.verify(root,SHA,NONCE)
            shutil.rmtree(root/'browser')
            with patch.object(gate,'source'),self.assertRaises((ValueError,OSError)):gate.complete(root,SHA,NONCE)
            self.assertEqual(json.loads((root/'summary.json').read_text())['exit_code'],50)
    def test_atomic_browser_publication(self):
        from terminan import r3_evidence
        original=r3_evidence.verify;seen=[]
        def observe(root,sha):
            seen.append(root.name)
            self.assertTrue(root.name.startswith('.pending-'))
            self.assertFalse(root.with_name('out').exists())
            return original(root,sha)
        with patch.object(r3_evidence,'verify',side_effect=observe):
            self.assertEqual(BrowserGateTests().run_bundle(report()),0)
        self.assertEqual(len(seen),1)

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import parse_qs,urlsplit
from terminan.r2_harness import Harness, Runtime, inspect_run
from terminan.synthetic import frame
from terminan.synthetic_contracts import fixtures,validate_fixture

SHA='a'*40
SECRET='PRIVATE_PATH_DSN_RAW_EXCEPTION'

class Child:
    def __init__(self,fault):
        self.fault=fault;self.returncode=None;self.stdout_bytes=100;self.stderr_bytes=0;self.output_limit=False;self.killed=False
    def poll(self):return self.returncode
    def quit(self,timeout):
        if self.fault=='shutdown_timeout':raise TimeoutError(SECRET)
        self.returncode=0
        return 0
    def kill(self):self.killed=True;self.returncode=-9
    def close(self):pass

class FakeRuntime(Runtime):
    def __init__(self,fault=None):self.fault=fault;self.now=0;self.child=Child(fault)
    def identity(self,repo):return SHA,True
    def spawn(self,repo,ready):
        self.write_json(ready,dict(host='127.0.0.1',port=12345,mode='SYNTHETIC',sources='DISABLED',candidate_sha=SHA,source_clean=True))
        return self.child
    def clock(self):return self.now
    def sleep(self,seconds):
        if self.fault=='review_wait':raise RuntimeError(SECRET)
        self.now+=seconds
    def browser(self,url):
        if self.fault=='browser_launch':raise OSError(SECRET)
        if self.fault=='early_child':self.child.returncode=0
    def fetch(self,url):
        parsed=urlsplit(url);query={k:v[0] for k,v in parse_qs(parsed.query).items()}
        if parsed.path=='/api/status':
            value=dict(mode='SYNTHETIC',sources='DISABLED',execution='DISABLED',candidate_sha=SHA,source_clean=True)
        elif parsed.path.endswith('/frame'):
            value=frame(step=int(query['step']),scenario=query['scenario']);value['candidate_sha']=SHA
            if self.fault=='assertion':value['mode']='LIVE'
        elif parsed.path.endswith('/contracts'):
            views=[]
            for raw in fixtures():
                raw['rows'][0]['available_at_ms']=raw['observed_at_ms']+1
                views.append(validate_fixture(raw,raw['observed_at_ms']))
            value=dict(mode='SYNTHETIC',candidate_sha=SHA,sources=views)
        else:return 200,b'SYNTHETIC R2 ASSET'
        return 200,json.dumps(value,allow_nan=False).encode()
    def write_json(self,path,value):
        if self.fault=='finalize' and path.name=='manifest.json':raise OSError(SECRET)
        super().write_json(path,value)

class FailClosedHarness(unittest.TestCase):
    def run_case(self,fault=None,sha=SHA,seconds=0,browser=True):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        runtime=FakeRuntime(fault)
        harness=Harness(expected_sha=sha,evidence_root=Path(temp.name),review_seconds=str(seconds),open_browser=browser,runtime=runtime)
        code=harness.run()
        final=harness.final_dir
        summary=json.loads((final/'summary.json').read_text()) if (final/'summary.json').exists() else None
        return code,summary,final,runtime
    def test_success_and_monotonic_600_second_review(self):
        code,s,path,rt=self.run_case(seconds=600)
        self.assertEqual(code,0);self.assertEqual(s['failure_stage'],'NONE');self.assertEqual(s['error_class'],'NONE')
        self.assertTrue(s['review_completed']);self.assertGreaterEqual(s['review_elapsed_seconds'],600)
        self.assertEqual(inspect_run(path,SHA),0)
        self.assertIsInstance(json.loads((path/'manifest.json').read_text()),list)
    def test_browser_failure_after_nine_successful_routes(self):
        code,s,path,rt=self.run_case('browser_launch')
        self.assertEqual((code,s['failure_stage'],s['error_class']),(31,'browser_launch','BROWSER_LAUNCH_FAILED'))
        smoke=json.loads((path/'smoke.json').read_text());self.assertEqual(len(smoke),9)
        self.assertTrue(all(r['status']==200 for r in smoke));self.assertEqual(inspect_run(path,SHA),31)
        self.assertNotIn(SECRET,(path/'summary.json').read_text())
    def test_early_zero_child_exit_is_not_success(self):
        code,s,path,rt=self.run_case('early_child',seconds=15)
        self.assertEqual((code,s['failure_stage'],s['error_class']),(33,'child_health','CHILD_EARLY_EXIT'))
        self.assertEqual(s['child_exit_code'],0);self.assertEqual(s['result'],'FAIL')
    def test_review_wait_failure_is_distinct(self):
        code,s,path,rt=self.run_case('review_wait',seconds=15)
        self.assertEqual((code,s['failure_stage']),(32,'review_wait'))
    def test_shutdown_timeout_kills_only_owned_child(self):
        code,s,path,rt=self.run_case('shutdown_timeout')
        self.assertEqual((code,s['failure_stage'],s['error_class']),(40,'graceful_shutdown','SHUTDOWN_TIMEOUT'))
        self.assertTrue(rt.child.killed);self.assertEqual(inspect_run(path,SHA),40)
    def test_assertions_remain_fail_closed(self):
        code,s,path,rt=self.run_case('assertion')
        self.assertEqual(code,30);self.assertEqual(s['failure_stage'],'smoke')
    def test_invalid_sha_has_single_entry_array_manifest_and_no_raw_input(self):
        code,s,path,rt=self.run_case(sha=SECRET)
        self.assertEqual(code,10);self.assertEqual(s['error_class'],'INVALID_SHA')
        entries=json.loads((path/'manifest.json').read_text())
        self.assertIsInstance(entries,list);self.assertEqual(len(entries),1)
        self.assertNotIn(SECRET,(path/'summary.json').read_text())
    def test_wrong_sha_is_preflight_failure(self):
        code,s,path,rt=self.run_case(sha='b'*40)
        self.assertEqual(code,10);self.assertEqual(s['error_class'],'SHA_MISMATCH')
    def test_missing_or_tampered_evidence_never_passes(self):
        code,s,path,rt=self.run_case()
        (path/'smoke.json').unlink()
        self.assertEqual(inspect_run(path,SHA),50)
    def test_finalization_failure_cannot_publish_pass(self):
        code,s,path,rt=self.run_case('finalize')
        self.assertEqual(code,50);self.assertIsNone(s);self.assertFalse(path.exists())

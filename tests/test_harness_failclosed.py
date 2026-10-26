import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
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
        if self.fault in ('shutdown_timeout','browser_and_shutdown'):raise TimeoutError(SECRET)
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
        if self.fault in ('browser_launch','browser_and_shutdown'):raise OSError(SECRET)
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
            if self.fault=='empty_contracts':views=[]
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
    def test_cleanup_failure_preserves_primary_stage(self):
        code,s,path,rt=self.run_case('browser_and_shutdown')
        self.assertEqual(code,31);self.assertEqual(s['failure_stage'],'browser_launch')
        self.assertTrue(any(v['exit_code']==40 for v in s['secondary_failures']))
        self.assertTrue(rt.child.killed)
    def test_empty_future_contracts_are_not_vacuously_successful(self):
        code,s,path,rt=self.run_case('empty_contracts')
        self.assertEqual(code,30);self.assertEqual(s['error_class'],'SMOKE_ASSERTION_FAILED')
    def test_late_publish_failure_commits_only_failure(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        rt=FakeRuntime();publish=rt.publish
        def once(pending,final):
            if not hasattr(rt,'failed'):
                rt.failed=True;raise OSError(SECRET)
            publish(pending,final)
        rt.publish=once
        h=Harness(expected_sha=SHA,evidence_root=temp.name,runtime=rt)
        self.assertEqual(h.run(),50)
        summary=json.loads((h.final_dir/'summary.json').read_text())
        self.assertEqual((summary['result'],summary['failure_stage']),('FAIL','evidence_finalize'))
        self.assertEqual(inspect_run(h.final_dir,SHA),50)
    def test_existing_pending_evidence_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            h=Harness(expected_sha=SHA,evidence_root=temp,runtime=FakeRuntime())
            h.pending.mkdir();original=h.pending/'summary.json';original.write_text('ORIGINAL EVIDENCE')
            self.assertEqual(h.run(),50)
            self.assertEqual(original.read_text(),'ORIGINAL EVIDENCE')
            self.assertFalse(h.final_dir.exists())
    def test_cancellation_during_cleanup_still_stops_owned_child(self):
        with tempfile.TemporaryDirectory() as temp:
            rt=FakeRuntime('browser_launch')
            def interrupted(timeout):raise KeyboardInterrupt()
            rt.child.quit=interrupted
            h=Harness(expected_sha=SHA,evidence_root=temp,runtime=rt,open_browser=True)
            self.assertEqual(h.run(),31)
            self.assertTrue(rt.child.killed);self.assertIsNotNone(rt.child.poll())
    def test_redirected_evidence_root_is_rejected_without_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);h=Harness(expected_sha=SHA,evidence_root=root,runtime=FakeRuntime())
            real_stat=__import__('os').lstat
            def redirected(path,*args,**kwargs):
                if Path(path)==root:
                    from types import SimpleNamespace
                    import stat
                    return SimpleNamespace(st_mode=stat.S_IFDIR,st_file_attributes=0x400)
                return real_stat(path,*args,**kwargs)
            with patch('os.lstat',side_effect=redirected):
                self.assertEqual(h.run(),50)
            self.assertEqual(list(root.iterdir()),[])
    def test_unknown_harness_evidence_version_is_rejected(self):
        from terminan.r2_evidence import verify
        code,summary,path,rt=self.run_case()
        summary['harness_contract_version']=99
        body=json.dumps(summary).encode();(path/'summary.json').write_bytes(body)
        entries=json.loads((path/'manifest.json').read_text())
        for entry in entries:
            if entry['file']=='summary.json':entry.update(bytes=len(body),sha256=hashlib.sha256(body).hexdigest())
        (path/'manifest.json').write_text(json.dumps(entries))
        with self.assertRaises(ValueError):verify(path,SHA)

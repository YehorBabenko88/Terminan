import copy,json,tempfile,unittest
from pathlib import Path
from terminan.r3_evidence import check,verify,bundle
SHA='a'*40

def valid():
    results=[]
    for count in (10000,100000):
        checksum=17
        for _ in range(count):checksum=(checksum*1664525+1013904223)&0xffffffff
        results.append(dict(updates=count,seed=17,batch=100,frames=count//100,samples=count//100,checksum=checksum,mode='SYNTHETIC',authority='SYNTHETIC_ONLY',elapsedMs=2000,renderCadenceFps=60,updatesPerSecond=5000,latencyMs=dict(p50=1,p95=2,p99=3),drawMs=dict(p50=1,p95=2,p99=3),frameIntervalMs=dict(p50=16,p95=17,p99=18),metrics=dict(retainedCandles=240,retainedEvents=20,bookRows=40,activeRequests=0)))
    memory=dict(state='AVAILABLE',rss_bytes=10000000,process_count=4)
    return dict(version=1,candidate_sha=SHA,source_clean=True,project='chromium-dpr1',results=results,resources=dict(state='AVAILABLE',cpuDuty=.1,heapBefore=1000,heapAfter=2000,heapGrowthBytes=1000,processMemory=dict(before=memory.copy(),after=memory.copy())),disposed=dict(listeners=0,rafPending=0,activeRequests=0,timerPending=0,retainedCandles=0))
class R3EvidenceTests(unittest.TestCase):
    def test_valid(self):check(valid(),SHA)
    def test_nonfinite_memory_rejected(self):
        for value in (float('nan'),float('inf'),'100',True):
            for field in ('heapGrowthBytes','heapBefore','heapAfter','cpuDuty'):
                data=valid();data['resources'][field]=value
                with self.assertRaises((ValueError,TypeError)):check(data,SHA)
            data=valid();data['resources']['processMemory']['after']['rss_bytes']=value
            with self.assertRaises((ValueError,TypeError)):check(data,SHA)
    def test_missing_and_bad_metrics(self):
        for mutate in ('sha','dirty','checksum','count','latency','memory'):
            data=valid()
            if mutate=='sha':data['candidate_sha']='b'*40
            elif mutate=='dirty':data['source_clean']=False
            elif mutate=='checksum':data['results'][1]['checksum']=0
            elif mutate=='count':data['results'][1]['updates']=99999
            elif mutate=='latency':data['results'][1]['latencyMs']['p99']=100
            else:data['resources']['processMemory']['after']['rss_bytes']=-1
            with self.assertRaises(ValueError):check(data,SHA)
    def test_missing_invalid_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            with self.assertRaises(OSError):verify(root,SHA)
            (root/'manifest.json').write_text('[{"path":"../secret","sha256":"bad"}]')
            with self.assertRaises(ValueError):verify(root,SHA)
    def test_tamper(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'summary.json').write_text('{}');(root/'manifest.json').write_text('[{"path":"summary.json","sha256":"'+'0'*64+'"}]')
            with self.assertRaises(ValueError):verify(root,SHA)

    def test_playwright_metadata_location(self):
        from terminan.r3_evidence import report_invocation
        self.assertEqual(report_invocation({'config':{'metadata':{'r3_invocation':'nonce'}}}),'nonce')
        self.assertIsNone(report_invocation({'metadata':{'r3_invocation':'stale'}}))

    def test_final_verification_failure_never_leaves_pass(self):
        import os,shutil
        from unittest.mock import patch
        repo=Path.cwd();nonce='a'*32
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            shutil.copyfile(repo/'contracts.lock.json',root/'contracts.lock.json')
            (root/'terminan/fixtures').mkdir(parents=True)
            shutil.copyfile(repo/'terminan/fixtures/r3-negative-v1.json',root/'terminan/fixtures/r3-negative-v1.json')
            tests=[]
            for project in ('chromium-dpr1','chromium-dpr1.5','chromium-dpr2'):
                d=valid();d.update(project=project,invocation=nonce,run_id='LOCAL',attempt='1')
                folder=root/'r3-test-results'/project;folder.mkdir(parents=True)
                (folder/'r3-performance.json').write_text(json.dumps(d))
                (folder/'r3-preview.png').write_bytes(b'INVALID PNG')
                tests.append(dict(projectName=project,status='expected',results=[dict(status='passed')]))
            (root/'report.json').write_text(json.dumps(dict(config=dict(metadata=dict(r3_invocation=nonce)),suites=[dict(specs=[dict(tests=tests)])])))
            try:
                os.chdir(root)
                with patch.dict(os.environ,{'R3_INVOCATION':nonce,'GITHUB_RUN_ID':'LOCAL','GITHUB_RUN_ATTEMPT':'1'}):
                    with self.assertRaises(ValueError):bundle(Path('report.json'),Path('out'),SHA,'chromium')
                self.assertEqual(json.loads(Path('out/summary.json').read_text())['result'],'FAIL')
            finally:os.chdir(repo)

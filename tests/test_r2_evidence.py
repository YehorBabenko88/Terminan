import json
from pathlib import Path
import tempfile
import unittest
from terminan.r2_evidence import verify, check_performance, check_report, manifest

class R2Evidence(unittest.TestCase):
    def test_performance_and_runner_errors_are_acceptance_gates(self):
        perf=dict(wallMs=2000,metrics=dict(avgRenderMs=2,p95RenderMs=5,playRateHz=3,idleExtraRenders=0),enginePerformance=dict(available=True,mainThreadCpuMs=200))
        check_performance(perf)
        for field,value in [('avgRenderMs',200),('p95RenderMs',200),('playRateHz',.1),('idleExtraRenders',20)]:
            changed={**perf,'metrics':{**perf['metrics'],field:value}}
            with self.assertRaises(ValueError):check_performance(changed)
        with self.assertRaises(ValueError):check_performance({**perf,'enginePerformance':dict(available=True,mainThreadCpuMs=1900)})
        with self.assertRaises(ValueError):check_report({'errors':[{'message':'runner crashed'}]})
    def test_summary_alone_never_proves_required_assertions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'summary.json').write_text(json.dumps(dict(candidate_sha='a'*40,result='PASS',physical='PENDING',kind='harness')))
            (root/'manifest.json').write_text('[]')
            with self.assertRaises(ValueError):verify(root,'a'*40)

    def test_wrong_sha_and_traversal_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'manifest.json').write_text('[{"file":"../secret","sha256":"bad","bytes":0}]')
            with self.assertRaises(ValueError):verify(root,'a'*40)

class BrowserInventoryTests(unittest.TestCase):
    # The complete default suite must be evidenced; count alone cannot prove identity.
    titles = (
        'zoom pan resize DPR and complete synthetic identity',
        'fault recovery contracts and bounded replay',
        'superseded requests cannot keep another symbol visible',
        'stress frame pipeline memory CPU and lifecycle evidence',
        'partial HTTP failure and in-flight disposal abort all requests',
        'dynamic fleet, every control, unavailable data and selection',
        'aborted stale response cannot overwrite new snapshot',
        'actual A states filter and selected detail follows latest metrics',
        'stalled local refresh becomes explicitly unavailable at deadline',
        'actual Python consumer rejects forged nested observation before Chromium renders',
    )

    def make_bundle(self, root, scope='all'):
        projects = [engine+'-dpr'+str(dpr) for engine in ('chromium','firefox') for dpr in (1,1.5,2)]
        if scope == 'chromium':
            projects = projects[:3]
        tests = [dict(title=title,project=project,status='passed',attempts=1)
                 for project in projects for title in self.titles]
        (root/'summary.json').write_text(json.dumps(dict(kind='browser',candidate_sha='a'*40,
            physical='PENDING',mode='SYNTHETIC',scope=scope,result='PASS')))
        for name in ('contract-pins.json','fixture-v1.json'):
            (root/name).write_text('{}')
        for project in projects:
            folder = root/project
            folder.mkdir()
            (folder/'preview.png').write_bytes(b'\x89PNG\r\n\x1a\n')
            perf = dict(candidate_sha='a'*40,source_clean=True,mode='SYNTHETIC',wallMs=2000,
                metrics=dict(avgRenderMs=2,p95RenderMs=5,playRateHz=3,idleExtraRenders=0,
                    retainedCandles=240,retainedEvents=20,peakRequests=4),
                enginePerformance=dict(available=True,mainThreadCpuMs=200),
                disposed=dict(listeners=0,rafPending=0,timerPending=0,activeRequests=0))
            (folder/'performance.json').write_text(json.dumps(perf))
        return tests

    def save_tests(self, root, tests):
        (root/'tests.json').write_text(json.dumps(tests))
        manifest(root)

    def test_complete_r2_and_infrastructure_inventory_is_accepted(self):
        for scope in ('all','chromium'):
            with self.subTest(scope=scope), tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                self.save_tests(root,self.make_bundle(root,scope))
                verify(root,'a'*40)

    def test_missing_duplicate_substituted_and_nonpassing_assertions_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            baseline=self.make_bundle(root)
            mutations={
                'missing_r2':baseline[1:],
                'missing_infrastructure':baseline[:5]+baseline[6:],
                'missing_consumer_assertion':[t for t in baseline if t['title']!='actual Python consumer rejects forged nested observation before Chromium renders'],
                'duplicate':baseline+[baseline[0]],
                'substituted':[{**baseline[0],'title':'unrelated assertion'}]+baseline[1:],
                'unknown_project':[{**baseline[0],'project':'chromium-dpr3'}]+baseline[1:],
                'failed':[{**baseline[0],'status':'failed'}]+baseline[1:],
                'skipped':[{**baseline[0],'status':'skipped'}]+baseline[1:],
                'retried':[{**baseline[0],'attempts':2}]+baseline[1:],
            }
            for name,tests in mutations.items():
                with self.subTest(mutation=name):
                    self.save_tests(root,tests)
                    with self.assertRaises(ValueError):verify(root,'a'*40)
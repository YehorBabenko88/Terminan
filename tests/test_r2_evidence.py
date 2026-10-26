import json
from pathlib import Path
import tempfile
import unittest
from terminan.r2_evidence import verify, check_performance, check_report

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

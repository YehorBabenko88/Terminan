"""Every full contract-suite workflow provisions immutable sibling source refs."""
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class PinnedWorkflowLayoutTests(unittest.TestCase):
    def test_runtime_and_visual_contract_jobs_provision_source_siblings(self):
        lock=json.loads((ROOT/'contracts.lock.json').read_text())
        for name in ('unified-runtime.yml','visual-qa.yml'):
            text=(ROOT/'.github/workflows'/name).read_text()
            with self.subTest(workflow=name):
                self.assertIn('working-directory: candidate',text)
                self.assertIn('path: candidate',text)
                self.assertIn('path: candidate/reports/',text)
                for source,repo in (('grid','bybit-cluster-grid'),('strattester','strattester')):
                    self.assertIn('repository: YehorBabenko88/'+repo,text)
                    self.assertIn('ref: '+lock[source]['sha'],text)
                    self.assertIn('path: '+source,text)


if __name__=='__main__':unittest.main()

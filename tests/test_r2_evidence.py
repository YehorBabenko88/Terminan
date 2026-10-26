import json
from pathlib import Path
import tempfile
import unittest
from terminan.r2_evidence import verify

class R2Evidence(unittest.TestCase):
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

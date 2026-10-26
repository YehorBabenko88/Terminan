import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from terminan.evidence import verify

class Evidence(unittest.TestCase):
    def test_integrity_and_tamper_and_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            body=json.dumps(dict(candidate_sha='a'*40,exit_code=0,physical='PENDING',result='AUTOMATED_SMOKE_PASS')).encode()
            (root/'summary.json').write_bytes(body)
            entries=[dict(file='summary.json',sha256=hashlib.sha256(body).hexdigest(),bytes=len(body))]
            (root/'manifest.json').write_text(json.dumps(entries))
            verify(root,'a'*40)
            (root/'summary.json').write_bytes(body+b' ')
            with self.assertRaises(ValueError):verify(root,'a'*40)
            entries[0]['file']='../summary.json'
            (root/'manifest.json').write_text(json.dumps(entries))
            with self.assertRaises(ValueError):verify(root,'a'*40)

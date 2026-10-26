import hashlib
import json
import os
from pathlib import Path
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]

class PinnedRepositories(unittest.TestCase):
    def test_exact_upstream_heads_and_contract_files(self):
        lock=json.loads((ROOT/'contracts.lock.json').read_text())
        for name,entry in lock.items():
            repo=Path(os.environ.get(name.upper()+'_REPO',ROOT.parent/name))
            with self.subTest(repository=name):
                sha=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
                self.assertEqual(sha,entry['sha'])
                for path,digest in entry['files'].items():
                    canonical=subprocess.check_output(['git','-C',str(repo),'show',sha+':'+path])
                    self.assertEqual(hashlib.sha256(canonical).hexdigest(),digest)
                    self.assertEqual(subprocess.call(['git','-C',str(repo),'diff','--quiet','HEAD','--',path]),0)

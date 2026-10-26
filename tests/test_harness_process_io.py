from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from terminan.r2_harness import OwnedChild,Fault

class ProcessIO(unittest.TestCase):
    def test_actual_shutdown_timeout_reaps_only_the_owned_process(self):
        process=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        child=OwnedChild(process)
        try:
            with self.assertRaises(Fault) as failure:child.quit(.05)
            self.assertEqual(failure.exception.error_class,'SHUTDOWN_TIMEOUT')
        finally:
            child.kill();self.assertTrue(child.close())
        self.assertIsNotNone(child.poll())
    def test_output_drains_are_bounded_and_never_retain_payload(self):
        process=subprocess.Popen([sys.executable,'-c',"import os; os.write(1,b'x'*100000); os.write(2,b'y'*100000)"],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        child=OwnedChild(process)
        try:process.wait(timeout=5)
        finally:
            if process.poll() is None:child.kill()
            self.assertTrue(child.close())
        self.assertEqual(child.stdout_bytes,100000);self.assertEqual(child.stderr_bytes,100000)
        self.assertTrue(child.output_limit)
    def test_missing_evidence_cli_is_nonzero_and_privacy_safe(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'PRIVATE_PATH_DSN_RAW_EXCEPTION'
            process=subprocess.run([sys.executable,'-m','terminan.r2_evidence','verify',str(path),'--sha','a'*40],capture_output=True,text=True,timeout=5)
            self.assertEqual(process.returncode,50)
            self.assertNotIn('PRIVATE_PATH_DSN_RAW_EXCEPTION',process.stdout+process.stderr)
            self.assertEqual(process.stderr,'')

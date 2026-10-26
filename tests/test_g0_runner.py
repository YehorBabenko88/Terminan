import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.request import urlopen

class Runner(unittest.TestCase):
    def test_owned_port_smoke_and_graceful_stdin_shutdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            ready=Path(tmp)/'ready.json'
            env={k:v for k,v in os.environ.items() if not k.startswith('TERMINAN_')}
            proc=subprocess.Popen([sys.executable,'-m','terminan.g0_runner','--ready',str(ready)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,text=True)
            try:
                deadline=time.monotonic()+8
                while not ready.exists() and proc.poll() is None and time.monotonic()<deadline:time.sleep(.05)
                self.assertTrue(ready.exists(),'runner did not become ready')
                info=json.loads(ready.read_text())
                self.assertEqual(info['host'],'127.0.0.1')
                with urlopen(f"http://127.0.0.1:{info['port']}/api/sources",timeout=3) as res:
                    self.assertEqual(json.load(res)['state'],'NOT_CONFIGURED')
                out,err=proc.communicate('quit\n',timeout=8)
                self.assertEqual(proc.returncode,0,err)
                self.assertEqual(err,'')
            finally:
                if proc.poll() is None:proc.kill()
                proc.communicate()

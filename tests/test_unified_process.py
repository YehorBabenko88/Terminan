import os,socket,subprocess,sys,time,unittest,tempfile
from pathlib import Path
from terminan.unified_process import run_browser
class OwnedBrowser(unittest.TestCase):
 def test_timeout_closes_owned_descendant_listener(self):
  with tempfile.TemporaryDirectory() as td:
   marker=Path(td)/'port.txt'
   code="import socket,time;from pathlib import Path;s=socket.socket();s.bind(('127.0.0.1',0));s.listen();Path("+repr(str(marker))+").write_text(str(s.getsockname()[1]));time.sleep(30)"
   parent="import subprocess,sys,time;subprocess.Popen([sys.executable,'-c',"+repr(code)+"]);time.sleep(30)"
   with self.assertRaises(subprocess.TimeoutExpired):run_browser([sys.executable,'-c',parent],dict(os.environ),timeout=3)
   self.assertTrue(marker.is_file());port=int(marker.read_text());time.sleep(.2)
   with socket.socket() as s:self.assertNotEqual(s.connect_ex(('127.0.0.1',port)),0)
 def test_normal_exit(self):
  p=run_browser([sys.executable,'-c','print("owned")'],dict(os.environ),timeout=5)
  self.assertEqual(p.returncode,0);self.assertEqual(p.stdout.strip(),b'owned')
if __name__=='__main__':unittest.main()


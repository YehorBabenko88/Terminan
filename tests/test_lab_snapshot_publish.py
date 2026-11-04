"""Atomic publisher/reader interoperability, using actual local file handles."""
import os,tempfile,unittest
from pathlib import Path
from terminan import lab_view
from scripts.lab_view_test_server import replace_snapshot

class SnapshotPublicationTests(unittest.TestCase):
 def test_open_reader_permits_atomic_replacement_and_keeps_original_inode(self):
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary);target=root/'snapshot.json';replacement=root/'next.json'
   target.write_bytes(b'{"sequence":1}');replacement.write_bytes(b'{"sequence":2}')
   fd=lab_view._snapshot_fd(target)
   try:
    original=os.fstat(fd);replace_snapshot(replacement,target)
    self.assertEqual(os.read(fd,1024),b'{"sequence":1}')
    self.assertNotEqual((original.st_dev,original.st_ino),(target.stat().st_dev,target.stat().st_ino))
   finally:os.close(fd)
   self.assertEqual(lab_view.read_snapshot(str(target))[0],{'sequence':2})

 def test_fixture_acknowledges_publication_while_actual_reader_is_open(self):
  import json,queue,subprocess,sys,threading
  from urllib.request import urlopen
  source=Path(__file__).resolve().parents[1]
  with tempfile.TemporaryDirectory() as temporary:
   private=Path(temporary)
   env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','PATH','USERPROFILE','APPDATA','LOCALAPPDATA'}}
   env.update(TEMP=str(private),TMP=str(private),PYTHONPATH=str(source))
   child=subprocess.Popen([sys.executable,'-u',str(source/'scripts/lab_view_test_server.py')],env=env,cwd=source,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
   messages=queue.Queue()
   reader=threading.Thread(target=lambda:[messages.put(json.loads(line)) for line in child.stdout],daemon=True);reader.start()
   try:
    hello=messages.get(timeout=10);snapshot=next(private.glob('terminan-lab-synthetic-*/snapshot.json'))
    fd=lab_view._snapshot_fd(snapshot)
    try:
     child.stdin.write('fresh\n');child.stdin.flush()
     self.assertEqual(messages.get(timeout=5),{'fixture':'SYNTHETIC_TEST_INPUT','applied':'fresh'})
     self.assertIsNone(child.poll())
    finally:os.close(fd)
    with urlopen(hello['url']+'/api/lab/overview',timeout=2) as response:self.assertEqual(json.load(response)['state'],'AVAILABLE')
    child.stdin.write('stop\n');child.stdin.flush();child.wait(timeout=5)
    self.assertEqual(child.returncode,0,child.stderr.read())
   finally:
    if child.poll() is None:child.kill();child.wait(timeout=5)
    for stream in (child.stdin,child.stdout,child.stderr):stream.close()
    reader.join(1)

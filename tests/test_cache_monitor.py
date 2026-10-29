import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
from terminan.saved_cache import open_cache
from terminan.cache_queue import init_queue
from terminan.cache_monitor import read_status

class CacheMonitorTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.path=Path(self.tmp.name)/"queue.sqlite"
  self.con=init_queue(open_cache(self.path))
 def tearDown(self):
  self.con.close();self.tmp.cleanup()
 def test_read_only_empty(self):
  result=read_status(self.path)
  self.assertEqual(result["mode"],"READ_ONLY")
  self.assertEqual(result["authority"],"OFFLINE_ONLY")
  self.assertEqual(result["entries"],0)
  self.assertEqual(result["jobs"],[])
 def test_status_does_not_mutate_database(self):
  before=self.con.execute("PRAGMA data_version").fetchone()
  read_status(self.path)
  after=self.con.execute("PRAGMA data_version").fetchone()
  self.assertEqual(before,after)
 def test_missing_db_is_not_created(self):
  missing=Path(self.tmp.name)/"absent.sqlite"
  with self.assertRaises(Exception):
   read_status(missing)
  self.assertFalse(missing.exists())
 def test_status_reads_job(self):
  self.con.execute("""INSERT INTO cache_jobs
   (job_id,cache_key,identity_json,source_json,state,created_at,updated_at)
   VALUES (?,?,?,?,?,?,?)""",("j1","k1","{}","{}","QUEUED",100,100))
  result=read_status(self.path)
  self.assertEqual(result["jobs"][0]["job_id"],"j1")
  self.assertEqual(result["jobs"][0]["state"],"QUEUED")

if __name__=="__main__":unittest.main()

import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
from terminan.saved_cache import open_cache, ALGORITHM
from terminan.cache_queue import init_queue, submit, run_once
from terminan.cache_monitor import read_status, read_job_result, lookup_exact_cache

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

 def test_verified_cache_result(self):
  identity=dict(source="grid",source_revision="a"*64,dataset="candles_1m",
   symbol="BTCUSDT",timeframe="5m",from_ms=1767225600000,to_ms=1767225840000,
   algorithm=ALGORITHM,parameters_hash="b"*64)
  candles=[dict(symbol="BTCUSDT",ts=1767225600000+i*60000,
   open=100+i,high=102+i,low=99+i,close=101+i,buy_volume=2,sell_volume=1) for i in range(5)]
  source=dict(source_revision="a"*64,candles=candles,
   footprint=[dict(symbol="BTCUSDT",ts=c["ts"],price=100,buy_volume=2,sell_volume=1) for c in candles])
  job=submit(self.con,identity,source)
  self.assertEqual(run_once(self.con)["state"],"FINISHED")
  result=read_job_result(self.path,job["job_id"])
  self.assertEqual(result["state"],"READY")
  self.assertEqual(result["total_candles"],1)
  self.assertEqual(result["candles"][0]["volume"],15)
  self.assertNotIn("levels",result["candles"][0])
  self.assertNotIn("source_json",result)
  self.con.execute("UPDATE cache_entries SET payload=?",(b"tampered",))
  self.assertEqual(read_job_result(self.path,job["job_id"])["state"],"CORRUPT")
 def test_exact_cache_lookup_requires_revision_and_bounds(self):
  identity=dict(source="grid",source_revision="a"*64,dataset="candles_1m",
   symbol="BTCUSDT",timeframe="5m",from_ms=1767225600000,to_ms=1767225840000,
   algorithm=ALGORITHM,parameters_hash="b"*64)
  candles=[dict(symbol="BTCUSDT",ts=1767225600000+i*60000,
   open=100+i,high=102+i,low=99+i,close=101+i,buy_volume=2,sell_volume=1) for i in range(5)]
  source=dict(source_revision="a"*64,candles=candles,
   footprint=[dict(symbol="BTCUSDT",ts=c["ts"],price=100,buy_volume=2,sell_volume=1) for c in candles])
  submit(self.con,identity,source)
  self.assertEqual(run_once(self.con)["state"],"FINISHED")
  self.assertEqual(lookup_exact_cache(self.path,"a"*64,"BTCUSDT","5m",1767225600000,1767225840000)["state"],"READY")
  self.assertEqual(lookup_exact_cache(self.path,"c"*64,"BTCUSDT","5m",1767225600000,1767225840000)["state"],"MISS")
  self.assertEqual(lookup_exact_cache(self.path,"a"*64,"BTCUSDT","15m",1767225600000,1767225840000)["state"],"MISS")
  self.assertEqual(lookup_exact_cache(self.path,"a"*64,"BTCUSDT","5m",1767225600000,1767225900000)["state"],"MISS")
 def test_bad_job_id(self):
  with self.assertRaises(ValueError):
   read_job_result(self.path,"../secret")

if __name__=="__main__":unittest.main()

import tempfile
import unittest
from pathlib import Path
from terminan.saved_cache import open_cache, get, ALGORITHM
from terminan.cache_queue import init_queue, submit, claim, finish, run_once, status

IDENTITY=dict(source="grid",source_revision="a"*64,dataset="candles_1m",
 symbol="BTCUSDT",timeframe="5m",from_ms=1767225600000,to_ms=1767225840000,
 algorithm=ALGORITHM,parameters_hash="b"*64)
CANDLES=[dict(symbol="BTCUSDT",ts=1767225600000+i*60000,
 open=100+i,high=102+i,low=99+i,close=101+i,buy_volume=2,sell_volume=1)
 for i in range(5)]
SOURCE=dict(source_revision="a"*64,candles=CANDLES,
 footprint=[dict(symbol="BTCUSDT",ts=c["ts"],price=100,buy_volume=2,sell_volume=1) for c in CANDLES])

class CacheQueueTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.path=Path(self.tmp.name)/"queue.sqlite"
  self.con=init_queue(open_cache(self.path))
 def tearDown(self):
  self.con.close();self.tmp.cleanup()
 def test_queue_to_ready_and_persist(self):
  j=submit(self.con,IDENTITY,SOURCE,now=100)
  self.assertEqual(j["state"],"QUEUED")
  self.assertEqual(run_once(self.con,now=101)["state"],"FINISHED")
  self.assertEqual(status(self.con,j["job_id"])["state"],"READY")
  self.con.close();self.con=init_queue(open_cache(self.path))
  self.assertEqual(get(self.con,IDENTITY,now=102)["state"],"HIT")
 def test_duplicate_idempotent(self):
  a=submit(self.con,IDENTITY,SOURCE,now=100)
  b=submit(self.con,IDENTITY,SOURCE,now=100)
  self.assertEqual(a["job_id"],b["job_id"])
 def test_stale_token_rejected(self):
  submit(self.con,IDENTITY,SOURCE,now=100)
  old=claim(self.con,now=101)
  new=claim(self.con,now=101+121)
  self.assertNotEqual(old["token"],new["token"])
  self.assertFalse(finish(self.con,old,{},now=223))
  self.assertEqual(status(self.con,new["job_id"])["state"],"RUNNING")
 def test_partial_failed(self):
  j=submit(self.con,IDENTITY,dict(SOURCE,candles=CANDLES[:1]),now=100)
  self.assertEqual(run_once(self.con,now=101)["state"],"FINISHED")
  self.assertEqual(status(self.con,j["job_id"])["state"],"FAILED")
  self.assertEqual(get(self.con,IDENTITY,now=102)["state"],"MISS")
 def test_expired_lease_not_accepted(self):
  submit(self.con,IDENTITY,SOURCE,now=100)
  old=claim(self.con,now=101)
  self.assertFalse(finish(self.con,old,{},now=222))

if __name__=="__main__":unittest.main()

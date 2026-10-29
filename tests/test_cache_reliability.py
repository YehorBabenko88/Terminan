import contextlib, copy, hashlib, json, sqlite3, subprocess, sys, tempfile, threading, unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlencode
from urllib.request import urlopen
from terminan.saved_cache import open_cache, compute_mtf, put, get, CacheError, ALGORITHM, EXACT_INDEX
from terminan.cache_queue import init_queue, submit, claim, finish, status
from terminan.cache_monitor import read_job_result, lookup_exact_cache
from terminan import cache_monitor

BASE=1767225600000
IDENTITY=dict(source='grid',source_revision='a'*64,dataset='candles_1m',symbol='BTCUSDT',
 timeframe='5m',from_ms=BASE,to_ms=BASE+240000,algorithm=ALGORITHM,parameters_hash='b'*64)
SOURCE=dict(source_revision='a'*64,candles=[dict(symbol='BTCUSDT',ts=BASE+i*60000,
 open=100,high=102,low=99,close=101,buy_volume=2,sell_volume=1) for i in range(5)],
 footprint=[dict(symbol='BTCUSDT',ts=BASE+i*60000,price=100,buy_volume=2,sell_volume=1) for i in range(5)])

class ReliabilityTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'cache.sqlite';self.con=init_queue(open_cache(self.path))
 def tearDown(self):self.con.close();self.temp.cleanup()
 def test_missing_whole_period_is_incomplete(self):
  ident=dict(IDENTITY,to_ms=BASE+14*60000);src=copy.deepcopy(SOURCE)
  for k in ('candles','footprint'):src[k]+=[dict(r,ts=r['ts']+10*60000) for r in SOURCE[k]]
  self.assertFalse(compute_mtf(ident,src)['complete'])
 def test_incomplete_footprint_volume_and_duplicate(self):
  src=copy.deepcopy(SOURCE);src['footprint'][0]['buy_volume']=1
  self.assertFalse(compute_mtf(IDENTITY,src)['complete'])
  src=copy.deepcopy(SOURCE);src['footprint'].append(copy.deepcopy(src['footprint'][0]))
  with self.assertRaises(CacheError):compute_mtf(IDENTITY,src)
 def test_exhausted_crash_becomes_failed(self):
  j=submit(self.con,IDENTITY,SOURCE,now=0)
  for t in (1,122,243):self.assertIsNotNone(claim(self.con,now=t))
  self.assertIsNone(claim(self.con,now=364));self.assertEqual(status(self.con,j['job_id'])['state'],'FAILED')
 def test_expired_ready_can_be_requeued(self):
  j=submit(self.con,IDENTITY,SOURCE,now=0);job=claim(self.con,now=1);finish(self.con,job,compute_mtf(IDENTITY,SOURCE),now=2)
  self.con.execute('DELETE FROM cache_entries')
  self.assertEqual(submit(self.con,IDENTITY,SOURCE,now=3)['state'],'QUEUED')
 def test_completion_cannot_replace_claim_identity(self):
  submit(self.con,IDENTITY,SOURCE,now=0);job=claim(self.con,now=1);job['identity']=dict(IDENTITY,parameters_hash='c'*64)
  self.assertFalse(finish(self.con,job,compute_mtf(IDENTITY,SOURCE),now=2))
 def test_finish_rolls_back_payload_on_publish_error(self):
  submit(self.con,IDENTITY,SOURCE,now=0);job=claim(self.con,now=1)
  self.con.execute("CREATE TRIGGER fail_publish BEFORE UPDATE OF state ON cache_jobs WHEN NEW.state='READY' BEGIN SELECT RAISE(ABORT,'injected'); END")
  with self.assertRaises(sqlite3.Error):finish(self.con,job,compute_mtf(IDENTITY,SOURCE),now=2)
  self.assertEqual(self.con.execute('SELECT count(*) FROM cache_entries').fetchone()[0],0)
 def test_rehashed_but_incomplete_payload_never_ready(self):
  j=submit(self.con,IDENTITY,SOURCE,now=0);job=claim(self.con,now=1);payload=compute_mtf(IDENTITY,SOURCE);finish(self.con,job,payload,now=2)
  payload['candles']=[];raw=json.dumps(payload).encode();self.con.execute('UPDATE cache_entries SET payload=?,content_hash=?',(raw,hashlib.sha256(raw).hexdigest()))
  self.assertNotEqual(read_job_result(self.path,j['job_id'],now=3)['state'],'READY')
 def test_exact_lookup_uses_index(self):
  indexes=[r[1] for r in self.con.execute('PRAGMA index_list(cache_jobs)')]
  self.assertIn(EXACT_INDEX,indexes)
 def test_concurrent_submissions_idempotent(self):
  barrier=threading.Barrier(6)
  def work(_):
   con=open_cache(self.path)
   try:barrier.wait();return submit(con,IDENTITY,SOURCE,now=1)['job_id']
   finally:con.close()
  with ThreadPoolExecutor(max_workers=6) as pool:ids=list(pool.map(work,range(6)))
  self.assertEqual(len(set(ids)),1)
 def test_put_eviction_is_atomic(self):
  payload=compute_mtf(IDENTITY,SOURCE)
  self.con.execute("CREATE TRIGGER fail_entry BEFORE INSERT ON cache_entries BEGIN SELECT RAISE(ABORT,'injected'); END")
  self.con.execute('DROP TRIGGER fail_entry');put(self.con,IDENTITY,payload,ttl_seconds=1,now=0)
  self.con.execute("CREATE TRIGGER fail_entry BEFORE INSERT ON cache_entries BEGIN SELECT RAISE(ABORT,'injected'); END")
  with self.assertRaises(sqlite3.Error):put(self.con,dict(IDENTITY,parameters_hash='c'*64),payload,now=2)
  self.assertEqual(self.con.execute('SELECT count(*) FROM cache_entries').fetchone()[0],1)
 def test_real_killed_writer_wal_snapshot_and_reclaim(self):
  j=submit(self.con,IDENTITY,SOURCE,now=0)
  code="""import sys,json,time
from terminan.saved_cache import open_cache
from terminan.cache_queue import init_queue,claim
c=init_queue(open_cache(sys.argv[1]));job=claim(c,now=1)
c.execute('BEGIN IMMEDIATE');c.execute(\"UPDATE cache_jobs SET error_code='UNCOMMITTED' WHERE job_id=?\",(job['job_id'],))
print(json.dumps(job),flush=True);sys.stdin.readline()
"""
  with subprocess.Popen([sys.executable,'-c',code,str(self.path)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True) as proc:
   try:
    old=json.loads(proc.stdout.readline())
    self.assertEqual(read_job_result(self.path,j['job_id'],now=2)['state'],'RUNNING')
   finally:proc.kill();proc.wait(timeout=10)
  self.assertIsNone(status(self.con,j['job_id'])['error_code'])
  fresh=claim(self.con,now=122);self.assertNotEqual(old['token'],fresh['token'])
  self.assertFalse(finish(self.con,old,compute_mtf(IDENTITY,SOURCE),now=123))
  self.assertTrue(finish(self.con,fresh,compute_mtf(IDENTITY,SOURCE),now=123))
 def test_preview_reader_never_reads_full_blob_or_computes(self):
  j=submit(self.con,IDENTITY,SOURCE,now=0);job=claim(self.con,now=1);finish(self.con,job,compute_mtf(IDENTITY,SOURCE),now=2)
  original=cache_monitor.reader
  @contextlib.contextmanager
  def guarded(db):
   with original(db) as con:
    def authorizer(action,table,column,*_):
     if action==sqlite3.SQLITE_READ and (table=='cache_entries' or (table,column)==('cache_jobs','source_json')):return sqlite3.SQLITE_DENY
     if action in (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE):return sqlite3.SQLITE_DENY
     return sqlite3.SQLITE_OK
    con.set_authorizer(authorizer);yield con
  with patch.object(cache_monitor,'reader',guarded),patch('terminan.saved_cache.compute_mtf',side_effect=AssertionError('HTTP compute')):
   self.assertEqual(lookup_exact_cache(self.path,'a'*64,'BTCUSDT','5m',BASE,BASE+240000,now=3)['state'],'READY')
 def test_compact_preview_corruption_and_coverage(self):
  j=submit(self.con,IDENTITY,SOURCE,now=0);job=claim(self.con,now=1);finish(self.con,job,compute_mtf(IDENTITY,SOURCE),now=2)
  preview=json.loads(self.con.execute('SELECT payload FROM cache_previews').fetchone()[0]);preview['candles']=[];raw=json.dumps(preview).encode()
  self.con.execute('UPDATE cache_previews SET payload=?,content_hash=?',(raw,hashlib.sha256(raw).hexdigest()))
  self.assertEqual(read_job_result(self.path,j['job_id'],now=3)['state'],'CORRUPT')
 def test_lookup_uses_one_wal_snapshot(self):
  j=submit(self.con,IDENTITY,SOURCE,now=0);job=claim(self.con,now=1);finish(self.con,job,compute_mtf(IDENTITY,SOURCE),now=2)
  original=cache_monitor.result_in_snapshot
  def replace(con,job_id,now):
   self.con.execute('UPDATE cache_jobs SET identity_json=? WHERE job_id=?',(json.dumps(dict(IDENTITY,to_ms=BASE+540000)),job_id))
   return original(con,job_id,now)
  with patch.object(cache_monitor,'result_in_snapshot',replace):
   result=lookup_exact_cache(self.path,'a'*64,'BTCUSDT','5m',BASE,BASE+240000,now=3)
  self.assertEqual(result['state'],'READY');self.assertEqual(result['to_ms'],BASE+240000)
  self.assertEqual(lookup_exact_cache(self.path,'a'*64,'BTCUSDT','5m',BASE,BASE+240000,now=3)['state'],'MISS')
 def test_retry_is_explicit_and_source_immutable(self):
  j=submit(self.con,IDENTITY,SOURCE,now=0);job=claim(self.con,now=1);finish(self.con,job,error='INCOMPLETE',now=2)
  self.assertEqual(submit(self.con,IDENTITY,SOURCE,now=3)['state'],'FAILED')
  self.assertEqual(submit(self.con,IDENTITY,SOURCE,now=3,retry=True)['state'],'QUEUED')
  changed=copy.deepcopy(SOURCE);changed['candles'][0]['close']=100
  with self.assertRaises(CacheError):submit(self.con,IDENTITY,changed,now=3)
 def test_absent_footprint_is_not_a_zero_trade_attestation(self):
  src=copy.deepcopy(SOURCE)
  for c in src['candles']:c.update(buy_volume=0,sell_volume=0)
  src['footprint']=[];self.assertFalse(compute_mtf(IDENTITY,src)['complete'])
  src['zero_trade_minutes']=[c['ts'] for c in src['candles']]
  payload=compute_mtf(IDENTITY,src);self.assertTrue(payload['complete']);self.assertIsNone(payload['candles'][0]['poc_price'])
  put(self.con,IDENTITY,payload,now=1)
 def test_corrupt_preview_can_be_requeued(self):
  j=submit(self.con,IDENTITY,SOURCE,now=0);job=claim(self.con,now=1);finish(self.con,job,compute_mtf(IDENTITY,SOURCE),now=2)
  self.con.execute('UPDATE cache_previews SET payload=?',(b'corrupt',))
  self.assertEqual(submit(self.con,IDENTITY,SOURCE,now=3)['state'],'QUEUED')
 def test_legacy_missing_index_never_falls_back_to_scan(self):
  self.con.execute('DROP INDEX '+EXACT_INDEX)
  with self.assertRaises(ValueError):lookup_exact_cache(self.path,'a'*64,'BTCUSDT','5m',BASE,BASE+240000)
  self.assertNotIn(EXACT_INDEX,[r[1] for r in self.con.execute('PRAGMA index_list(cache_jobs)')])
 def test_manual_preview_is_consistent_with_data_epoch(self):
  from scripts.audit_cache import prepare_preview
  from terminan.saved_sources import SavedSources
  root=Path(self.temp.name)/'preview';result=prepare_preview(root)
  source=SavedSources(json.loads((root/'sources.json').read_text()))
  page=source.page('audit-fixture','candles_1m')
  self.assertEqual(page['epoch'],result['source_revision'])
  self.assertEqual(lookup_exact_cache(root/'cache.sqlite',page['epoch'],'BTCUSDT','5m',BASE,BASE+240000)['state'],'READY')
 def test_http_is_read_only_and_does_not_start_worker(self):
  from terminan.saved_server import SavedServer,SavedHandler
  j=submit(self.con,IDENTITY,SOURCE);job=claim(self.con);finish(self.con,job,compute_mtf(IDENTITY,SOURCE))
  server=SavedServer(('127.0.0.1',0),SavedHandler);server.cache_db=self.path;server.candidate_sha='d'*40
  thread=threading.Thread(target=server.serve_forever);thread.start()
  before=self.con.execute('PRAGMA data_version').fetchone()
  try:
   with patch('terminan.cache_queue.run_once',side_effect=AssertionError('HTTP worker')),patch('terminan.saved_cache.compute_mtf',side_effect=AssertionError('HTTP compute')):
    q=urlencode(dict(revision='a'*64,symbol='BTCUSDT',timeframe='5m',from_ms=BASE,to_ms=BASE+240000))
    for path in ('/api/saved/cache-result?job_id='+j['job_id'],'/api/saved/cache-lookup?'+q):
     with urlopen(f'http://127.0.0.1:{server.server_port}'+path,timeout=3) as r:self.assertEqual(json.load(r)['state'],'READY')
   self.assertEqual(before,self.con.execute('PRAGMA data_version').fetchone())
  finally:server.shutdown();server.server_close();thread.join(timeout=5)

import hashlib,json,sqlite3,tempfile,unittest
from pathlib import Path
from terminan.paper_ledger import PaperReplayLedger,canonical_json,ReplayConflict
class ReadOnlyLookupTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.path=self.root/'paper.sqlite'
 def lookup(self,path=None,pin='a'*64):
  lookup=getattr(PaperReplayLedger,'lookup_existing',None);self.assertIsNotNone(lookup,'read-only lookup must precede ledger construction')
  return lookup(self.path if path is None else path,'run',pin)
 def receipt(self):
  receipt=dict(schema='terminan.paper.result.v2',run_id='run',request_sha256='a'*64,status='OFFLINE_UNATTESTED',provenance='CALLER_SUPPLIED_UNATTESTED',execution_authority=False,trading_authorized=False,strategy={'id':'poc_next_minute','version':'2'},fills=[])
  receipt['result_sha256']=hashlib.sha256(canonical_json(receipt)).hexdigest();return receipt
 def image(self):return {p.name:p.read_bytes() for p in self.root.iterdir() if p.is_file()}
 def test_absent_path_is_not_created(self):
  self.assertIsNone(self.lookup());self.assertEqual(self.image(),{})
 def test_owned_receipt_read_and_conflict_leave_exact_bytes_unchanged(self):
  receipt=self.receipt();PaperReplayLedger(self.path).record(receipt);before=self.image()
  self.assertEqual(self.lookup(),receipt)
  with self.assertRaises(ReplayConflict):self.lookup(pin='b'*64)
  self.assertEqual(self.image(),before)
 def test_foreign_empty_or_arbitrary_existing_file_is_never_adopted(self):
  for raw in (b'',b'not SQLite'):
   self.path.write_bytes(raw);before=self.image()
   with self.assertRaises(RuntimeError):self.lookup()
   self.assertEqual(self.image(),before);self.path.unlink()
  db=sqlite3.connect(self.path)
  try:db.execute('CREATE TABLE foreign_data(value)');db.commit()
  finally:db.close()
  before=self.image()
  with self.assertRaises(RuntimeError):self.lookup()
  self.assertEqual(self.image(),before)
 def test_any_sidecar_is_refused_before_sqlite_can_create_or_recover_files(self):
  PaperReplayLedger(self.path).record(self.receipt())
  for suffix in ('-wal','-shm','-journal'):
   side=Path(str(self.path)+suffix);side.write_bytes(b'SYNTHETIC_SIDEFILE');before=self.image()
   with self.assertRaises(RuntimeError):self.lookup()
   self.assertEqual(self.image(),before);side.unlink()
 def test_live_wal_is_refused_without_mutating_any_original_file(self):
  PaperReplayLedger(self.path).record(self.receipt());writer=sqlite3.connect(self.path)
  try:
   writer.execute('PRAGMA journal_mode=WAL');writer.execute('CREATE TABLE extra_owned_state(value)');writer.commit();before=self.image()
   with self.assertRaises(RuntimeError):self.lookup()
   self.assertEqual(self.image(),before)
  finally:writer.close()

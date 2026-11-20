import base64,hashlib,importlib,json,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from terminan.paper_ledger import PaperReplayLedger,canonical_json
from terminan.paper_journal import PaperJournal
FIXTURE=json.loads((Path(__file__).parent/'fixtures/historical_paper_v1_f20.json').read_text())
class HistoricalRestoreTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.source=self.root/'original.sqlite';self.source.write_bytes(base64.b64decode(FIXTURE['database_base64']));self.pin=FIXTURE['database_sha256'];self.target=self.root/'restored.sqlite'
 def migration(self):
  self.assertIsNotNone(importlib.util.find_spec('terminan.migration.paper_receipts'),'explicit historical decoder/isolated restore required')
  return importlib.import_module('terminan.migration.paper_receipts')
 def restore(self,pin=None,target=None):
  return self.migration().restore_historical_paper_stream(self.source,pin or self.pin,'preserved-v1-source','paper-v1-run',target or self.target,target_source_id='restored',target_run_id='canonical-run')
 def test_historical_receipt_is_read_only_and_needs_no_math_sdk(self):
  mod=self.migration();before=self.source.read_bytes()
  with patch.dict('sys.modules',{'market_profile_math':None}):
   receipt=mod.read_historical_paper_receipt(self.source,self.pin,'historical-receipt',FIXTURE['receipt']['request_sha256'])
  self.assertEqual(receipt,FIXTURE['receipt']);self.assertEqual(self.source.read_bytes(),before);self.assertEqual({p.name for p in self.root.iterdir()},{'original.sqlite'})
 def test_original_events_restore_into_new_database_and_recover_open_position(self):
  mod=self.migration();before=self.source.read_bytes()
  exported=mod.export_historical_paper_stream(self.source,self.pin,'preserved-v1-source','paper-v1-run')
  self.assertEqual(exported['events'],FIXTURE['events']);self.assertEqual(exported['acks'],FIXTURE['acks'])
  result=self.restore();self.assertFalse(result['execution_authority']);self.assertFalse(result['trading_authorized']);self.assertEqual(result['checkpoint'],3)
  journal=PaperJournal(PaperReplayLedger(self.target),'restored','canonical-run','BTCUSDT');event={**FIXTURE['exit_event'],'schema':'terminan.paper.event.v2'}
  ack=journal.submit(event);self.assertEqual(ack['fill'],FIXTURE['expected_exit_ack']['fill']);self.assertEqual(ack['strategy_id'],'poc_next_minute');self.assertEqual(ack['strategy_version'],'2')
  self.assertEqual(self.source.read_bytes(),before);self.assertEqual(hashlib.sha256(before).hexdigest(),self.pin)
 def test_bad_snapshot_or_existing_destination_is_never_written_or_adopted(self):
  before=self.source.read_bytes()
  with self.assertRaises(ValueError):self.restore(pin='0'*64)
  self.assertFalse(self.target.exists());self.target.write_bytes(b'UNRELATED_OWNED_FIXTURE')
  with self.assertRaises(ValueError):self.restore()
  self.assertEqual(self.target.read_bytes(),b'UNRELATED_OWNED_FIXTURE');self.assertEqual(self.source.read_bytes(),before)
 def test_corrupt_final_ack_refuses_before_destination_creation(self):
  db=sqlite3.connect(self.source)
  try:db.execute("UPDATE paper_events_v1 SET ack=? WHERE sequence=3",(b'{}',));db.commit()
  finally:db.close()
  before=self.source.read_bytes()
  with self.assertRaises(RuntimeError):self.restore(pin=hashlib.sha256(before).hexdigest())
  self.assertFalse(self.target.exists());self.assertEqual(self.source.read_bytes(),before)

 def test_owner_refusal_or_unknown_columns_precede_fresh_destination(self):
  mod=self.migration();before=self.source.read_bytes()
  with patch('market_profile_math.paper_position_size',side_effect=ValueError('OWNER_REFUSED')),self.assertRaises(ValueError):self.restore()
  self.assertFalse(self.target.exists());self.assertEqual(self.source.read_bytes(),before)
  db=sqlite3.connect(self.source)
  try:db.execute('ALTER TABLE paper_streams_v1 ADD COLUMN unknown TEXT');db.commit()
  finally:db.close()
  before=self.source.read_bytes()
  with self.assertRaises(RuntimeError):self.restore(pin=hashlib.sha256(before).hexdigest())
  self.assertFalse(self.target.exists());self.assertEqual(self.source.read_bytes(),before)

"""Explicit owner recovery from inert copies of genuine SQLite rollback journals."""
import json,pathlib,sqlite3,tempfile,unittest,os
from contextlib import closing,contextmanager
from hashlib import sha256
from unittest.mock import patch
from terminan.paper_ledger import PaperReplayLedger,canonical_json
class PaperOwnedRecoveryTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=pathlib.Path(self.temp.name);self.path=self.root/'owned.db'
  receipt=dict(run_id='known',request_sha256='a'*64,status='OFFLINE_UNATTESTED',provenance='CALLER_SUPPLIED_UNATTESTED',execution_authority=False,trading_authorized=False)
  receipt['result_sha256']=sha256(canonical_json(receipt)).hexdigest();self.receipt=receipt
  PaperReplayLedger(self.path).record(receipt)
 def recover(self,path=None):
  self.assertTrue(hasattr(PaperReplayLedger,'recover_owned'),'missing explicit owned recovery API')
  return PaperReplayLedger.recover_owned(path or self.path)
 def snapshot_journal(self,hot=False):
  source=self.root/'writer.db';source.write_bytes(self.path.read_bytes())
  with closing(sqlite3.connect(source)) as c:
   c.execute('PRAGMA cache_size=1');c.execute('BEGIN IMMEDIATE')
   for i in range(200 if hot else 1):c.execute('INSERT INTO paper_replay_receipts VALUES(?,?,?)',('partial'+str(i),'b'*64,'x'*4096 if hot else '{}'))
   self.path.write_bytes(source.read_bytes());journal=pathlib.Path(str(source)+'-journal').read_bytes();pathlib.Path(str(self.path)+'-journal').write_bytes(journal);c.rollback()
  self.assertEqual(journal[:8],bytes.fromhex('d9d505f920a163d7') if hot else b'\0'*8)
 def assert_known(self):self.assertEqual(PaperReplayLedger.lookup_existing(self.path,'known','a'*64),self.receipt)
 def test_nonhot_owned_journal_requires_explicit_recovery_and_keeps_receipt(self):
  self.snapshot_journal()
  with self.assertRaisesRegex(RuntimeError,'sidecars'):PaperReplayLedger.lookup_existing(self.path,'known','a'*64)
  self.assertIsNone(self.recover());self.assert_known();self.assertFalse(pathlib.Path(str(self.path)+'-journal').exists())
  with closing(sqlite3.connect(self.path)) as c:self.assertEqual(c.execute('SELECT run_id FROM paper_replay_receipts').fetchall(),[('known',)])
 def test_hot_journal_rolls_back_real_spilled_uncommitted_pages_without_process(self):
  self.snapshot_journal(hot=True);self.assertIsNone(self.recover());self.assert_known()
  with closing(sqlite3.connect(self.path)) as c:self.assertEqual(c.execute('SELECT run_id FROM paper_replay_receipts').fetchall(),[('known',)])
 def test_foreign_or_malformed_journal_refuses_without_modifying_originals(self):
  self.snapshot_journal();j=pathlib.Path(str(self.path)+'-journal');valid=j.read_bytes()
  for raw in (b'FOREIGN_SIDECAR',b'badmagic'+valid[8:],valid[:24]+b'\0'*4+valid[28:]):
   j.write_bytes(raw);before=self.path.read_bytes()
   with self.assertRaises(RuntimeError):self.recover()
   self.assertEqual(self.path.read_bytes(),before);self.assertEqual(j.read_bytes(),raw)
 def test_foreign_schema_or_application_id_is_not_adopted(self):
  for kind in ('schema','appid','collation'):
   target=self.root/(kind+'.db')
   with closing(sqlite3.connect(target)) as c:
    if kind=='collation':c.execute('CREATE TABLE paper_replay_receipts(run_id TEXT COLLATE NOCASE PRIMARY KEY NOT NULL,request_sha256 TEXT NOT NULL,receipt TEXT NOT NULL)')
    else:c.execute('CREATE TABLE foreign_data(value TEXT)');c.execute('INSERT INTO foreign_data VALUES("keep")')
    if kind in ('schema','collation'):c.execute('PRAGMA application_id=1414550065')
    c.commit()
   before=target.read_bytes()
   with self.assertRaises(RuntimeError):self.recover(target)
   self.assertEqual(target.read_bytes(),before)
 def test_wal_shm_and_hardlinks_refuse_without_sidecar_deletion(self):
  for suffix in ('-wal','-shm'):
   side=pathlib.Path(str(self.path)+suffix);side.write_bytes(b'foreign');before=self.path.read_bytes()
   with self.assertRaises(RuntimeError):self.recover()
   self.assertEqual(side.read_bytes(),b'foreign');self.assertEqual(self.path.read_bytes(),before);side.unlink()
  alias=self.root/'hardlink.db';os.link(self.path,alias)
  with self.assertRaises(RuntimeError):self.recover()
  self.assertTrue(alias.exists())
 def test_missing_path_never_creates_database(self):
  p=self.root/'missing.db'
  with self.assertRaises(RuntimeError):self.recover(p)
  self.assertFalse(p.exists())
 def test_committed_receipt_corruption_refuses_before_headerwrite(self):
  with closing(sqlite3.connect(self.path)) as c:c.execute('UPDATE paper_replay_receipts SET receipt="{}"');c.commit()
  before=self.path.read_bytes()
  with self.assertRaises(RuntimeError):self.recover()
  self.assertEqual(self.path.read_bytes(),before)
 def test_identity_replacement_after_staging_refuses_before_recovery_write(self):
  import terminan.paper_ledger as module
  self.assertTrue(hasattr(module,'tempfile'),'missing owned staging boundary')
  original=module.tempfile.TemporaryDirectory;replacement=[]
  @contextmanager
  def race(*args,**kwargs):
   with original(*args,**kwargs) as tmp:yield tmp
   other=self.root/'replacement.db';other.write_bytes(self.path.read_bytes());os.replace(other,self.path);replacement.append(self.path.read_bytes())
  with patch.object(module.tempfile,'TemporaryDirectory',race),self.assertRaisesRegex(RuntimeError,'changed'):self.recover()
  self.assertEqual(self.path.read_bytes(),replacement[0])

 def test_corrupt_hot_page_checksum_is_not_recovered_or_modified(self):
  self.snapshot_journal(hot=True);j=pathlib.Path(str(self.path)+'-journal');raw=bytearray(j.read_bytes());sector=int.from_bytes(raw[20:24],'big');page=int.from_bytes(raw[24:28],'big');raw[sector+4+page]^=1;j.write_bytes(raw);before=self.path.read_bytes();stored=j.read_bytes()
  with self.assertRaises(RuntimeError):self.recover()
  self.assertEqual(self.path.read_bytes(),before);self.assertEqual(j.read_bytes(),stored)

 def test_inert_precommit_and_postcommit_ack_recovery_never_executes_engine(self):
  from terminan.paper_journal import PaperJournal
  from test_paper_journal import ENABLE,MINUTE,ENTRY,EXIT
  for timing in ('before','after'):
   source=self.root/(timing+'-writer.db');target=self.root/(timing+'-restored.db');ledger=PaperReplayLedger(source);journal=PaperJournal(ledger,'source','run','BTCUSDT')
   for item in (ENABLE,MINUTE,ENTRY):journal.submit(item)
   original=ledger._paper_event_transaction
   def copy_snapshot():
    target.write_bytes(source.read_bytes());side=pathlib.Path(str(source)+'-journal')
    if side.exists():pathlib.Path(str(target)+'-journal').write_bytes(side.read_bytes())
   @contextmanager
   def interrupted(*,write):
    with original(write=write) as database:
     yield database
     if write and timing=='before':copy_snapshot();raise OSError('INERT_PRECOMMIT_NO_ACK')
    if write and timing=='after':copy_snapshot();raise OSError('INERT_POSTCOMMIT_NO_ACK')
   with patch.object(ledger,'_paper_event_transaction',interrupted),self.assertRaises(OSError):journal.submit(EXIT)
   with patch('terminan.paper_journal.PaperEngine',side_effect=AssertionError('RECOVERY_MUST_NOT_EXECUTE_ENGINE')):self.assertIsNone(self.recover(target))
   restored=PaperJournal(PaperReplayLedger(target),'source','run','BTCUSDT');initial=list(restored.read_fills());self.assertEqual(len(initial),int(timing=='after'))
   ack=restored.submit(EXIT);self.assertEqual(ack['checkpoint'],4)
   if initial:self.assertEqual(initial,[ack])
   self.assertEqual(list(PaperJournal(PaperReplayLedger(target),'source','run','BTCUSDT').read_fills()),[ack])

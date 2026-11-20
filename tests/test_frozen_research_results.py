from contextlib import closing
import hashlib,sqlite3,tempfile,unittest,os
from pathlib import Path
from unittest.mock import patch
from terminan.paper_ledger import PaperReplayLedger
from terminan.research_archive import ResearchArchive
FIXTURES=Path(__file__).parent/'fixtures'
def pin(path):return hashlib.sha256(path.read_bytes()).hexdigest()
class FrozenResearchReaderTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.source=self.root/'source.sqlite';self.target=self.root/'target.sqlite'
 def fixture(self,kind='six'):
  with closing(sqlite3.connect(self.source)) as db,db:db.executescript((FIXTURES/('historical-research-'+kind+'.sql')).read_text())
  return pin(self.source)
 def restore(self,digest=None,source_id='frozen-source'):
  from terminan.migration.research_results import restore_frozen_research_results
  return restore_frozen_research_results(self.source,digest or pin(self.source),source_id,self.target)
 def test_both_original_schemas_round_trip_without_source_sqlite_open_or_byte_changes(self):
  for kind,count in (('six',2),('nine',3)):
   with self.subTest(kind=kind):
    if self.source.exists():self.source.unlink()
    if self.target.exists():self.target.unlink()
    digest=self.fixture(kind);before=self.source.read_bytes();original=sqlite3.connect;opened=[]
    def guarded(name,*a,**kw):
     self.assertNotIn(self.source.as_posix(),str(name).replace('\\','/'));opened.append((str(name),kw));return original(name,*a,**kw)
    with patch('sqlite3.connect',side_effect=guarded):result=self.restore(digest)
    self.assertEqual(self.source.read_bytes(),before);self.assertEqual(pin(self.source),digest);self.assertFalse(result['execution_authority']);self.assertFalse(result['trading_authorized'])
    rows=list(ResearchArchive(PaperReplayLedger(self.target)).read_snapshot('frozen-source'));self.assertEqual(len(rows),count)
    self.assertEqual(rows[0][2][5],'{"net": 1.20, "legacy": NaN}');self.assertEqual(rows[1][2][5],'not-json: original metrics TEXT')
    self.assertEqual(rows[1][2][4],float('inf') if kind=='six' else float('-inf'))
    if kind=='nine':self.assertEqual(rows[1][2][-3:],('job',7,2));self.assertEqual(rows[2][2][-3:],('job',8,3))
    self.assertTrue(any('?mode=ro&immutable=1' in name for name,_ in opened));self.assertEqual(list(self.root.glob('source.sqlite-*')),[])
 def test_any_existing_destination_is_refused_without_adoption_or_mutation(self):
  self.fixture()
  for kind in ('empty','foreign','owned','same-source','hardlink'):
   if self.target.exists():self.target.unlink()
   if kind=='empty':self.target.touch()
   elif kind=='foreign':self.target.write_bytes(b'foreign')
   elif kind=='owned':PaperReplayLedger(self.target)
   elif kind=='same-source':self.target=self.source
   else:os.link(self.source,self.target)
   before=self.target.read_bytes()
   with self.subTest(kind=kind),self.assertRaises((ValueError,RuntimeError,FileExistsError)):self.restore()
   self.assertEqual(self.target.read_bytes(),before)
   if kind=='same-source':self.target=self.root/'target.sqlite'
 def test_hash_identity_and_bad_late_row_refuse_before_destination_creation(self):
  self.fixture()
  for digest,ident in (('b'*64,'source'),(pin(self.source),'../unsafe')):
   with self.assertRaises(ValueError):self.restore(digest,ident)
   self.assertFalse(self.target.exists())
  with closing(sqlite3.connect(self.source)) as db,db:db.execute("UPDATE research_results SET metrics=x'ff' WHERE run_id='run-b'")
  with self.assertRaises(ValueError):self.restore()
  self.assertFalse(self.target.exists())
 def test_hot_sidecars_and_wal_header_are_refused_without_recovery(self):
  self.fixture();before=self.source.read_bytes()
  for suffix in ('-wal','-shm','-journal'):
   side=Path(str(self.source)+suffix);side.write_bytes(b'preserve hot state')
   with self.subTest(suffix=suffix),self.assertRaises(ValueError):self.restore()
   self.assertEqual(self.source.read_bytes(),before);self.assertEqual(side.read_bytes(),b'preserve hot state');self.assertFalse(self.target.exists());side.unlink()
  raw=bytearray(before);raw[18]=raw[19]=2;self.source.write_bytes(raw)
  with self.assertRaises(ValueError):self.restore()
  self.assertEqual(self.source.read_bytes(),raw);self.assertFalse(self.target.exists())
 def test_wrong_real_table_schema_or_view_refuses_before_destination(self):
  self.fixture('nine')
  with closing(sqlite3.connect(self.source)) as db,db:db.execute('DROP TABLE staged_research_results')
  with self.assertRaises(ValueError):self.restore()
  self.assertFalse(self.target.exists())
  with closing(sqlite3.connect(self.source)) as db,db:db.execute('CREATE VIEW staged_research_results AS SELECT * FROM research_results')
  with self.assertRaises(ValueError):self.restore()
  self.assertFalse(self.target.exists())
 def test_size_budget_refuses_before_target_and_copy_sqlite_open(self):
  self.fixture()
  from terminan.migration import research_results as module
  with patch.object(module,'_MAX_BACKUP_BYTES',self.source.stat().st_size-1),patch('sqlite3.connect',side_effect=AssertionError('NO_SQL_BEFORE_COPY_BUDGET')),self.assertRaises(ValueError):self.restore()
  self.assertFalse(self.target.exists())

 def test_private_snapshot_is_readonly_and_source_change_prevents_any_target(self):
  self.fixture();before=self.source.read_bytes();original=sqlite3.connect;checked=[]
  def change_after_copy(name,*a,**kw):
   db=original(name,*a,**kw)
   if '?mode=ro&immutable=1' in str(name):
    with self.assertRaises(sqlite3.OperationalError):db.execute('CREATE TABLE forbidden(x)')
    checked.append(True);self.source.write_bytes(before+b'changed')
   return db
  with patch('sqlite3.connect',side_effect=change_after_copy),self.assertRaises(ValueError):self.restore()
  self.assertEqual(checked,[True]);self.assertFalse(self.target.exists());self.assertEqual(self.source.read_bytes(),before+b'changed')
 def test_archive_row_budget_is_enforced_before_destination_ddl(self):
  self.fixture()
  with patch('terminan.research_archive._MAX_ROWS',1),self.assertRaises(ValueError):self.restore()
  self.assertFalse(self.target.exists())
 def test_operator_cli_uses_same_reader_and_sanitized_failure_without_process(self):
  import io,json
  from terminan.migration.research_results import main
  digest=self.fixture();out=io.StringIO()
  self.assertEqual(main([str(self.source),digest,'cli-source',str(self.target)],stdout=out),0)
  self.assertFalse(json.loads(out.getvalue())['execution_authority'])
  out=io.StringIO();self.assertEqual(main([str(self.source),digest,'cli-source',str(self.target)],stdout=out),1)
  self.assertEqual(json.loads(out.getvalue())['status'],'HISTORICAL_RESTORE_REJECTED');self.assertNotIn(str(self.source),out.getvalue())

 def test_restore_does_not_require_math_or_old_packages(self):
  import sys
  self.fixture()
  with patch.dict(sys.modules,{'market_math':None,'market_profile_math':None,'strattester':None,'grid':None,'meta_analyse':None}):result=self.restore()
  self.assertEqual(result['source_status'],'CALLER_SUPPLIED_UNATTESTED');self.assertFalse(result['execution_authority'])

 def test_original_empty_and_signed_zero_infinity_fixture_rows_preserved(self):
  for stamps in ((),(float('inf'),-0.0,float('-inf'))):
   if self.source.exists():self.source.unlink()
   if self.target.exists():self.target.unlink()
   self.fixture()
   with closing(sqlite3.connect(self.source)) as db,db:
    db.execute('DELETE FROM research_results')
    db.executemany('INSERT INTO research_results VALUES(?,?,?,?,?,?)',[(f'run-{i}','BTCUSDT','legacy','1',stamp,'{"value": Infinity}') for i,stamp in reversed(list(enumerate(stamps)))])
    expected=db.execute('SELECT * FROM research_results ORDER BY run_id').fetchall()
   before=self.source.read_bytes();result=self.restore();actual=[row for _,_,row in ResearchArchive(PaperReplayLedger(self.target)).read_snapshot('frozen-source')]
   self.assertEqual(result['tables']['research_results']['row_count'],len(expected));self.assertEqual(actual,expected);self.assertEqual([r[4].hex() for r in actual],[r[4].hex() for r in expected]);self.assertEqual(self.source.read_bytes(),before)
 def test_original_six_noncanonical_ddl_variants_refuse_before_any_destination(self):
  fields='run_id TEXT NOT NULL,symbol TEXT NOT NULL,strategy_id TEXT NOT NULL,strategy_version TEXT NOT NULL,created_at REAL NOT NULL,metrics TEXT NOT NULL'
  key=',PRIMARY KEY(run_id,symbol,strategy_id,strategy_version)'
  variants=[fields,fields+',PRIMARY KEY(symbol,run_id,strategy_id,strategy_version)',fields.replace('created_at REAL','created_at NUMERIC')+key,fields.replace('run_id TEXT NOT NULL','run_id TEXT')+key,fields.replace('metrics TEXT NOT NULL','metrics TEXT')+key,fields+',hidden_copy TEXT GENERATED ALWAYS AS(metrics) VIRTUAL'+key]
  for definition in variants:
   if self.source.exists():self.source.unlink()
   with closing(sqlite3.connect(self.source)) as db,db:db.execute('CREATE TABLE research_results('+definition+')')
   before=self.source.read_bytes()
   with self.subTest(definition=definition),self.assertRaises(ValueError):self.restore()
   self.assertFalse(self.target.exists());self.assertEqual(self.source.read_bytes(),before);self.assertEqual(list(self.root.iterdir()),[self.source])
 def test_present_empty_stage_with_legacy_schema_is_not_absence(self):
  self.fixture()
  stage=(FIXTURES/'historical-research-nine.sql').read_text().split(';')[1]+';'
  with closing(sqlite3.connect(self.source)) as db,db:db.executescript(stage)
  before=self.source.read_bytes()
  with self.assertRaises(ValueError):self.restore()
  self.assertFalse(self.target.exists());self.assertEqual(self.source.read_bytes(),before)
 def test_active_wal_writer_and_all_sidecar_bytes_remain_untouched(self):
  self.fixture()
  with closing(sqlite3.connect(self.source)) as writer:
   writer.execute('PRAGMA journal_mode=WAL');writer.execute('UPDATE research_results SET created_at=999');writer.commit()
   paths=sorted(self.root.iterdir());before={p.name:p.read_bytes() for p in paths}
   with self.assertRaises(ValueError):self.restore()
   self.assertEqual(sorted(self.root.iterdir()),paths);self.assertEqual({p.name:p.read_bytes() for p in paths},before);self.assertFalse(self.target.exists())
 def test_original_special_source_path_and_sidecar_alias_boundary(self):
  self.source=self.root/'archive #1.sqlite';self.fixture();self.target=Path(str(self.source)+'-wal')
  with self.assertRaises(ValueError):self.restore()
  self.assertFalse(self.target.exists());self.target=self.root/'restored.sqlite';self.restore()
  backup=self.root/'backup.sqlite'
  with closing(sqlite3.connect(self.target)) as db,closing(sqlite3.connect(backup)) as copy:db.backup(copy)
  a=list(ResearchArchive(PaperReplayLedger(self.target)).read_snapshot('frozen-source'));b=list(ResearchArchive(PaperReplayLedger(backup)).read_snapshot('frozen-source'));self.assertEqual(a,b)

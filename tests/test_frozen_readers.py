import os,sqlite3,tempfile,unittest
from pathlib import Path
from contextlib import closing
from unittest import mock
from terminan import data
from terminan.migration.candle_snapshot import read_instrument_snapshot

class FrozenReaderTests(unittest.TestCase):
 def fixture(self,folder):
  p=Path(folder)/'research.sqlite'
  with closing(sqlite3.connect(p)) as db,db:
   db.execute('CREATE TABLE research_results(run_id TEXT,symbol TEXT,strategy_id TEXT,strategy_version TEXT,created_at REAL,metrics TEXT)')
   db.execute('INSERT INTO research_results VALUES(?,?,?,?,?,?)',('r1','BTCUSDT','s','v1',1,'{"pnl":-2}'))
   db.execute('CREATE TABLE candles(symbol TEXT)')
   db.execute("INSERT INTO candles VALUES('BTCUSDT')")
  return p
 def test_delete_snapshot_preserves_result_and_all_bytes(self):
  with tempfile.TemporaryDirectory() as folder:
   p=self.fixture(folder);before=p.read_bytes()
   with mock.patch.dict(os.environ,{'TERMINAN_RESULTS_DB':str(p)}):
    self.assertEqual(data.research('BTCUSDT'),[dict(run_id='r1',strategy='s',version='v1',created_at=1.0,metrics={'pnl':-2})])
   self.assertEqual(read_instrument_snapshot(p),['BTCUSDT'])
   self.assertEqual(p.read_bytes(),before);self.assertEqual(list(p.parent.iterdir()),[p])
 def test_sidecars_refused_before_sqlite_open(self):
  for suffix in ('-wal','-shm','-journal'):
   with self.subTest(suffix=suffix),tempfile.TemporaryDirectory() as folder:
    p=self.fixture(folder);side=Path(str(p)+suffix);side.write_bytes(b'')
    with mock.patch.dict(os.environ,{'TERMINAN_RESULTS_DB':str(p)}),mock.patch.object(sqlite3,'connect',side_effect=AssertionError('must refuse before SQLite')):
     with self.assertRaises(ValueError):data.research('BTCUSDT')
     with self.assertRaises(ValueError):read_instrument_snapshot(p)
    self.assertEqual(side.read_bytes(),b'')
 def test_wal_header_without_sidecars_refused_before_open(self):
  with tempfile.TemporaryDirectory() as folder:
   p=self.fixture(folder);raw=bytearray(p.read_bytes());raw[18:20]=bytes((2,2));p.write_bytes(raw)
   with mock.patch.dict(os.environ,{'TERMINAN_RESULTS_DB':str(p)}),mock.patch.object(sqlite3,'connect',side_effect=AssertionError('must refuse before SQLite')):
    with self.assertRaises(ValueError):data.research('BTCUSDT')
   self.assertEqual(p.read_bytes(),raw);self.assertEqual(list(p.parent.iterdir()),[p])
 def test_real_wal_copy_never_creates_shm(self):
  with tempfile.TemporaryDirectory() as folder:
   p=self.fixture(folder);dest=p.parent/'frozen.sqlite'
   with closing(sqlite3.connect(p)) as writer:
    writer.execute('PRAGMA journal_mode=WAL');writer.execute("INSERT INTO candles VALUES('ETHUSDT')");writer.commit()
    dest.write_bytes(p.read_bytes());Path(str(dest)+'-wal').write_bytes(Path(str(p)+'-wal').read_bytes())
    before={x.name:x.read_bytes() for x in p.parent.glob('frozen.sqlite*')}
    with mock.patch.dict(os.environ,{'TERMINAN_RESULTS_DB':str(dest)}):
     with self.assertRaises(ValueError):data.research('BTCUSDT')
    self.assertEqual({x.name:x.read_bytes() for x in p.parent.glob('frozen.sqlite*')},before)
 def test_missing_configuration_returns_empty(self):
  with mock.patch.dict(os.environ,{},clear=True):self.assertEqual(data.research('BTCUSDT'),[])
 def test_reader_connection_denies_writes(self):
  from terminan.migration.research_results import open_frozen_sqlite_snapshot
  with tempfile.TemporaryDirectory() as folder:
   p=self.fixture(folder);before=p.read_bytes()
   with open_frozen_sqlite_snapshot(p) as db:
    with self.assertRaises(sqlite3.OperationalError):db.execute("DELETE FROM candles")
   self.assertEqual(p.read_bytes(),before);self.assertEqual(list(p.parent.iterdir()),[p])
 def test_source_changed_during_projection_is_refused(self):
  with tempfile.TemporaryDirectory() as folder:
   p=self.fixture(folder);decode=data.json.loads
   def mutate(raw):
    result=decode(raw)
    with p.open('ab') as out:out.write(b'changed')
    return result
   with mock.patch.dict(os.environ,{'TERMINAN_RESULTS_DB':str(p)}),mock.patch.object(data.json,'loads',side_effect=mutate):
    with self.assertRaisesRegex(ValueError,'changed during read'):data.research('BTCUSDT')
 def test_hardlinked_source_refused_before_sqlite(self):
  with tempfile.TemporaryDirectory() as folder:
   p=self.fixture(folder);alias=p.parent/'alias.sqlite';os.link(p,alias)
   with mock.patch.dict(os.environ,{'TERMINAN_RESULTS_DB':str(p)}),mock.patch.object(sqlite3,'connect',side_effect=AssertionError('preflight required')):
    with self.assertRaises(ValueError):data.research('BTCUSDT')

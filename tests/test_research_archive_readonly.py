"""Historical archive reads must never create/recover a database."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest
from terminan.paper_ledger import PaperReplayLedger
from terminan.research_archive import ResearchArchive,research_result_receipt
class HistoricalArchiveReadOnlyTests(unittest.TestCase):
 def setUp(self):
  self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve();self.path=self.root/'archive.sqlite'
  self.row=('run','BTCUSDT','historical','1',123.125,'{"score":NaN}')
  self.ledger=PaperReplayLedger(self.path);self.archive=ResearchArchive(self.ledger)
  self.archive.import_snapshot('fixture',{'research_results':[self.row]},research_result_receipt('a'*64,{'research_results':[self.row]}))
 def test_missing_owned_path_is_not_recreated_by_read(self):
  retained=self.root/'retained.sqlite';self.assertEqual(retained.parent,self.root);self.path.rename(retained);before=retained.read_bytes()
  with self.assertRaises((KeyError,RuntimeError)):list(self.archive.read_snapshot('fixture'))
  self.assertFalse(self.path.exists());self.assertEqual(retained.read_bytes(),before)
 def test_existing_read_does_not_enter_readwrite_connection(self):
  before=self.path.read_bytes()
  with patch.object(PaperReplayLedger,'_connect',side_effect=AssertionError('READWRITE_CONNECTION_FORBIDDEN')):
   self.assertEqual(list(self.archive.read_snapshot('fixture')),[('research_results','LEGACY_UNFENCED',self.row)])
  self.assertEqual(self.path.read_bytes(),before)
 def test_present_sidecar_is_preserved_and_refused_before_sqlite_open(self):
  side=Path(str(self.path)+'-journal');side.write_bytes(b'foreign-retained-sidecar');before={p.name:p.read_bytes() for p in self.root.iterdir()}
  with self.assertRaises(RuntimeError):list(self.archive.read_snapshot('fixture'))
  self.assertEqual({p.name:p.read_bytes() for p in self.root.iterdir()},before)
 def test_public_existing_reader_never_initializes_or_adopts_missing_file(self):
  with patch.object(PaperReplayLedger,'__init__',side_effect=AssertionError('NO_DATABASE_FACTORY')):
   self.assertEqual(list(ResearchArchive.read_existing(self.path,'fixture')),[('research_results','LEGACY_UNFENCED',self.row)])
   absent=self.root/'absent.sqlite'
   with self.assertRaises(KeyError):list(ResearchArchive.read_existing(absent,'fixture'))
   self.assertFalse(absent.exists())
 def test_lexical_network_parent_alias_and_stream_paths_refuse_before_filesystem(self):
  candidates=('//untrusted/share/archive.sqlite',str(self.root/'nested'/'..'/'archive.sqlite'),str(self.path)+':untrusted')
  for candidate in candidates:
   with self.subTest(path=candidate),patch.object(Path,'stat',side_effect=AssertionError('NO_FILESYSTEM_FOR_INVALID_PATH')),patch.object(Path,'lstat',side_effect=AssertionError('NO_FILESYSTEM_FOR_INVALID_PATH')):
    with self.assertRaises(RuntimeError):list(ResearchArchive.read_existing(candidate,'fixture'))
if __name__=='__main__':unittest.main()

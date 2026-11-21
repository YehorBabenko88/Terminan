import unittest, sqlite3, tempfile
from pathlib import Path
from contextlib import closing
from terminan.paper_ledger import PaperReplayLedger
from test_historical_fill_migration import ROWS, source_receipt

class HistoricalSchemaMigrationTests(unittest.TestCase):
    def test_explicit_archive_schema_migration_preserves_backup_digest_and_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            file=Path(folder)/'source.sqlite'; backup=Path(folder)/'before.sqlite'
            ledger=PaperReplayLedger(file)
            receipt=source_receipt(ROWS)
            ledger.import_historical_fills('snapshot',ROWS,receipt)
            with closing(sqlite3.connect(file)) as db, db:
                db.execute('ALTER TABLE historical_fill_archives RENAME TO meta_fill_archives')
                db.execute('ALTER TABLE historical_fill_rows RENAME TO meta_fill_rows')
                with closing(sqlite3.connect(backup)) as target:db.backup(target)
            changed=ledger.migrate_historical_archive_schema()
            self.assertEqual(changed,True)
            self.assertEqual(list(ledger.restore_historical_fills('snapshot')),ROWS)
            self.assertEqual(ledger.migrate_historical_archive_schema(),False)
            with closing(sqlite3.connect(backup)) as db:
                self.assertEqual(db.execute('SELECT row_count,sha256 FROM meta_fill_archives').fetchone(),(2,receipt['sha256']))
            with closing(sqlite3.connect(file)) as db:
                self.assertEqual(db.execute("SELECT name FROM sqlite_schema WHERE name LIKE 'meta_fill_%'").fetchall(),[])

    def test_ambiguous_old_and_new_archive_names_refuse_without_removal(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger=PaperReplayLedger(Path(folder)/'archive.sqlite')
            with closing(sqlite3.connect(ledger.path)) as db, db:
                db.execute('CREATE TABLE meta_fill_archives(source_id TEXT, row_count INTEGER, sha256 TEXT)')
                db.execute('CREATE TABLE historical_fill_archives(source_id TEXT, row_count INTEGER, sha256 TEXT)')
            with self.assertRaises(ValueError):ledger.migrate_historical_archive_schema()
            with closing(sqlite3.connect(ledger.path)) as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM sqlite_schema WHERE name IN ('meta_fill_archives','historical_fill_archives')").fetchone()[0],2)

    def test_retired_archive_api_is_removed(self):
        self.assertFalse(hasattr(PaperReplayLedger,'import_meta_fills'))
        self.assertFalse(hasattr(PaperReplayLedger,'restore_meta_fills'))

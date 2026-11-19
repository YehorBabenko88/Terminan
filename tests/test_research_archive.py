from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from terminan.paper_ledger import PaperReplayLedger, ReplayConflict
from terminan.research_archive import ResearchArchive, research_result_receipt


PUBLISHED = "research_results"
STAGED = "staged_research_results"
ROWS = {
    PUBLISHED: [
        ("run-1", "BTCUSDT", "a", "1", 123.5,
         '{"fold": 2, "net": 1.20, "variant": "BASE"}', None, 0, 0),
        ("run-2", "BTCUSDT", "a", "1", 124.5, '{"variant": "ML"}', "job", 7, 2),
    ],
    STAGED: [
        ("stage-1", "run-3", "BTCUSDT", "a", "1", 125.5,
         '{"fold": 3, "variant": "ML", "legacy_metric": NaN}', "job", 8, 3),
    ],
}


class ResearchArchiveTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "receipts.sqlite3"

    def archive(self, path=None):
        return ResearchArchive(PaperReplayLedger(path or self.path))

    def test_archive_retry_and_backup_preserve_metrics_and_old_leases(self):
        receipt = research_result_receipt("a" * 64, ROWS)
        self.assertEqual(self.archive().import_snapshot("source-1", ROWS, receipt), receipt)
        self.assertEqual(self.archive().import_snapshot("source-1", ROWS, receipt), receipt)
        different = research_result_receipt("b" * 64, ROWS)
        with self.assertRaises(ReplayConflict):
            self.archive().import_snapshot("source-1", ROWS, different)
        backup_path = self.path.with_name("backup.sqlite3")
        with closing(sqlite3.connect(self.path)) as source, \
                closing(sqlite3.connect(backup_path)) as backup:
            source.backup(backup)
            self.assertEqual(backup.execute("PRAGMA integrity_check").fetchone(), ("ok",))
        restored = list(self.archive(backup_path).read_snapshot("source-1"))
        self.assertEqual(restored, [
            (PUBLISHED, "LEGACY_UNFENCED", ROWS[PUBLISHED][0]),
            (PUBLISHED, "PUBLISHED_UNVERIFIED", ROWS[PUBLISHED][1]),
            (STAGED, "STAGED_UNVERIFIED", ROWS[STAGED][0]),
        ])
        self.assertEqual(receipt, research_result_receipt("a" * 64, {
            table: [row for name, _, row in restored if name == table]
            for table in (PUBLISHED, STAGED)
        }))

    def test_failure_in_second_table_rolls_back_both_tables(self):
        receipt = research_result_receipt("a" * 64, ROWS)
        with self.assertRaises(ValueError):
            self.archive().import_snapshot("source-1", dict(ROWS, **{STAGED: []}), receipt)
        with self.assertRaises(KeyError):
            next(self.archive().read_snapshot("source-1"))
        self.archive().import_snapshot("source-1", ROWS, receipt)

    def test_reject_duplicate_or_unsorted_native_keys(self):
        for entries in ([ROWS[PUBLISHED][0]] * 2, list(reversed(ROWS[PUBLISHED]))):
            with self.assertRaises(ValueError):
                research_result_receipt("a" * 64, dict(ROWS, **{PUBLISHED: entries}))

    def test_corrupt_stage_blocks_all_readback(self):
        receipt = research_result_receipt("a" * 64, ROWS)
        self.archive().import_snapshot("source-1", ROWS, receipt)
        with closing(sqlite3.connect(self.path)) as database, database:
            database.execute("DELETE FROM archived_research_rows_v1 WHERE table_name = ?", (STAGED,))
        with self.assertRaisesRegex(RuntimeError, "integrity"):
            next(self.archive().read_snapshot("source-1"))

    def test_historical_sqlite_infinities_remain_archive_only(self):
        published = [
            (*row[:4], stamp, *row[5:])
            for row, stamp in zip(ROWS[PUBLISHED], (float("inf"), float("-inf")))
        ]
        tables = dict(ROWS, **{PUBLISHED: published})
        receipt = research_result_receipt("a" * 64, tables)
        self.archive().import_snapshot("source-1", tables, receipt)
        restored = [row for table, _, row in self.archive().read_snapshot("source-1")
                    if table == PUBLISHED]
        self.assertEqual(restored, published)

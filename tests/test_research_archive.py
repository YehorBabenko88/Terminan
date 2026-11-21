from contextlib import closing
from hashlib import sha256
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

    def test_six_column_backup_is_read_only_and_round_trips_without_stage(self):
        legacy = self.path.with_name("legacy.sqlite3")
        columns = "run_id,symbol,strategy_id,strategy_version,created_at,metrics"
        with closing(sqlite3.connect(legacy)) as database, database:
            database.execute("CREATE TABLE research_results "
                             "(run_id TEXT,symbol TEXT,strategy_id TEXT,strategy_version TEXT,"
                             "created_at REAL,metrics TEXT)")
            database.executemany("INSERT INTO research_results VALUES (?,?,?,?,?,?)",
                                 [row[:6] for row in ROWS[PUBLISHED]])
        original = legacy.read_bytes()
        source_sha = sha256(original).hexdigest()
        with closing(sqlite3.connect(legacy.as_uri() + "?mode=ro&immutable=1", uri=True)) as database:
            projected = list(database.execute(
                f"SELECT {columns} FROM research_results ORDER BY run_id,symbol,strategy_id,strategy_version"))
        tables = {PUBLISHED: projected}
        receipt = research_result_receipt(source_sha, tables)
        self.assertEqual(set(receipt["tables"]), {PUBLISHED})
        self.archive().import_snapshot("six", tables, receipt)
        self.assertEqual(self.archive().import_snapshot("six", tables, receipt), receipt)
        self.assertEqual(list(self.archive().read_snapshot("six")),
                         [(PUBLISHED, "LEGACY_UNFENCED", row) for row in projected])
        self.assertEqual(legacy.read_bytes(), original)
        self.assertEqual(list(legacy.parent.glob("legacy.sqlite3*")), [legacy])

    def test_six_column_receipt_never_accepts_padded_or_staged_rows(self):
        tables = {PUBLISHED: [ROWS[PUBLISHED][0][:6]]}
        receipt = research_result_receipt("a" * 64, tables)
        for incorrect in ({PUBLISHED: ROWS[PUBLISHED]}, dict(tables, **{STAGED: []})):
            with self.assertRaises(ValueError):
                self.archive().import_snapshot("six", incorrect, receipt)

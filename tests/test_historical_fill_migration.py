import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from hashlib import sha256
from pathlib import Path

from terminan.paper_ledger import PaperReplayLedger, ReplayConflict


ROWS = [
    [1, "BTCUSDT", "short", "102.0000", "100.00", "target",
     "1.23", "0.10", "1.13", "2026-11-19T00:00:00.123456+00:00"],
    [7, "BTCUSDT", "long", "98.00", "95.00", "stop",
     "-3.0", "0.20", "-3.20", "2026-11-19T00:01:00.000000+00:00"],
]


def source_receipt(rows):
    digest = sha256(b"meta.persisted-state.digest.v1\0paper_fills\0")
    for row in rows:
        raw = json.dumps(row, ensure_ascii=True, separators=(",", ":")).encode()
        digest.update(len(raw).to_bytes(4, "big"))
        digest.update(raw)
    return {
        "schema": "meta.persisted-state.digest.v1",
        "table": "paper_fills",
        "row_count": len(rows),
        "sha256": digest.hexdigest(),
        "source_status": "UNVERIFIED_LOCAL_READBACK",
        "execution_authority": False,
        "trading_authorized": False,
    }


class HistoricalFillMigrationTests(unittest.TestCase):
    def setUp(self):
        case = tempfile.TemporaryDirectory()
        self.addCleanup(case.cleanup)
        self.path = Path(case.name) / "term.db"
        self.ledger = PaperReplayLedger(self.path)

    def test_immutable_source_round_trip_and_retry(self):
        receipt = source_receipt(ROWS)
        # Pinned Meta #81 c25fd2c persisted_state_receipt on the same SQL rows.
        self.assertEqual(receipt["sha256"],
                         "5ecbdef3159f295330f024b6cbc7982acdb07aea61522d67c393104ca6d62770")
        self.assertEqual(self.ledger.import_historical_fills("legacy-a", iter(ROWS), receipt),
                         receipt)
        reopened = PaperReplayLedger(self.path)
        self.assertEqual(list(reopened.restore_historical_fills("legacy-a")), ROWS)
        self.assertEqual(reopened.import_historical_fills("legacy-a", iter(ROWS), receipt),
                         receipt)
        changed = [ROWS[0], [8, *ROWS[1][1:]]]
        with self.assertRaises(ReplayConflict):
            self.ledger.import_historical_fills("legacy-a", changed, source_receipt(changed))
        self.assertEqual(list(reopened.restore_historical_fills("legacy-a")), ROWS)

    def test_missing_or_invalid_row_rolls_back_whole_import(self):
        for incomplete in (ROWS[:1], [ROWS[0], [*ROWS[1][:-1], "2026-11-19"]]):
            with self.subTest(rows=incomplete):
                with self.assertRaises(ValueError):
                    self.ledger.import_historical_fills("legacy-a", incomplete, source_receipt(ROWS))
                with self.assertRaises(KeyError):
                    list(self.ledger.restore_historical_fills("legacy-a"))
        self.ledger.import_historical_fills("legacy-a", ROWS, source_receipt(ROWS))
        self.assertEqual(list(self.ledger.restore_historical_fills("legacy-a")), ROWS)

    def test_corrupt_archive_emits_no_rows(self):
        self.ledger.import_historical_fills("legacy-a", ROWS, source_receipt(ROWS))
        with closing(sqlite3.connect(self.path)) as database, database:
            database.execute("DELETE FROM historical_fill_rows WHERE fill_id = 7")
        with self.assertRaisesRegex(RuntimeError, "integrity"):
            next(self.ledger.restore_historical_fills("legacy-a"))

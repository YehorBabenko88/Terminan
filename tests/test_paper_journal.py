import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, contextmanager
from hashlib import sha256
from pathlib import Path
from threading import Barrier
from unittest.mock import patch

from terminan.paper_journal import PaperJournal
from terminan.paper_ledger import PaperReplayLedger, ReplayConflict


def event(sequence, kind, time, **values):
    return {
        "schema": "terminan.paper.event.v1", "sequence": sequence,
        "kind": kind, "event_time": f"2026-11-19T{time}+00:00", **values,
    }


ENABLE = event(1, "enabled", "00:00:00", enabled=True)
MINUTE = event(2, "closed_minute", "00:00:00", poc="100", complete=True)
ENTRY = event(3, "trade", "00:01:01", price="102")
EXIT = event(4, "trade", "00:01:02", price="100")


class PaperJournalTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "receipts.db"

    def open(self):
        return PaperJournal(PaperReplayLedger(self.path), "grid-fixture", "run1", "BTCUSDT")

    def test_restart_recovers_position_and_exact_fill_ack(self):
        journal = self.open()
        for item in (ENABLE, MINUTE, ENTRY):
            self.assertIsNone(journal.submit(item)["fill"])
        journal = self.open()
        ack = journal.submit(EXIT)
        self.assertEqual(ack["checkpoint"], 4)
        self.assertEqual(ack["fill_id"], ["grid-fixture", "run1", 4])
        self.assertEqual(ack["event_time"], EXIT["event_time"])
        self.assertEqual(ack["fill"]["side"], "short")
        self.assertEqual(ack["fill"]["reason"], "target")
        self.assertEqual(ack["fill"]["exit_time"], EXIT["event_time"])
        self.assertFalse(ack["trading_authorized"])
        restarted = self.open()
        self.assertEqual(restarted.submit(EXIT), ack)
        self.assertEqual(list(restarted.read_fills()), [ack])
        with self.assertRaises(ReplayConflict):
            restarted.submit(dict(EXIT, price="101"))

    def test_failure_after_fill_computation_rolls_back_ack_and_checkpoint(self):
        journal = self.open()
        for item in (ENABLE, MINUTE, ENTRY):
            journal.submit(item)
        with patch.object(journal, "_ack", side_effect=OSError("injected disk failure")):
            with self.assertRaises(OSError):
                journal.submit(EXIT)
        self.assertEqual(list(journal.read_fills()), [])
        with self.assertRaises(RuntimeError):
            journal.submit(EXIT)
        restarted = self.open()
        ack = restarted.submit(EXIT)
        self.assertEqual(list(restarted.read_fills()), [ack])

    def test_missing_event_cannot_advance_and_disabled_trade_is_durable(self):
        journal = self.open()
        with self.assertRaises(ReplayConflict):
            journal.submit(MINUTE)
        disabled_trade = event(1, "trade", "00:01:01", price="102")
        self.assertIsNone(journal.submit(disabled_trade)["fill"])
        self.assertEqual(self.open().submit(disabled_trade)["checkpoint"], 1)
        self.assertEqual(list(self.open().read_fills()), [])

    def test_process_exit_before_commit_or_after_commit_before_ack(self):
        child = """
import json
import os
import sys
from contextlib import contextmanager
from terminan.paper_journal import PaperJournal
from terminan.paper_ledger import PaperReplayLedger

ledger = PaperReplayLedger(sys.argv[1])
journal = PaperJournal(ledger, "grid-fixture", "run1", "BTCUSDT")
original = ledger._paper_event_transaction
@contextmanager
def interrupted(*, write):
    with original(write=write) as db:
        yield db
        if sys.argv[3] == "before":
            os._exit(42)
    os._exit(42)
ledger._paper_event_transaction = interrupted
journal.submit(json.loads(sys.argv[2]))
"""
        for timing in ("before", "after"):
            with self.subTest(timing=timing):
                self.path = self.path.with_name(timing + ".db")
                journal = self.open()
                for item in (ENABLE, MINUTE, ENTRY):
                    journal.submit(item)
                proc = subprocess.run(
                    [sys.executable, "-c", child, str(self.path), json.dumps(EXIT), timing],
                    timeout=15, check=False)
                self.assertEqual(proc.returncode, 42)
                restored = self.open()
                initial = list(restored.read_fills())
                self.assertEqual(len(initial), int(timing == "after"))
                ack = restored.submit(EXIT)
                if initial:
                    self.assertEqual(initial, [ack])
                self.assertEqual(ack["checkpoint"], 4)
                self.assertEqual(list(self.open().read_fills()), [ack])

    def test_stale_writer_and_backup(self):
        first = self.open()
        stale = self.open()
        for item in (ENABLE, MINUTE, ENTRY, EXIT):
            ack = first.submit(item)
        self.assertEqual(stale.submit(EXIT), ack)
        with self.assertRaisesRegex(ReplayConflict, "stale writer"):
            stale.submit(event(5, "gap", "00:01:03"))
        backup_path = self.path.with_name("backup.db")
        with closing(sqlite3.connect(self.path)) as source, \
                closing(sqlite3.connect(backup_path)) as backup:
            source.backup(backup)
        restored = PaperJournal(PaperReplayLedger(backup_path), "grid-fixture", "run1", "BTCUSDT")
        self.assertEqual(list(restored.read_fills()), [ack])
        self.assertEqual(restored.submit(EXIT), ack)

    def test_missing_last_event_is_not_silently_replayed(self):
        journal = self.open()
        journal.submit(ENABLE)
        with closing(sqlite3.connect(self.path)) as database, database:
            database.execute("DELETE FROM paper_events_v1")
        with self.assertRaisesRegex(RuntimeError, "checkpoint gap"):
            self.open()

    def test_ordered_fill_digest_matches_acknowledged_results(self):
        journal = self.open()
        items = [ENABLE, MINUTE, ENTRY, EXIT,
                 event(5, "closed_minute", "00:01:00", poc="100", complete=True),
                 event(6, "trade", "00:02:01", price="98"),
                 event(7, "trade", "00:02:02", price="100")]
        acks = [journal.submit(item) for item in items]
        expected = [ack for ack in acks if ack["fill"] is not None]
        stored = list(self.open().read_fills())
        self.assertEqual([ack["checkpoint"] for ack in stored], [4, 7])
        self.assertEqual(sha256(json.dumps(stored, sort_keys=True).encode()).digest(),
                         sha256(json.dumps(expected, sort_keys=True).encode()).digest())

    def test_restart_rejects_event_before_minute_availability(self):
        journal = self.open()
        journal.submit(ENABLE)
        journal.submit(MINUTE)
        restarted = self.open()
        with self.assertRaisesRegex(ValueError, "event time regressed"):
            restarted.submit(event(3, "gap", "00:00:59"))
        self.assertEqual(restarted.submit(ENTRY)["checkpoint"], 3)

    def test_committed_fill_can_be_reconciled_after_ack_is_lost(self):
        journal = self.open()
        self.assertIsNone(journal.read_checkpoint())
        for item in (ENABLE, MINUTE, ENTRY):
            journal.submit(item)
        transaction = journal._ledger._paper_event_transaction

        @contextmanager
        def disconnect_after_commit(*, write):
            with transaction(write=write) as database:
                yield database
            raise OSError("simulated disconnect after commit")

        with patch.object(journal._ledger, "_paper_event_transaction", disconnect_after_commit):
            with self.assertRaises(OSError):
                journal.submit(EXIT)

        restarted = self.open()
        saved = restarted.read_checkpoint()
        self.assertEqual(saved["checkpoint"], 4)
        self.assertEqual(saved["fill_id"], ["grid-fixture", "run1", 4])
        self.assertEqual(restarted.submit(EXIT), saved)
        self.assertEqual(list(restarted.read_fills()), [saved])

    def test_two_writers_cannot_commit_different_events_at_one_sequence(self):
        original = self.open()
        for item in (ENABLE, MINUTE, ENTRY):
            original.submit(item)
        barrier = Barrier(2)

        def submit(journal, candidate):
            barrier.wait(timeout=5)
            try:
                return journal.submit(candidate)
            except ReplayConflict:
                return None

        with ThreadPoolExecutor(max_workers=2) as pool:
            attempts = [pool.submit(submit, self.open(), candidate)
                        for candidate in (EXIT, dict(EXIT, price="99"))]
            committed = [result for attempt in attempts if (result := attempt.result()) is not None]
        self.assertEqual(len(committed), 1)
        self.assertEqual(list(self.open().read_fills()), committed)

    def test_canonical_retry_and_corrupt_input_refusal(self):
        journal = self.open()
        for item in (ENABLE, MINUTE, ENTRY, EXIT):
            ack = journal.submit(item)
        differently_serialized = json.dumps(dict(reversed(list(EXIT.items()))), indent=2)
        self.assertEqual(journal.submit(json.loads(differently_serialized)), ack)
        with self.assertRaises(ReplayConflict):
            journal.submit(dict(EXIT, price="100.0"))
        with closing(sqlite3.connect(self.path)) as database, database:
            database.execute("UPDATE paper_events_v1 SET event = ? WHERE sequence = 4",
                             (json.dumps(dict(EXIT, price="90")).encode(),))
        with self.assertRaisesRegex(RuntimeError, "acknowledgement integrity"):
            journal.read_checkpoint()
        with self.assertRaisesRegex(RuntimeError, "acknowledgement integrity"):
            list(journal.read_fills())
        with self.assertRaisesRegex(RuntimeError, "acknowledgement integrity"):
            self.open()

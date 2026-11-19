import copy
import http.client
import json
import os
import sqlite3
import sys
import tempfile
import types
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Barrier, Thread
from unittest.mock import patch

from terminan.paper import replay_paper
from terminan.paper_ledger import PaperReplayLedger, ReplayConflict
from terminan.server import Handler
from test_paper import mock_math, offline_request


class PaperReplayLedgerTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "receipts.sqlite3"
        self.env = patch.dict(os.environ, {"TERMINAN_PAPER_LEDGER": str(self.path)})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.request = offline_request()

    def test_opt_in_replay_survives_reopen_and_math_unavailability(self):
        def unavailable(_):
            self.fail("a stored receipt should not invoke Math again")

        first = replay_paper(self.request, compute=mock_math)
        self.assertEqual(first["status"], "OFFLINE_UNATTESTED")
        self.assertFalse(first["trading_authorized"])
        self.assertEqual(first, PaperReplayLedger(self.path).read(
            first["run_id"], first["request_sha256"]))
        self.assertEqual(first, replay_paper(self.request, compute=unavailable))

    def test_changed_request_cannot_overwrite_run(self):
        original = replay_paper(self.request, compute=mock_math)
        different = copy.deepcopy(self.request)
        different["parameters"]["notional"] = "200"
        with self.assertRaises(ReplayConflict):
            replay_paper(different, compute=mock_math)
        self.assertEqual(original, replay_paper(self.request, compute=mock_math))

    def test_failed_replay_leaves_run_id_available(self):
        with self.assertRaises(ValueError):
            invalid = dict(self.request, events=[{"kind": "unknown"}])
            replay_paper(invalid, compute=mock_math)
        self.assertEqual(len(replay_paper(self.request, compute=mock_math)["fills"]), 1)

    def test_concurrent_different_requests_leave_only_winner(self):
        barrier = Barrier(2)
        different = copy.deepcopy(self.request)
        different["parameters"]["notional"] = "200"

        def compute(request):
            barrier.wait(timeout=5)
            return mock_math(request)

        def attempt(request):
            try:
                return replay_paper(request, compute=compute)
            except ReplayConflict:
                return None

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, (self.request, different)))
        receipts = [result for result in results if result is not None]
        self.assertEqual(len(receipts), 1)
        receipt = receipts[0]
        self.assertEqual(receipt, PaperReplayLedger(self.path).read(
            receipt["run_id"], receipt["request_sha256"]))

    def test_modified_result_is_rejected(self):
        original = replay_paper(self.request, compute=mock_math)
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute("UPDATE paper_replay_receipts SET receipt = ?",
                               (json.dumps(dict(original, status="LIVE")),))
        with self.assertRaisesRegex(RuntimeError, "receipt integrity"):
            replay_paper(self.request, compute=mock_math)

    def test_existing_foreign_database_is_left_untouched(self):
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute("CREATE TABLE legacy_history(value TEXT)")
            connection.execute("INSERT INTO legacy_history VALUES ('keep')")
        with self.assertRaisesRegex(RuntimeError, "dedicated"):
            replay_paper(self.request, compute=mock_math)
        with closing(sqlite3.connect(self.path)) as connection:
            self.assertEqual(connection.execute(
                "SELECT name FROM sqlite_schema WHERE type='table'"
            ).fetchall(), [("legacy_history",)])
            self.assertEqual(connection.execute(
                "SELECT value FROM legacy_history"
            ).fetchall(), [("keep",)])

    def test_http_replay_returns_same_receipt_after_server_restart(self):
        def post(compute, request):
            module = types.ModuleType("market_compute_api")
            module.compute_batch = compute
            with patch.dict(sys.modules, {"market_compute_api": module}), \
                    patch.object(Handler, "log_message"):
                with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
                    worker = Thread(target=server.serve_forever)
                    worker.start()
                    try:
                        with closing(http.client.HTTPConnection(
                            "127.0.0.1", server.server_port, timeout=5
                        )) as client:
                            client.request("POST", "/api/paper/replay",
                                           body=json.dumps(request),
                                           headers={"Content-Type": "application/json"})
                            with client.getresponse() as response:
                                return response.status, json.load(response)
                    finally:
                        server.shutdown()
                        worker.join()

        def unavailable(_):
            self.fail("retry should return the committed receipt")

        status, first = post(mock_math, self.request)
        self.assertEqual(status, 200)
        self.assertEqual(len(first["fills"]), 1)
        self.assertEqual(post(unavailable, self.request), (200, first))
        changed = dict(self.request, parameters={"notional": "200"})
        self.assertEqual(post(unavailable, changed)[0], 400)

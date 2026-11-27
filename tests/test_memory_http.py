import copy
import json
import os
import sqlite3
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen
from unittest.mock import patch

from terminan.server import Handler


class MemoryHTTPTest(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.status = 200
        self.record = {
            "schema": "math.scientific-memory.record.v1",
            "id": "a" * 64,
            "symbol": "BTCUSDT",
            "dataset": {"id": "c" * 64, "source": "fixture"},
            "status": "reproduced",
            "input_hash": "b" * 64,
            "metrics": {"price": "9007199254740993.000100", "result": None},
        }
        self.payload = {
            "schema": "math.scientific-memory.list.v1",
            "symbol": "BTCUSDT",
            "records": [self.record],
        }

        class FixtureHandler(BaseHTTPRequestHandler):
            def do_GET(handler):
                self.requests.append(handler.path)
                handler.send_response(self.status)
                handler.end_headers()
                handler.wfile.write(json.dumps(self.payload).encode())

            def log_message(self, *_):
                pass

        class TerminalHandler(Handler):
            def log_message(self, *_):
                pass

        fixture_url = self.run_server(FixtureHandler)
        self.terminal_url = self.run_server(TerminalHandler)
        env = patch.dict(os.environ, {"TERMINAN_MEMORY_URL": fixture_url, "TERMINAN_RESULTS_DB": ""})
        env.start()
        self.addCleanup(env.stop)

    def run_server(self, handler):
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.addCleanup(server.server_close)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        return f"http://127.0.0.1:{server.server_port}"

    def get(self, route, status=200):
        try:
            response = urlopen(self.terminal_url + route, timeout=5)
        except HTTPError as exc:
            response = exc
        with response:
            self.assertEqual(response.status, status)
            return json.load(response)

    def test_research_returns_upstream_records_without_alteration(self):
        self.assertEqual(self.get("/api/research?symbol=BTCUSDT"), [self.record])
        self.assertEqual(self.requests, ["/v1/scientific-memory?symbol=BTCUSDT&limit=50"])
        self.assertTrue(self.get("/api/status")["research"])

    def test_valid_empty_result_and_failed_upstream(self):
        self.payload["records"] = []
        self.assertEqual(self.get("/api/research"), [])
        self.status = 503
        self.assertEqual(self.get("/api/research", 503), {"error": "source unavailable"})

    def test_rejects_wrong_contract_scope_identity_and_count(self):
        payload = self.payload
        for field, value in [
            ("schema", "unexpected"), ("symbol", "ETHUSDT"), ("records", {}),
            ("records", [self.record] * 51),
        ]:
            with self.subTest(field=field, value_type=type(value)):
                self.payload = {**payload, field: value}
                self.get("/api/research", 503)
        for field, value in [
            ("schema", "unexpected"), ("id", 123), ("id", "short"),
            ("symbol", "ETHUSDT"), ("dataset", {"id": ""}), ("dataset", {"id": 123}),
            ("status", []), ("status", "unknown"), ("input_hash", None), ("input_hash", "H" * 64),
        ]:
            with self.subTest(field=field, value=value):
                self.payload = copy.deepcopy(payload)
                self.payload["records"][0][field] = value
                self.get("/api/research", 503)

    def test_non_loopback_source_is_rejected(self):
        with patch.dict(os.environ, {"TERMINAN_MEMORY_URL": "http://192.0.2.1"}):
            self.get("/api/research", 503)
        self.assertEqual(self.requests, [])

    def test_invalid_symbol_does_not_contact_upstream(self):
        self.get("/api/research?symbol=invalid!", 400)
        self.assertEqual(self.requests, [])

    def test_legacy_sqlite_read_remains_available_without_memory_url(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.sqlite"
            connection = sqlite3.connect(path)
            with connection:
                connection.execute("CREATE TABLE research_results (symbol, run_id, strategy_id, strategy_version, created_at, metrics)")
                connection.execute("INSERT INTO research_results VALUES (?, ?, ?, ?, ?, ?)",
                                   ("BTCUSDT", "run", "strategy", "1", "2026-11-27", "{}"))
            connection.close()
            with patch.dict(os.environ, {"TERMINAN_RESULTS_DB": str(path)}):
                del os.environ["TERMINAN_MEMORY_URL"]
                self.assertEqual(self.get("/api/research"), [{
                    "run_id": "run", "strategy": "strategy", "version": "1",
                    "created_at": "2026-11-27", "metrics": {},
                }])
                self.assertTrue(self.get("/api/status")["research"])
        self.assertEqual(self.requests, [])

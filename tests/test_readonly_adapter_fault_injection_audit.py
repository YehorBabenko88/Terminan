"""Deterministic read-only adapter fault injection. No live databases."""
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from terminan import data
from terminan.source_views import grid_market_view


class ReadOnlyAdapterFaultInjection(unittest.TestCase):
    def test_sqlite_missing_file_is_unavailable(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.dict(os.environ, {"TERMINAN_STRATTESTER_DB": str(Path(d) / "missing.sqlite")}):
                self.assertIsNone(data.sqlite_ro("TERMINAN_STRATTESTER_DB"))
                self.assertEqual(data.candles("BTCUSDT"), [])

    def test_sqlite_connection_is_query_only(self):
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "fixture.sqlite"
            with sqlite3.connect(db) as conn:
                conn.execute("CREATE TABLE candles(symbol TEXT, timeframe TEXT, open_time INTEGER, open REAL, high REAL, low REAL, close REAL, volume REAL)")
            with patch.dict(os.environ, {"TERMINAN_STRATTESTER_DB": str(db)}):
                conn = data.sqlite_ro("TERMINAN_STRATTESTER_DB")
                try:
                    self.assertEqual(conn.execute("PRAGMA query_only").fetchone()[0], 0)
                    with self.assertRaises(sqlite3.OperationalError):
                        conn.execute("CREATE TABLE unauthorized_write (id INTEGER)")
                finally:
                    conn.close()

    def test_sqlite_malformed_schema_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "bad.sqlite"
            with sqlite3.connect(db) as conn:
                conn.execute("CREATE TABLE candles (symbol TEXT)")
            with patch.dict(os.environ, {"TERMINAN_STRATTESTER_DB": str(db)}):
                with self.assertRaises(sqlite3.OperationalError):
                    data.candles("BTCUSDT")

    def test_pg_unconfigured_does_not_connect(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(data.grid_query("SELECT 1", ()), [])
            self.assertEqual(grid_market_view("BTCUSDT")["l2"]["state"], "UNAVAILABLE")

    def test_pg_connect_timeout_propagates(self):
        class FakePsycopg:
            @staticmethod
            def connect(*args, **kwargs):
                raise TimeoutError("synthetic connection timeout")
        with patch.dict(os.environ, {"TERMINAN_GRID_DSN": "synthetic-only"}):
            with patch.dict("sys.modules", {"psycopg": FakePsycopg}):
                with self.assertRaisesRegex(TimeoutError, "synthetic connection timeout"):
                    data.grid_query("SELECT 1", ())

    def test_pg_connection_options_are_read_only_and_bounded(self):
        seen = {}
        class FakePsycopg:
            @staticmethod
            def connect(dsn, **kwargs):
                seen.update(kwargs)
                raise TimeoutError("synthetic")
        with patch.dict(os.environ, {"TERMINAN_GRID_DSN": "synthetic-only"}):
            with patch.dict("sys.modules", {"psycopg": FakePsycopg}):
                with self.assertRaises(TimeoutError):
                    data.grid_query("SELECT 1", ())
        self.assertEqual(seen["connect_timeout"], 3)
        self.assertIn("default_transaction_read_only=on", seen["options"])
        self.assertIn("statement_timeout=3000", seen["options"])


if __name__ == "__main__":
    unittest.main()

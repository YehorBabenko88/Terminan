"""Pinned, offline, non-invasive cross-repository integration contract checks.

These tests exercise the Terminan boundary only. They DO NOT establish live
Grid/Strattester schema compatibility or physical Windows acceptance.
"""
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from terminan import data

PINS = {
    "Terminan": "fee79f4b15fc1f9efcff9ca12c403688b0026260",
    "bybit-cluster-grid": "d537d525296ef34f727996e240ae6c60102c6082",
    "strattester": "37ff7e9d12a4d2dccd788fc493c28557dbe8bcea",
}


class PinnedReadOnlyBoundaryTests(unittest.TestCase):
    def test_pins_are_full_immutable_commit_ids(self):
        self.assertEqual(set(PINS), {"Terminan", "bybit-cluster-grid", "strattester"})
        for sha in PINS.values():
            self.assertEqual(len(sha), 40)
            self.assertTrue(all(c in "0123456789abcdef" for c in sha))

    def test_symbol_and_timeframe_fail_closed(self):
        for symbol in ("BTC/USDT", "btcUSDT", "BTCUSDT;DROP", "", "A" * 31):
            with self.subTest(symbol=symbol), self.assertRaises(ValueError):
                data.validate(symbol)
        for tf in ("1m;DROP", "0m", "1M", ""):
            with self.subTest(timeframe=tf), self.assertRaises(ValueError):
                data.validate("BTCUSDT", tf)

    def test_absent_sources_return_no_synthetic_data(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(data.candles("BTCUSDT"), [])
            self.assertEqual(data.research("BTCUSDT"), [])
            self.assertEqual(data.grid_candles("BTCUSDT"), [])
            self.assertEqual(data.footprint("BTCUSDT"), [])

    def test_sqlite_is_read_only_even_with_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.sqlite"
            with sqlite3.connect(path) as con:
                con.execute("CREATE TABLE candles(symbol TEXT, timeframe TEXT, open_time INTEGER, open REAL, high REAL, low REAL, close REAL, volume REAL)")
                con.execute("INSERT INTO candles VALUES ('BTCUSDT','1m',1000,1,2,1,2,3)")
            with patch.dict(os.environ, {"TERMINAN_STRATTESTER_DB": str(path)}):
                self.assertEqual(len(data.candles("BTCUSDT")), 1)
                con = data.sqlite_ro("TERMINAN_STRATTESTER_DB")
                try:
                    with self.assertRaises(sqlite3.OperationalError):
                        con.execute("INSERT INTO candles VALUES ('BTCUSDT','1m',2000,1,2,1,2,3)")
                finally:
                    con.close()
            with sqlite3.connect(path) as con:
                self.assertEqual(con.execute("SELECT COUNT(*) FROM candles").fetchone()[0], 1)

    def test_grid_query_uses_read_only_session_and_timeout(self):
        import inspect
        source = inspect.getsource(data.grid_query)
        self.assertIn("default_transaction_read_only=on", source)
        self.assertIn("statement_timeout=3000", source)
        self.assertIn("connect_timeout=3", source)

    def test_sqlite_missing_schema_fails_explicitly(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.sqlite"
            with sqlite3.connect(path) as con:
                con.execute("CREATE TABLE unrelated(value TEXT)")
            with patch.dict(os.environ, {"TERMINAN_STRATTESTER_DB": str(path)}):
                with self.assertRaises(sqlite3.OperationalError):
                    data.candles("BTCUSDT")

    def test_research_json_is_not_promoted_to_trading_authority(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.sqlite"
            with sqlite3.connect(path) as con:
                con.execute("CREATE TABLE research_results(symbol TEXT, run_id TEXT, strategy_id TEXT, strategy_version TEXT, created_at INTEGER, metrics TEXT)")
                con.execute("INSERT INTO research_results VALUES (?,?,?,?,?,?)",
                            ("BTCUSDT", "run-1", "strategy-1", "v1", 1000, json.dumps({"sharpe": 1.25})))
            with patch.dict(os.environ, {"TERMINAN_RESULTS_DB": str(path)}):
                result = data.research("BTCUSDT")
            self.assertEqual(result[0]["run_id"], "run-1")
            self.assertEqual(result[0]["metrics"], {"sharpe": 1.25})
            self.assertNotIn("execute", result[0])
            self.assertNotIn("order", result[0])

    def test_research_malformed_json_fails_explicitly(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad-results.sqlite"
            with sqlite3.connect(path) as con:
                con.execute("CREATE TABLE research_results(symbol TEXT, run_id TEXT, strategy_id TEXT, strategy_version TEXT, created_at INTEGER, metrics TEXT)")
                con.execute("INSERT INTO research_results VALUES (?,?,?,?,?,?)",
                            ("BTCUSDT", "run-1", "strategy-1", "v1", 1000, "{bad"))
            with patch.dict(os.environ, {"TERMINAN_RESULTS_DB": str(path)}):
                with self.assertRaises(ValueError):
                    data.research("BTCUSDT")

    def test_grid_candles_query_is_bounded_and_symbol_scoped(self):
        row = (60000, 10, 12, 9, 11, 5, 3, 2, 4, 10)
        with patch.object(data, "grid_query", return_value=[row]) as query:
            result = data.grid_candles("BTCUSDT", limit=999999)
        self.assertEqual(result[0]["t"], 60000.0)
        sql, params = query.call_args.args
        self.assertIn("WHERE symbol=%s", sql)
        self.assertIn("LIMIT %s", sql)
        self.assertEqual(params, ("BTCUSDT", 1000))

    def test_grid_footprint_query_is_bounded_and_symbol_scoped(self):
        row = (60000, 10, 5, 3, 2, 8)
        with patch.object(data, "grid_query", return_value=[row]) as query:
            result = data.footprint("BTCUSDT", limit=999999)
        self.assertEqual(result[0]["volume"], 8.0)
        sql, params = query.call_args.args
        self.assertIn("WHERE symbol=%s", sql)
        self.assertIn("LIMIT %s", sql)
        self.assertEqual(params, ("BTCUSDT", 1000))

    def test_grid_footprint_is_not_l2_feed(self):
        import inspect
        source = inspect.getsource(data.footprint)
        self.assertIn("footprint_1m", source)
        self.assertNotIn("orderbook", source.lower())


if __name__ == "__main__":
    unittest.main()

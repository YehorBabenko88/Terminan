"""HTTP contract for inert managed 5m/15m qualified chart."""
import http.client
import json
import threading
import time
import unittest
from unittest.mock import patch
from http.server import ThreadingHTTPServer

from terminan import data
from terminan.server import Handler


class QualifiedTimeframeHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.server.daemon_threads = True
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def setUp(self):
        self.old = data._private_market_data_client
        data._private_market_data_client = None
        self.addCleanup(setattr, data, "_private_market_data_client", self.old)

    def read(self, path):
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port, timeout=3)
        try:
            connection.request("GET", path)
            response = connection.getresponse()
            return response.status, json.loads(response.read().decode("utf-8"))
        finally:
            connection.close()

    def test_unmanaged_chart_is_inert_and_query_is_closed(self):
        base = "/api/market-data/qualified/timeframe"
        status, result = self.read(
            base + "?symbol=BTCUSDT&timeframe=15m&bars=5")
        self.assertEqual(status, 200)
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertEqual(result["rows"], [])
        self.assertFalse(result["execution_authority"])
        self.assertFalse(result["trading_authorized"])
        self.assertFalse(result["paper_admitted"])
        for query in (
                "symbol=BTCUSDT&timeframe=1m&bars=5",
                "symbol=BTCUSDT&timeframe=15m&bars=6",
                "symbol=BTCUSDT&timeframe=5m&bars=0",
                "symbol=BTCUSDT&timeframe=5m&bars=True",
                "symbol=BTCUSDT&timeframe=5m&bars=1&bars=2",
                "symbol=BTCUSDT&timeframe=5m&bars=1&debug=1",
                "symbol=BTCUSDT&timeframe=5m",
                "symbol=BTCUSDT&timeframe=5m&bars=",
                "symbol=BTCUSDT&timeframe=5m&bars=1&unexpected="):
            with self.subTest(query=query):
                bad_status, _ = self.read(base + "?" + query)
                self.assertEqual(bad_status, 400)


    def test_chart_query_budget_precedes_generic_url_decoding(self):
        """An overlong chart query must be rejected before parse_qs runs."""
        paths = (
            "/api/market-data/qualified/historical",
            "/api/market-data/qualified/timeframe",
        )
        for path in paths:
            for suffix in ("&extra=" + "A" * 2100, "#" + "B" * 2100):
                with self.subTest(path=path, suffix=suffix[:18]):
                    with patch("terminan.server.parse_qs",
                               side_effect=AssertionError("decoded too early")):
                        status, value = self.read(
                            path + "?symbol=BTCUSDT" + suffix)
                    self.assertEqual(status, 400)
                    self.assertEqual(value["error"],
                                     "BOUNDED_QUALIFIED_CHART_QUERY_REQUIRED")

    def test_ui_calls_source_exact_mtf_without_numeric_volume_rounding(self):
        """An exact 5m/15m UI must not reconstruct trades or 1m fallback."""
        from importlib.resources import files
        html = files("terminan").joinpath("index.html").read_text(
            encoding="utf-8")
        self.assertIn("'/api/market-data/qualified/timeframe?'", html)
        self.assertIn("if (timeframe === '1m')", html)
        self.assertIn("timeframe === '5m' || timeframe === '15m'", html)
        self.assertIn("last.volume_decimal", html)
        self.assertIn("last.delta_decimal", html)
        self.assertIn("source_numeric_precision", html)
        self.assertIn("DECIMAL", html.upper())
        self.assertIn("НЕ raw биржевые тики", html)
        self.assertIn("без fallback", html)
        self.assertNotIn("Number(last.volume_decimal)", html)
        self.assertNotIn("parseFloat(last.delta_decimal)", html)

    def test_historical_route_requires_explicit_asof_and_is_never_live(self):
        base = "/api/market-data/qualified/historical"
        boundary = ((int(time.time() * 1000) // 900000) - 4) * 900000
        asof = boundary + 60000
        valid = (f"symbol=BTCUSDT&timeframe=5m&bars=3"
                 f"&before_ms={boundary}&as_of_ms={asof}")
        status, result = self.read(base + "?" + valid)
        self.assertEqual(status, 200)
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertEqual(result["rows"], [])
        self.assertEqual(result["observation_mode"], "HISTORICAL_AS_OF_SOURCE_ONLY")
        self.assertEqual(result["live_freshness"], "NOT_APPLICABLE")
        self.assertFalse(result["paper_admitted"])
        self.assertFalse(result["trading_authorized"])
        self.assertFalse(result["execution_authority"])
        bad = (
            f"symbol=BTCUSDT&timeframe=5m&bars=3&before_ms={boundary}",
            f"symbol=BTCUSDT&timeframe=5m&bars=3&as_of_ms={asof}",
            valid + "&debug=1",
            valid + "&bars=4",
            valid.replace("bars=3", "bars=6"),
            valid.replace("timeframe=5m", "timeframe=1m"),
            valid.replace(f"before_ms={boundary}", "before_ms=0"),
            valid.replace(f"before_ms={boundary}", f"before_ms={boundary+1}"),
            valid.replace(f"as_of_ms={asof}", f"as_of_ms={boundary-60000}"),
            valid.replace(f"as_of_ms={asof}", f"as_of_ms={asof+31*86400000}"),
        )
        for query in bad:
            with self.subTest(query=query):
                reject, _ = self.read(base + "?" + query)
                self.assertEqual(reject, 400)


if __name__ == "__main__":
    unittest.main()

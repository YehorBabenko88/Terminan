"""HTTP contract for inert managed 5m/15m qualified chart."""
import http.client
import json
import threading
import unittest
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


if __name__ == "__main__":
    unittest.main()

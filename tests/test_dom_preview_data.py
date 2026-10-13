import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import urlopen

from terminan.dom_preview_data import PreviewBook
from terminan.server import Handler


class PreviewBookTests(unittest.TestCase):
    def test_viewport_is_engine_projection(self):
        result = PreviewBook().read(25, 5)
        self.assertEqual(result["source"], "SYNTHETIC_FIXTURE")
        self.assertIs(result["tradable"], False)
        self.assertEqual(result["status"], "LIVE")
        self.assertEqual(len(result["rows"]), 25)
        self.assertEqual(result["rows"][0]["price_ticks"], 100060)
        self.assertTrue(any(row["bid_lots"] > 0 for row in result["rows"]))
        self.assertTrue(any(row["ask_lots"] > 0 for row in result["rows"]))

    def test_invalid_parameters(self):
        with self.assertRaises(ValueError):
            PreviewBook().read(999, 1)
        with self.assertRaises(ValueError):
            PreviewBook().read(25, 0)

    def test_http_contract(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = "http://127.0.0.1:%d" % server.server_port
            with urlopen(base + "/api/dom-preview?rows=15&group=10", timeout=3) as response:
                data = json.load(response)
                self.assertEqual(data["source"], "SYNTHETIC_FIXTURE")
                self.assertEqual(len(data["rows"]), 15)
                self.assertEqual(response.headers["Cache-Control"], "no-store")
            with self.assertRaises(HTTPError) as error:
                urlopen(base + "/api/dom-preview?rows=50000", timeout=3)
            self.assertEqual(error.exception.code, 400)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()

"""Check synthetic preview is served locally and does not expose trading routes."""
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import urlopen
from terminan.server import Handler


class PreviewTests(unittest.TestCase):
    def test_preview_route(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with urlopen("http://127.0.0.1:%d/dom-preview" % server.server_port, timeout=3) as response:
                body = response.read().decode("utf-8")
                self.assertEqual(response.status, 200)
                self.assertIn("ДЕМОНСТРАЦИЯ", body)
                self.assertIn("SYNTHETIC", body)
                self.assertIn("no-store", response.headers["Cache-Control"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()

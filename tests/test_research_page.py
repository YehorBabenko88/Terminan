import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import urlopen
from terminan.server import Handler


class ResearchPageTests(unittest.TestCase):
    def test_page_served_with_no_store_and_provenance_warning(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with urlopen("http://127.0.0.1:%d/research" % server.server_port, timeout=3) as response:
                html = response.read().decode("utf-8")
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers["Cache-Control"], "no-store")
                self.assertIn("/api/source/strattester", html)
                self.assertIn("UNVERIFIED", html)
                self.assertIn("net_pnl", html)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()

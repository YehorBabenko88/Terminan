import json
import threading
import unittest
from urllib.request import urlopen
from terminan.server import Handler, ThreadingHTTPServer

class MathLabRouteTests(unittest.TestCase):
    def test_loopback_math_tab_and_closed_health(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            root = "http://127.0.0.1:%d" % server.server_port
            with urlopen(root + "/math", timeout=3) as response:
                page = response.read().decode("utf-8")
                self.assertEqual(response.status, 200)
                self.assertIn("Math Laboratory", page)
                self.assertIn("math.graph.preview.v1", page)
            with urlopen(root + "/api/math/health", timeout=3) as response:
                data = json.load(response)
                self.assertEqual(response.status, 200)
                self.assertEqual(data["state"], "NOT_CONNECTED")
                self.assertFalse(data["trading_authorized"])
                self.assertFalse(data["research_enabled"])
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=3)

if __name__ == "__main__":
    unittest.main()

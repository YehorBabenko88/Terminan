import threading
import unittest
from urllib.request import urlopen
from terminan.server import Handler, ThreadingHTTPServer

class HistoryOverlayRoutes(unittest.TestCase):
    def test_readonly_static_routes(self):
        server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
        worker=threading.Thread(target=server.serve_forever,daemon=True)
        worker.start()
        try:
            base="http://127.0.0.1:%d"%server.server_port
            with urlopen(base+"/history-overlay",timeout=3) as r:
                html=r.read().decode("utf-8")
                self.assertEqual(r.status,200)
                self.assertIn('id="chart"',html)
                self.assertIn('id="asof"',html)
                self.assertIn('NO_DATA',html)
            with urlopen(base+"/history-assets/overlay.js",timeout=3) as r:
                code=r.read().decode("utf-8")
                self.assertEqual(r.status,200)
                self.assertIn("available_at_ms<=asOf",code)
                self.assertIn("UNSUPPORTED_OR_UNTRUSTED_PACKET",code)
                self.assertNotIn("fetch(",code)
        finally:
            server.shutdown();server.server_close();worker.join(timeout=3)

if __name__=="__main__":unittest.main()

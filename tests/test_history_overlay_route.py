import threading
import unittest
from urllib.request import urlopen, Request
from urllib.error import HTTPError
import json
from tests.test_history_overlay_admission import packet
from terminan.server import Handler, ThreadingHTTPServer

class HistoryOverlayRoutes(unittest.TestCase):
    def test_admission_http_is_local_bounded_and_returns_only_safe_errors(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        base='http://127.0.0.1:%d'%server.server_port
        def post(body,origin=base,ctype='application/json'):
            return urlopen(Request(base+'/api/history-overlay/validate',data=body,
                headers={'Origin':origin,'Content-Type':ctype}),timeout=3)
        try:
            with post(json.dumps(packet()).encode()) as response:
                result=json.load(response)
                self.assertEqual(result['integrity'],'SHA256_MATCH')
                self.assertEqual(response.headers['Cache-Control'],'no-store')
            for body,origin,ctype,code in [(b'{}','https://example.com','application/json',403),
                  (b'{}',base,'text/plain',415),
                  (b'{bad',base,'application/json',422)]:
                with self.subTest(code=code):
                    with self.assertRaises(HTTPError) as ctx:post(body,origin,ctype)
                    self.assertEqual(ctx.exception.code,code);ctx.exception.close()
            # Reject oversized declared bodies before reading them. Sending megabytes
            # into a closed Windows socket can reset the connection before HTTPError.
            request=Request(base+'/api/history-overlay/validate',data=b'{}',headers={
                'Origin':base,'Content-Type':'application/json','Content-Length':'2097153'})
            with self.assertRaises(HTTPError) as ctx:urlopen(request,timeout=3)
            self.assertEqual(ctx.exception.code,413);ctx.exception.close()
        finally:
            server.shutdown();server.server_close();worker.join(timeout=3)
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
                self.assertIn("/api/history-overlay/validate",code)
                self.assertIn("scientificBinding",code)
        finally:
            server.shutdown();server.server_close();worker.join(timeout=3)

if __name__=="__main__":unittest.main()

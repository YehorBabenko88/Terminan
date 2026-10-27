"""Disposable real loopback Supervisor -> Terminan dashboard acceptance."""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from unittest.mock import patch
from terminan.consumer import dashboard

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        body=json.dumps({"api_version":{"major":1,"minor":0},
            "producer":"unified-system","read_only":True,
            "status":"AVAILABLE","state":"BLOCKED",
            "trading_authorized":False,"physical_acceptance":"NOT_RUN"}).encode()
        self.send_response(200)
        self.send_header("Content-Length",str(len(body)))
        self.end_headers();self.wfile.write(body)

class DashboardHTTPTests(unittest.TestCase):
    def test_dashboard_supervisor_blocked(self):
        server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
        server.daemon_threads=True
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            with patch.dict("os.environ",{"TERMINAN_SUPERVISOR_CONTRACT_PORT":str(server.server_port)}):
                with patch("terminan.consumer.all_sources",return_value={"sources":{}}):
                    result=dashboard("BTCUSDT")
            self.assertEqual(result["supervisor"]["state"],"BLOCKED")
            self.assertEqual(result["supervisor"]["provenance"],"UNVERIFIED")
            self.assertFalse(result["trading_authorized"])
        finally:
            server.shutdown();server.server_close();thread.join(timeout=3)
            self.assertFalse(thread.is_alive())

if __name__=="__main__":unittest.main()

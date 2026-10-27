"""Disposable loopback HTTP tests for Supervisor consumer."""
import json
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from unittest.mock import patch
from terminan.supervisor_consumer import supervisor_status

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        if self.path!="/internal/v1/health":
            self.send_error(404);return
        if self.server.slow:
            time.sleep(0.7)
        body=json.dumps({"api_version":{"major":1,"minor":0},"producer":self.server.producer,
                         "read_only":True,"status":"AVAILABLE","state":"BLOCKED",
                         "trading_authorized":False,"physical_acceptance":"NOT_RUN"}).encode()
        try:
            self.send_response(200)
            self.send_header("Content-Type","application/json")
            self.send_header("Content-Length",str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (OSError,BrokenPipeError):
            pass

class TransportTests(unittest.TestCase):
    def serve(self,producer="unified-system",slow=False):
        server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
        server.daemon_threads=True
        server.producer=producer
        server.slow=slow
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        self.addCleanup(lambda: (server.shutdown(),server.server_close(),thread.join(timeout=3)))
        return server.server_port
    def test_valid_blocked_status(self):
        port=self.serve()
        with patch.dict("os.environ",{"TERMINAN_SUPERVISOR_CONTRACT_PORT":str(port)}):
            result=supervisor_status()
        self.assertEqual(result["state"],"BLOCKED")
        self.assertFalse(result["trading_authorized"])
    def test_wrong_producer_rejected(self):
        port=self.serve(producer="bybit-cluster-grid")
        with patch.dict("os.environ",{"TERMINAN_SUPERVISOR_CONTRACT_PORT":str(port)}):
            self.assertEqual(supervisor_status()["state"],"UNAVAILABLE")
    def test_slow_headers_rejected(self):
        port=self.serve(slow=True)
        with patch.dict("os.environ",{"TERMINAN_SUPERVISOR_CONTRACT_PORT":str(port)}):
            start=time.monotonic()
            result=supervisor_status()
            elapsed=time.monotonic()-start
        self.assertEqual(result["state"],"UNAVAILABLE")
        self.assertLess(elapsed,5.0)

if __name__=="__main__":unittest.main()

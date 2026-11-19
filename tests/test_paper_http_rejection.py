from contextlib import closing
import http.client
from http.server import ThreadingHTTPServer
import os
from pathlib import Path
import tempfile
from threading import Thread
import unittest
from unittest.mock import patch

from terminan.server import Handler


class PaperHttpRejectionTests(unittest.TestCase):
    def test_bounded_rejected_body_returns_http_status_without_creating_ledger(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "must-not-exist.sqlite3"
            with patch.dict(os.environ, {"TERMINAN_PAPER_LEDGER": str(ledger)}), \
                    patch.object(Handler, "log_message"), \
                    ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
                worker = Thread(target=server.serve_forever)
                worker.start()
                try:
                    for route, origin, expected in (
                            ("/api/paper/replay", "http://attacker.invalid", 400),
                            ("/api/orders", None, 404)):
                        with self.subTest(route=route), closing(http.client.HTTPConnection(
                                "127.0.0.1", server.server_port, timeout=5)) as client:
                            headers = {"Content-Type": "application/json"}
                            if origin is not None:
                                headers["Origin"] = origin
                            # Deliberately invalid JSON: a rejected body is consumed
                            # within bounds but never parsed or passed to replay.
                            client.request("POST", route, body=b"x" * 65536, headers=headers)
                            with client.getresponse() as response:
                                self.assertEqual(response.status, expected)
                                self.assertTrue(response.read())
                    self.assertFalse(ledger.exists())
                    for framing in (
                            [("Content-Length", "262145")],
                            [("Content-Length", "1"), ("Content-Length", "2")],
                            [("Transfer-Encoding", "chunked")]):
                        with self.subTest(framing=framing), closing(http.client.HTTPConnection(
                                "127.0.0.1", server.server_port, timeout=5)) as client:
                            client.putrequest("POST", "/api/paper/replay")
                            client.putheader("Content-Type", "application/json")
                            for name, value in framing:
                                client.putheader(name, value)
                            client.endheaders()
                            # No body is sent: forbidden framing must be rejected
                            # before waiting for or draining an unbounded body.
                            with client.getresponse() as response:
                                self.assertEqual(response.status, 400)
                                self.assertTrue(response.read())
                    self.assertFalse(ledger.exists())
                finally:
                    server.shutdown()
                    worker.join(timeout=5)
                    self.assertFalse(worker.is_alive())

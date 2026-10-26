"""Offline HTTP failure-path regressions; no production DB or network required."""
import io
import json
import unittest
from unittest.mock import patch

from terminan.server import Handler


class FakeHandler(Handler):
    def __init__(self, path):
        self.path = path
        self.wfile = io.BytesIO()
        self.status = None
        self.headers = {}
    def send_response(self, code, message=None):
        self.status = code
    def send_header(self, key, value):
        self.headers[key] = value
    def end_headers(self):
        pass
    def send_error(self, code, message=None, explain=None):
        self.status = code


class HttpFaultInjection(unittest.TestCase):
    def test_invalid_dom_rows_return_400(self):
        h = FakeHandler("/api/dom-preview?rows=not-an-integer")
        h.do_GET()
        self.assertEqual(h.status, 400)
        self.assertEqual(h.headers["Cache-Control"], "no-store")

    def test_source_exception_fails_closed_without_leaking_secrets(self):
        h = FakeHandler("/api/source/health")
        with patch("terminan.server.source_health", side_effect=RuntimeError("password=secret-value")):
            h.do_GET()
        self.assertEqual(h.status, 503)
        body = h.wfile.getvalue().decode()
        self.assertEqual(json.loads(body), {"error": "source unavailable"})
        self.assertNotIn("secret-value", body)

    def test_unknown_endpoint_returns_404(self):
        h = FakeHandler("/api/not-a-real-endpoint")
        h.do_GET()
        self.assertEqual(h.status, 404)

    def test_status_endpoint_is_read_only(self):
        h = FakeHandler("/api/status")
        with patch.dict("os.environ", {}, clear=True):
            h.do_GET()
        self.assertEqual(h.status, 200)
        self.assertEqual(json.loads(h.wfile.getvalue())["mode"], "READ_ONLY")

    def test_invalid_json_number_fails_closed(self):
        h = FakeHandler("/api/source/health")
        with patch("terminan.server.source_health", return_value={"value": float("nan")}):
            h.do_GET()
        self.assertEqual(h.status, 400)
        self.assertNotIn("NaN", h.wfile.getvalue().decode())


if __name__ == "__main__":
    unittest.main()

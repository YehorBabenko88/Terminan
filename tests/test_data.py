import http.client
import json
import os
import sqlite3
import tempfile
import threading
import unittest
from unittest import mock
from terminan import data

class AdapterTests(unittest.TestCase):
    def test_invalid_symbol(self):
        with self.assertRaises(ValueError): data.candles('BTC;DROP')
    def test_missing_sources(self):
        old=os.environ.pop('TERMINAN_STRATTESTER_DB',None)
        try: self.assertEqual(data.instruments(),[])
        finally:
            if old is not None: os.environ['TERMINAN_STRATTESTER_DB']=old
    def test_readonly_candles(self):
        with tempfile.TemporaryDirectory() as d:
            p=os.path.join(d,'market.db');c=sqlite3.connect(p)
            c.execute('CREATE TABLE candles(symbol TEXT,timeframe TEXT,open_time INTEGER,open REAL,high REAL,low REAL,close REAL,volume REAL)')
            c.execute('INSERT INTO candles VALUES(?,?,?,?,?,?,?,?)',('BTCUSDT','1m',123,1,3,1,2,4));c.commit();c.close()
            old=os.environ.get('TERMINAN_STRATTESTER_DB');os.environ['TERMINAN_STRATTESTER_DB']=p
            try:
                self.assertEqual(data.instruments(),['BTCUSDT'])
                self.assertEqual(data.candles('BTCUSDT')[0]['c'],2)
            finally:
                if old is None:os.environ.pop('TERMINAN_STRATTESTER_DB',None)
                else:os.environ['TERMINAN_STRATTESTER_DB']=old
if __name__=='__main__':unittest.main()


class GridReadOnlyGatewayTests(unittest.TestCase):
    """Current Grid v1 reports UNAVAILABLE even with PostgreSQL read-only."""

    @staticmethod
    def caps():
        return {
            "api_version": {"major": 1, "minor": 0},
            "producer": "bybit-cluster-grid", "read_only": True,
            "status": "UNAVAILABLE", "reason": "SOURCE_PROVENANCE_UNAVAILABLE",
            "capabilities": {
                "candles": "UNAVAILABLE", "footprint": "UNAVAILABLE",
                "live_l2": False,
            },
        }

    @classmethod
    def health(cls):
        return {**cls.caps(), "database": "READ_ONLY"}

    @staticmethod
    def connection_factory(payloads, requests):
        class Response:
            def __init__(self, payload):
                self.payload = payload
                self.status = payload.get("_status", 200)
            def getheader(self, name):
                if name == "Content-Type":
                    return self.payload.get("_type", "application/json")
                if name == "Content-Encoding":
                    return self.payload.get("_encoding")
                return None
            def read(self, n=-1):
                data = self.payload.get("_raw")
                if data is None:
                    data = json.dumps({
                        k: v for k, v in self.payload.items()
                        if not k.startswith("_")
                    }).encode()
                return data[:n]

        class Connection:
            def __init__(self, host, port, timeout):
                requests.append(("connect", host, port, timeout))
            def request(self, method, path, headers):
                requests.append(("request", method, path, headers))
            def getresponse(self):
                return Response(payloads.pop(0))
            def close(self):
                requests.append(("close",))
        return Connection

    def test_unconfigured_is_disconnected_and_never_connects(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch("terminan.data.http.client.HTTPConnection") as opening:
                result = data.grid_source_status()
        opening.assert_not_called()
        self.assertEqual(result["connection"], "UNAVAILABLE")
        self.assertEqual(result["market_data"], "UNAVAILABLE")
        self.assertFalse(result["execution_authority"])

    def test_existing_grid_capabilities_are_not_misreported_as_live(self):
        calls, payloads = [], [self.caps(), self.health()]
        with mock.patch.dict(os.environ, {"TERMINAN_GRID_API_PORT": "18766"}):
            with mock.patch("terminan.data.http.client.HTTPConnection",
                            self.connection_factory(payloads, calls)):
                result = data.grid_source_status()
        self.assertEqual(result["connection"], "CONNECTED_UNQUALIFIED")
        self.assertEqual(result["database"], "READ_ONLY")
        self.assertEqual(result["market_data"], "UNAVAILABLE")
        self.assertEqual(result["candles"], "UNAVAILABLE")
        self.assertFalse(result["live_l2"])
        self.assertFalse(result["execution_authority"])
        self.assertEqual([c[2] for c in calls if c[0] == "request"],
                         ["/internal/v1/capabilities", "/internal/v1/health"])
        self.assertEqual([c[1] for c in calls if c[0] == "connect"],
                         ["127.0.0.1", "127.0.0.1"])
        self.assertTrue(all(c[1] == "GET" for c in calls if c[0] == "request"))
        self.assertTrue(all("Authorization" not in c[3] for c in calls if c[0] == "request"))
        self.assertEqual(len([c for c in calls if c[0] == "close"]), 2)

    def test_version_or_producer_mismatch_fails_closed(self):
        for change in ({"producer": "other-source"},
                       {"api_version": {"major": 2, "minor": 0}},
                       {"read_only": False}, {"status": "LIVE"}):
            with self.subTest(change=change):
                calls = []
                with mock.patch.dict(os.environ, {"TERMINAN_GRID_API_PORT": "18766"}):
                    with mock.patch("terminan.data.http.client.HTTPConnection",
                                    self.connection_factory([{**self.caps(), **change}], calls)):
                        result = data.grid_source_status()
                self.assertEqual(result["connection"], "UNAVAILABLE")
                self.assertEqual(result["database"], "UNAVAILABLE")
                self.assertFalse(result["execution_authority"])

    def test_untrusted_capability_and_wrong_database_fail_closed(self):
        for change in ({"candles": "LIVE"}, {"live_l2": True}):
            with self.subTest(change=change):
                caps = self.caps()
                caps["capabilities"].update(change)
                calls = []
                with mock.patch.dict(os.environ, {"TERMINAN_GRID_API_PORT": "18766"}):
                    with mock.patch("terminan.data.http.client.HTTPConnection",
                                    self.connection_factory([caps, self.health()], calls)):
                        self.assertEqual(data.grid_source_status()["connection"], "UNAVAILABLE")
        bad_health = {**self.health(), "database": "READ_WRITE"}
        with mock.patch.dict(os.environ, {"TERMINAN_GRID_API_PORT": "18766"}):
            with mock.patch("terminan.data.http.client.HTTPConnection",
                            self.connection_factory([self.caps(), bad_health], [])):
                self.assertEqual(data.grid_source_status()["connection"], "UNAVAILABLE")

    def test_no_redirect_compression_or_unbounded_payload(self):
        for sample in (
            {"_status": 302},
            {"_encoding": "gzip"},
            {"_type": "text/html"},
            {"_raw": b"x" * (data._GRID_MAX_JSON + 1)},
            {"_raw": b'{"api_version":NaN}'},
        ):
            with self.subTest(sample=tuple(sample)):
                with mock.patch.dict(os.environ, {"TERMINAN_GRID_API_PORT": "18766"}):
                    with mock.patch("terminan.data.http.client.HTTPConnection",
                                    self.connection_factory([sample], [])):
                        result = data.grid_source_status()
                self.assertEqual(result["connection"], "UNAVAILABLE")

    def test_invalid_port_is_rejected_without_network(self):
        for port in ("http://127.0.0.1:18766", "0", "65536", "-1", "80/path",
                     "00123", "localhost:80", " 18766", "18766 "):
            with self.subTest(port=port):
                with mock.patch.dict(os.environ, {"TERMINAN_GRID_API_PORT": port}):
                    with mock.patch("terminan.data.http.client.HTTPConnection") as opening:
                        self.assertEqual(data.grid_source_status()["connection"], "UNAVAILABLE")
                    opening.assert_not_called()

    def test_connection_exception_redacted(self):
        with mock.patch.dict(os.environ, {"TERMINAN_GRID_API_PORT": "18766"}):
            with mock.patch("terminan.data.http.client.HTTPConnection",
                            side_effect=RuntimeError("token=never-print-me")):
                result = data.grid_source_status()
        self.assertNotIn("never-print-me", str(result))
        self.assertEqual(result["connection"], "UNAVAILABLE")

    def test_status_http_routes_are_bounded_and_read_only(self):
        from http.server import ThreadingHTTPServer
        from terminan.server import Handler

        fixed = {
            "api_version": {"major": 1, "minor": 0},
            "producer": "bybit-cluster-grid",
            "connection": "CONNECTED_UNQUALIFIED",
            "market_data": "UNAVAILABLE",
            "database": "READ_ONLY",
            "candles": "UNAVAILABLE",
            "footprint": "UNAVAILABLE",
            "live_l2": False,
            "execution_authority": False,
        }
        with mock.patch("terminan.data.grid_source_status", return_value=fixed):
            with mock.patch.object(Handler, "log_message", return_value=None):
                server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
                server.daemon_threads = True
                worker = threading.Thread(target=server.serve_forever, daemon=True)
                worker.start()
                try:
                    for route in ("/api/grid/source", "/api/status"):
                        conn = http.client.HTTPConnection(
                            "127.0.0.1", server.server_port, timeout=3
                        )
                        try:
                            conn.request("GET", route)
                            resp = conn.getresponse()
                            self.assertEqual(resp.status, 200)
                            self.assertEqual(resp.getheader("Cache-Control"), "no-store")
                            result = json.loads(resp.read())
                        finally:
                            conn.close()
                        source = result if route == "/api/grid/source" else result["grid_source"]
                        self.assertEqual(source["market_data"], "UNAVAILABLE")
                        self.assertFalse(source["execution_authority"])
                        self.assertFalse(source["live_l2"])
                finally:
                    server.shutdown()
                    server.server_close()
                    worker.join(timeout=3)
                    self.assertFalse(worker.is_alive())

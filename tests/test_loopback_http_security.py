"""Offline loopback HTTP regression: no database, exchange or trading access."""
import http.client
import threading
import unittest
from http.server import ThreadingHTTPServer
from terminan.server import Handler


class LoopbackHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def request(self, method, path, host=None):
        con = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        try:
            headers = {'Host': host if host is not None else f'127.0.0.1:{self.server.server_port}'}
            con.request(method, path, headers=headers)
            response = con.getresponse()
            response.read()
            return response.status, dict(response.getheaders())
        finally:
            con.close()

    def test_valid_loopback_status(self):
        status, headers = self.request('GET', '/api/status')
        self.assertEqual(status, 200)
        self.assertEqual(headers.get('Cache-Control'), 'no-store')
        self.assertEqual(headers.get('X-Content-Type-Options'), 'nosniff')

    def test_rebinding_host_rejected(self):
        status, _ = self.request('GET', '/api/status', 'attacker.invalid')
        self.assertEqual(status, 403)

    def test_oversized_target_rejected(self):
        status, _ = self.request('GET', '/api/status?' + 'x' * 2100)
        self.assertEqual(status, 414)

    def test_mutating_methods_rejected(self):
        for method in ('POST', 'PUT', 'DELETE', 'OPTIONS'):
            with self.subTest(method=method):
                status, _ = self.request(method, '/api/status')
                self.assertEqual(status, 405)

    def test_query_field_limit(self):
        status, _ = self.request('GET', '/api/status?' + '&'.join('x=1' for _ in range(13)))
        self.assertEqual(status, 400)

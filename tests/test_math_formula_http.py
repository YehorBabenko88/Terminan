"""Real local HTTP catches the missing route; upstream is controlled, no DB."""
import io
import http.client
import json
import threading
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from terminan.server import Handler, ThreadingHTTPServer


class FormulaHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.worker = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()
        cls.root = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.worker.join()

    def request(self, payload, origin=None):
        raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        try:
            conn.putrequest('POST', '/api/math/formula')
            conn.putheader('Content-Type', 'application/json')
            conn.putheader('Origin', origin or self.root)
            conn.putheader('Content-Length', str(len(raw)))
            # Headers alone suffice for rejection before reading a body.
            conn.endheaders(raw if len(raw) <= 262144 and origin is None else None)
            r = conn.getresponse()
            return r.status, r.read()
        finally:
            conn.close()

    def formula(self):
        return dict(schema='math.formula.v1', execution_authority=False,
                    values=[1, 2], formula='x+1', inputUnit='dimensionless', outputUnit='dimensionless')

    def test_allowed_formula_reaches_bridge(self):
        result = dict(schema='math.formula.result.v1', source='CALLER_SUPPLIED_UNATTESTED',
                      trading_authorized=False, execution_authority=False, values=[2, 3])
        with patch.dict('os.environ', {'TERMINAN_MATH_OFFLINE_BRIDGE': '1'}), patch(
                'terminan.math_bridge.urlopen', return_value=io.BytesIO(json.dumps(result).encode())):
            code, raw = self.request(self.formula())
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(raw)['values'], [2, 3])

    def test_malformed_json(self):
        with patch.dict('os.environ', {'TERMINAN_MATH_OFFLINE_BRIDGE': '1'}):
            self.assertEqual(self.request(b'{!')[0], 422)

    def test_body_limit(self):
        self.assertEqual(self.request(b' '*262145)[0], 413)

    def test_disconnected_engine(self):
        with patch.dict('os.environ', {'TERMINAN_MATH_OFFLINE_BRIDGE': '1'}), patch(
                'terminan.math_bridge.urlopen', side_effect=URLError('offline')):
            code, raw = self.request(self.formula())
        self.assertEqual(code, 422)
        self.assertFalse(json.loads(raw)['trading_authorized'])

    def test_disabled_engine(self):
        with patch.dict('os.environ', {}, clear=True):
            self.assertEqual(self.request(self.formula())[0], 422)

    def test_authority_refused(self):
        d = self.formula(); d['execution_authority'] = True
        with patch.dict('os.environ', {'TERMINAN_MATH_OFFLINE_BRIDGE': '1'}):
            self.assertEqual(self.request(d)[0], 422)

    def test_cross_origin(self):
        self.assertEqual(self.request(self.formula(), 'http://attacker.invalid')[0], 403)

    def test_upstream_trading_authority_refused(self):
        result = dict(schema='math.formula.result.v1', source='CALLER_SUPPLIED_UNATTESTED',
                      trading_authorized=True, execution_authority=False, values=[2, 3])
        with patch.dict('os.environ', {'TERMINAN_MATH_OFFLINE_BRIDGE': '1'}), patch(
                'terminan.math_bridge.urlopen', return_value=io.BytesIO(json.dumps(result).encode())):
            self.assertEqual(self.request(self.formula())[0], 422)

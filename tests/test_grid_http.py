import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from terminan import data
from terminan.server import fleet_snapshot


class GridHTTPContractTest(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.status = 200
        self.payload = {'version': 2, 'symbol': 'BTCUSDT', 'timeframe': '1m', 'rows': [
            {'t': 1795795200000, 'o': '1234.12345678901234567890', 'poc': None, 'h': '1240', 'l': '1230', 'c': '1238', 'buy': '0', 'sell': '0', 'delta': '0', 'trades': 0},
        ]}

        class Handler(BaseHTTPRequestHandler):
            def do_GET(handler):
                self.requests.append(handler.path)
                handler.send_response(self.status)
                handler.end_headers()
                handler.wfile.write(json.dumps(self.payload).encode())

            def log_message(self, *_):
                pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.addCleanup(server.server_close)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        settings = patch.dict(os.environ, {'TERMINAN_GRID_URL': f'http://127.0.0.1:{server.server_port}'})
        settings.start()
        self.addCleanup(settings.stop)

    def test_exact_candle_and_null_through_grid_http(self):
        self.assertEqual(data.grid_candles('BTCUSDT'), self.payload['rows'])
        self.assertEqual(self.requests, ['/v2/candles?symbol=BTCUSDT&limit=300'])

    def test_empty_is_success_but_invalid_scope_and_failed_source_are_errors(self):
        self.payload['rows'] = []
        self.assertEqual(data.grid_candles('BTCUSDT'), [])
        self.payload['timeframe'] = '5m'
        with self.assertRaises(RuntimeError):
            data.grid_candles('BTCUSDT')
        self.status = 503
        with self.assertRaises(RuntimeError):
            data.grid_candles('BTCUSDT')

    def test_binary64_grid_price_is_rejected(self):
        self.payload['rows'][0]['o'] = 1.5
        with self.assertRaises(RuntimeError):
            data.grid_candles('BTCUSDT')

    def test_grid_configuration_does_not_substitute_minutes_for_higher_intervals(self):
        self.assertEqual(data.candles('BTCUSDT', '5m'), [])
        self.assertEqual(self.requests, [])
        with self.assertRaises(ValueError):
            data.candles('BTCUSDT', '2m')

    def test_math_levels_pass_through_without_a_float_conversion(self):
        level = {'timeframe': '1h', 'side': 'high', 'price': '1.00000000000000001'}
        self.payload = {'schema': 'math.market.levels.result.v1', 'symbol': 'BTCUSDT', 'levels': [level]}
        with patch.dict(os.environ, {'TERMINAN_MATH_URL': os.environ['TERMINAN_GRID_URL']}):
            self.assertEqual(data.math_levels('BTCUSDT'), [level])
        self.assertEqual(self.requests, ['/v1/levels?symbol=BTCUSDT'])

    def test_math_levels_refuse_a_response_without_version_or_matching_symbol(self):
        with patch.dict(os.environ, {'TERMINAN_MATH_URL': os.environ['TERMINAN_GRID_URL']}):
            with self.assertRaises(RuntimeError):
                data.math_levels('ETHUSDT')

    def test_monitor_reads_grid_nodes_without_a_database_adapter(self):
        self.payload = {'version': 1, 'nodes': [{'node_id': 'fixture', 'last_seen': '2026-11-27T18:00:00+05:30',
                                                'assigned_symbols': 1}]}
        nodes = fleet_snapshot()['nodes']
        self.assertEqual(nodes[0]['last_seen'], '2026-11-27T12:30:00+00:00')
        self.assertEqual(self.requests, ['/v1/nodes'])

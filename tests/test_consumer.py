import json
from unittest.mock import patch
from test_g0_http import HTTPContract
from terminan.consumer import present_source
from terminan.consumer import source_contract
from unittest.mock import MagicMock
import socket
import threading
import time


class ConsumerHTTP(HTTPContract):
    def test_deadline_expiring_before_socket_assignment_cannot_enter_headers(self):
        con = MagicMock(sock=None)
        con.request.side_effect = lambda *a, **kw: setattr(con, 'sock', MagicMock())
        def immediate_timer(delay, callback):
            timer = MagicMock()
            timer.start.side_effect = callback
            return timer
        with patch.dict('os.environ', {'TERMINAN_GRID_CONTRACT_PORT': '18766'}), patch('terminan.consumer.http.client.HTTPConnection', return_value=con), patch('terminan.consumer.threading.Timer', side_effect=immediate_timer), patch('terminan.consumer.time.monotonic', side_effect=[0, 0, 0, 6]):
            result = source_contract('grid')
        self.assertEqual(result['state'], 'UNAVAILABLE')
        con.request.assert_called_once()
        con.getresponse.assert_not_called()
        con.close.assert_called_once()

    def test_slow_headers_have_whole_operation_deadline(self):
        listener = socket.socket()
        listener.bind(('127.0.0.1', 0))
        listener.listen()
        listener.settimeout(2)
        stop = threading.Event()
        sent = []
        def drip():
            try:
                con, _ = listener.accept()
                with con:
                    con.recv(4096)
                    con.sendall(b'HTTP/1.1 200 OK\r\nX-Slow: ')
                    until = time.monotonic() + 3
                    while time.monotonic() < until and not stop.wait(0.03):
                        con.sendall(b'a')
                        sent.append(1)
            except OSError:
                pass
        worker = threading.Thread(target=drip, daemon=True)
        worker.start()
        self.addCleanup(listener.close)
        self.addCleanup(stop.set)
        started = time.monotonic()
        with patch.dict('os.environ', {'TERMINAN_GRID_CONTRACT_PORT': str(listener.getsockname()[1])}), patch('terminan.consumer.OPERATION_SECONDS', 0.25, create=True):
            result = source_contract('grid')
        elapsed = time.monotonic() - started
        stop.set()
        worker.join(2)
        self.assertEqual(result['state'], 'UNAVAILABLE')
        self.assertGreaterEqual(len(sent), 3)
        self.assertLess(elapsed, 1.5)
    def test_unavailable_supervisor_and_no_execution(self):
        with patch.dict('os.environ', {}, clear=True):
            status, body = self.request('/api/consumer/v1/status')
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual(data['version'], 1)
        self.assertIs(data['trading_authorized'], False)
        self.assertEqual(data['physical_acceptance'], 'NOT_RUN')
        self.assertEqual(data['supervisor']['state'], 'UNAVAILABLE')
        self.assertTrue(all(v['state'] == 'UNAVAILABLE' for v in data['sources'].values()))

    def test_labels_and_unknown_contract_fail_closed(self):
        view = dict(version=1, state='HISTORICAL', authority='HISTORICAL_ONLY', coverage={})
        for state, label in [('HISTORICAL', 'HISTORICAL'), ('STALE', 'STALE'), ('PARTIAL', 'GAP'), ('INVALID_DATA', 'UNAVAILABLE')]:
            self.assertEqual(present_source(dict(view, state=state))['state'], label)
        self.assertEqual(present_source(dict(view, authority='SYNTHETIC_ONLY'))['provenance'], 'SYNTHETIC_ONLY')
        for invalid in (None, {}, dict(view, version=True), dict(view, version=2), dict(view, authority='LIVE'), dict(view, coverage=[])):
            self.assertEqual(present_source(invalid)['state'], 'UNAVAILABLE')

    def test_endpoint_origin_and_query_security(self):
        self.assertEqual(self.request('/api/consumer/v1/status', {'Origin': 'https://example.com'})[0], 403)
        self.assertEqual(self.request('/api/consumer/v1/status?symbol=bad')[0], 400)

    def test_versioned_source_contracts_fail_closed(self):
        for name, version, producer in [('strattester', {'major': 1, 'minor': 0}, 'strattester'), ('grid', {'major': 1, 'minor': 0}, 'bybit-cluster-grid')]:
            value = dict(api_version=version, producer=producer, read_only=True, status='UNAVAILABLE')
            response = MagicMock(status=503)
            body = json.dumps(value).encode()
            response.read1.side_effect = [body, b'', body, b'']
            connection = MagicMock()
            connection.getresponse.return_value = response
            with patch.dict('os.environ', {'TERMINAN_'+name.upper()+'_CONTRACT_PORT':'18766'}), patch('terminan.consumer.http.client.HTTPConnection', return_value=connection) as factory:
                result = source_contract(name)
                self.assertEqual(result['reason'], 'SOURCE_PROVENANCE_UNQUALIFIED')
                factory.assert_called_with('127.0.0.1', 18766, timeout=0.25)
                self.assertEqual(connection.request.call_count, 2)
                response.read1.side_effect = [json.dumps(dict(value, read_only=1)).encode(), b'']
                self.assertEqual(source_contract(name)['reason'], 'SOURCE_CONTRACT_INVALID_OR_UNAVAILABLE')
                response.read1.side_effect = [b'X'*65537]
                self.assertEqual(source_contract(name)['state'], 'UNAVAILABLE')
        with patch.dict('os.environ', {'TERMINAN_GRID_CONTRACT_PORT':'http://user:secret@example.com'}), patch('terminan.consumer.http.client.HTTPConnection') as factory:
            self.assertEqual(source_contract('grid')['reason'], 'INVALID_LOOPBACK_PORT')
            factory.assert_not_called()

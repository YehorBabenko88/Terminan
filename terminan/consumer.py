"""Presentation of versioned read-only views; never grants execution authority."""
from .g0_sources import all_sources
from .supervisor_consumer import supervisor_status
import http.client
import json
import os
import time
import socket
import threading

UNIFIED_SHA = '50e6e63cb183f6dcf1dee3c753f966717ee3b110'
SOURCE_CONTRACT_SHAS = {'strattester': 'ef1c53861998188bdd03b9f037dc45573b3c2acb',
                        'grid': '4ad202996ac06116e336b66851beb6e97beffa26'}
OPERATION_SECONDS = 5
SOCKET_SECONDS = 0.25


def source_contract(name):
    """Bounded GETs to explicitly configured numeric loopback ports, no redirects."""
    unavailable = {'state': 'UNAVAILABLE', 'reason': 'SOURCE_CONTRACT_NOT_CONFIGURED'}
    raw = os.environ.get('TERMINAN_' + name.upper() + '_CONTRACT_PORT', '')
    if not raw:
        return unavailable
    if not raw.isascii() or not raw.isdecimal() or len(raw) > 5 or not 1 <= int(raw) <= 65535:
        return dict(unavailable, reason='INVALID_LOOPBACK_PORT')
    producer = 'strattester' if name == 'strattester' else 'bybit-cluster-grid'
    try:
        deadline = time.monotonic() + OPERATION_SECONDS
        for endpoint in ('capabilities', 'health'):
            con = http.client.HTTPConnection('127.0.0.1', int(raw), timeout=SOCKET_SECONDS)
            active_socket = [None]
            def expire(connection=con, captured=active_socket):
                sock = captured[0] or connection.sock
                if sock is not None:
                    try:
                        sock.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                    try:
                        sock.close()
                    except OSError:
                        pass
            timer = threading.Timer(max(0, deadline-time.monotonic()), expire)
            timer.daemon = True
            timer.start()
            try:
                if time.monotonic() >= deadline:
                    raise ValueError('request deadline')
                con.request('GET', '/internal/v1/' + endpoint, headers={'Accept': 'application/json'})
                active_socket[0] = con.sock
                if time.monotonic() >= deadline:
                    raise ValueError('response deadline')
                response = con.getresponse()
                if response.status not in (200, 503):
                    raise ValueError('http status')
                body = bytearray()
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise ValueError('response deadline')
                    if con.sock is not None:
                        con.sock.settimeout(min(SOCKET_SECONDS, remaining))
                    chunk = response.read1(min(4096, 65537-len(body)))
                    if not chunk:
                        break
                    body.extend(chunk)
                    if len(body) > 65536:
                        raise ValueError('oversized response')
                value = json.loads(body, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
                version = value.get('api_version')
                valid_version = (isinstance(version, dict) and type(version.get('major')) is int
                                 and version['major'] == 1 and type(version.get('minor')) is int
                                 and version['minor'] == 0)
                if not valid_version or value.get('producer') != producer or value.get('read_only') is not True:
                    raise ValueError('unqualified contract')
                if endpoint == 'health' and value.get('status') != 'UNAVAILABLE':
                    raise ValueError('unsupported qualified source')
            finally:
                timer.cancel()
                timer.join()
                con.close()
        # Both source-owned v1 contracts currently withhold all qualified data.
        return {'state': 'UNAVAILABLE', 'reason': 'SOURCE_PROVENANCE_UNQUALIFIED',
                'api_version': {'major': 1, 'minor': 0}, 'producer': producer, 'read_only': True,
                'contract_source_sha': SOURCE_CONTRACT_SHAS[name], 'runtime_source_sha': 'UNVERIFIED'}
    except (OSError, ValueError, TypeError, AttributeError, http.client.HTTPException):
        return dict(unavailable, reason='SOURCE_CONTRACT_INVALID_OR_UNAVAILABLE')


def present_source(view):
    unavailable = {'state': 'UNAVAILABLE', 'provenance': 'UNVERIFIED'}
    if not isinstance(view, dict) or type(view.get('version')) is not int or view['version'] != 1:
        return unavailable
    authority = view.get('authority')
    if authority not in ('HISTORICAL_ONLY', 'AGGREGATED_HISTORY_NOT_L2', 'TELEMETRY_ONLY', 'SYNTHETIC_ONLY'):
        return unavailable
    state = view.get('state')
    coverage = view.get('coverage', {})
    if not isinstance(coverage, dict):
        return unavailable
    if state == 'STALE':
        label = 'STALE'
    elif state == 'PARTIAL':
        label = 'GAP'
    elif state == 'HISTORICAL':
        label = 'HISTORICAL'
    elif state == 'FRESH' and authority == 'TELEMETRY_ONLY':
        label = 'TELEMETRY'
    else:
        label = 'UNAVAILABLE'
    return {'state': label, 'provenance': authority,
            'runtime_identity': 'UNVERIFIED',
            'coverage_verified': coverage.get('verified') is True}


def dashboard(symbol, timeframe='1m'):
    views = all_sources(symbol, timeframe)
    return {'version': 1, 'mode': 'READ_ONLY',
            'sources': {name: present_source(view) for name, view in views['sources'].items()},
            'source_contracts': {name: source_contract(name) for name in ('strattester', 'grid')},
            'supervisor': supervisor_status(),
            'trading_authorized': False, 'physical_acceptance': 'NOT_RUN'}

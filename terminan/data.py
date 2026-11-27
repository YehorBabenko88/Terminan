"""Read-only adapters; never mutate source databases."""
import http.client
import json
import os
import re
import time
from contextlib import contextmanager

SYMBOL = re.compile(r"^[A-Z0-9]{2,30}$")
TIMEFRAMES = {"1m", "3m", "5m", "15m", "30m", "1h", "4h", "1d"}


_PRIVATE_DATA_ENV='UNIFIED_MARKET_DATA_READ_CAPABILITY'
_private_market_data_client=None

class MarketDataReadClient:
    """Private route scope from the owned runtime; no startup authority."""
    __slots__=('_port','_token','_admission')
    def __init__(self,record,admission,release_id):
        if admission is None or admission.require_current() is not True:raise ValueError('CURRENT_SOURCE_REQUIRED')
        fields={'port','token','source_commit','release_id','epoch'}
        if type(record) is not dict or set(record)!=fields:raise ValueError('PRIVATE_SOURCE_REJECTED')
        if (type(record['port']) is not int or not 1<=record['port']<=65535
                or any(type(record[key]) is not str for key in fields-{'port'})
                or not re.fullmatch('[a-f0-9]{64}',record['token'])
                or not re.fullmatch('[a-f0-9]{40}',record['source_commit'])
                or not re.fullmatch('[a-f0-9-]{32,36}',record['epoch'])
                or not 0<len(release_id)<=128 or record['release_id']!=release_id):raise ValueError('PRIVATE_SOURCE_REJECTED')
        if admission.source_identity('market_data')['commit']!=record['source_commit']:raise ValueError('SOURCE_REVISION_REJECTED')
        self._port=record['port'];self._token=record['token'];self._admission=admission
    @property
    def port(self):return self._port
    def __repr__(self):return '<MarketDataReadClient private read-only capability>'
    def get(self,path):
        if (path not in ('/internal/v1/health','/internal/v1/capabilities')
                and re.fullmatch(r'/internal/v1/(?:candles|footprint)\?symbol=[A-Z0-9]{2,30}&limit=(?:[1-9][0-9]{0,2}|1000)',path) is None
                and re.fullmatch(r'/internal/v2/candles/qualified\?symbol=[A-Z0-9]{2,30}&limit=(?:[1-9][0-9]{0,2}|1000)',path) is None
                and re.fullmatch(r'/internal/v2/candles/qualified-rollup\?symbol=[A-Z0-9]{2,30}&timeframe=(?:5m|15m)&limit=[1-5]',path) is None):raise ValueError('READ_ROUTE_REJECTED')
        if self._admission.require_current() is not True:raise ValueError('CURRENT_SOURCE_REQUIRED')
        result=_market_data_http_get(self.port,path,headers={'Authorization':'Bearer '+self._token})
        if self._admission.require_current() is not True:raise ValueError('CURRENT_SOURCE_REQUIRED')
        return result

def configure_market_data_client(startup_admission):
    global _private_market_data_client
    _private_market_data_client=None
    raw=os.environ.pop(_PRIVATE_DATA_ENV,None)
    if not os.environ.get('UNIFIED_MODULE_ID'):
        if raw is not None:raise ValueError('UNMANAGED_PRIVATE_SOURCE_REJECTED')
        return
    if os.environ.get('UNIFIED_MODULE_ID')!='terminan' or type(raw) is not str or len(raw)>2048:raise ValueError('PRIVATE_SOURCE_REQUIRED')
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('PRIVATE_SOURCE_REJECTED')
            result[key]=value
        return result
    try:
        record=json.loads(raw,object_pairs_hook=unique)
        client=MarketDataReadClient(record,startup_admission,os.environ.get('UNIFIED_RELEASE_ID',''))
    except Exception:raise ValueError('PRIVATE_SOURCE_REJECTED') from None
    _private_market_data_client=client

def _market_data_port():
    if _private_market_data_client is not None:return _private_market_data_client.port
    return os.environ.get('MARKET_DATA_API_PORT')


def validate(symbol, timeframe="1m"):
    if not SYMBOL.fullmatch(symbol) or timeframe not in TIMEFRAMES:
        raise ValueError("invalid symbol or timeframe")

@contextmanager
def sqlite_ro(env):
    from .migration.research_results import open_frozen_sqlite_snapshot
    path = os.environ.get(env)
    if not path:
        yield None
        return
    with open_frozen_sqlite_snapshot(path) as con:
        yield con

def candles(symbol, timeframe="1m", limit=300):
    validate(symbol,timeframe)
    # Qualified source API is the only active market-data boundary.
    return market_data_candles(symbol,limit) if timeframe=="1m" else []

def instruments():
    # Discovery is unavailable until a source-qualified immutable catalogue is admitted.
    return []

def research(symbol, limit=50):
    validate(symbol)
    with sqlite_ro("TERMINAN_RESULTS_DB") as con:
        if con is None:
            return []
        rows = con.execute("SELECT run_id,strategy_id,strategy_version,created_at,metrics FROM research_results WHERE symbol=? ORDER BY created_at DESC LIMIT ?", (symbol,max(1,min(int(limit),100)))).fetchall()
        return [dict(run_id=r[0], strategy=r[1], version=r[2], created_at=r[3], metrics=json.loads(r[4])) for r in rows]

def _market_data_market_rows(dataset, symbol, limit):
    """Consume the existing MarketData v1 loopback market endpoint, never SQL directly.

    The current MarketData endpoint has no source-qualified dataset. Reject every
    unqualified/nonempty response; do not turn archived rows into live evidence.
    An authenticated Unified Gateway and qualified MarketData receipt are required
    before enabling actual strategy/chart data.
    """
    validate(symbol)
    count = max(1, min(int(limit), 1000))
    port_text = str(_market_data_port() or "")
    if not re.fullmatch(r"[1-9][0-9]{0,4}", port_text):
        return []
    port = int(port_text)
    if port > 65535:
        return []
    try:
        envelope = _market_data_internal_get(
            port, f"/internal/v1/{dataset}?symbol={symbol}&limit={count}"
        )
        if (type(envelope) is not dict
                or envelope.get("api_version") != {"major": 1, "minor": 0}
                or envelope.get("producer") != "market_data"
                or envelope.get("read_only") is not True
                or envelope.get("status") != "UNAVAILABLE"
                or envelope.get("reason") != "SOURCE_PROVENANCE_UNAVAILABLE"
                or envelope.get("rows") != []
                or envelope.get("limit") != count
                or envelope.get("symbol") != symbol
                or envelope.get("timeframe") != "1m"):
            raise ValueError("unqualified MarketData market response")
    except Exception:
        # Fail closed without exposing remote errors, internal paths or DSNs.
        return []
    return []


def market_data_candles(symbol, limit=300):
    return _market_data_market_rows("candles", symbol, limit)


def footprint(symbol, limit=500):
    return _market_data_market_rows("footprint", symbol, limit)

# MarketData owns all exchange connectivity. This bounded probe consumes ONLY the
# existing MarketData public-data capability API on the same host; it never retrieves
# exchange data, DB credentials, or grants strategy execution authority.
_MARKET_DATA_CAPS_PATH = "/internal/v1/capabilities"
_MARKET_DATA_HEALTH_PATH = "/internal/v1/health"
_MARKET_DATA_MAX_JSON = 16384
# B's canonical v2 limits each record to 1 MiB; chart reads at most 5.
# Keep a bounded transport budget for a valid 5-row footprint receipt.
# This is not a general increase for legacy/unmanaged probe endpoints.
_QUALIFIED_V2_MAX_JSON = 5 * 1_048_576 + 65_536
_QUALIFIED_MTF_MAX_JSON = 8 * 1_048_576 + 65_536


def _market_data_internal_get(port,path):
    if _private_market_data_client is not None:
        if port!=_private_market_data_client.port:raise ValueError("SOURCE_ENDPOINT_REJECTED")
        return _private_market_data_client.get(path)
    if os.environ.get("UNIFIED_MODULE_ID"):raise ValueError("PRIVATE_SOURCE_REQUIRED")
    return _market_data_http_get(port,path)


def _market_data_http_get(port, path, *, headers=None):
    """One direct loopback GET; no DNS, redirects, proxy or writes."""
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
    try:
        conn.request("GET", path, headers={"Accept": "application/json",
                                           "Connection": "close",**(headers or {})})
        response = conn.getresponse()
        if response.status != 200:
            raise ValueError("market-data gateway unavailable")
        if response.getheader("Content-Encoding"):
            raise ValueError("market-data compressed response unsupported")
        media_type = (response.getheader("Content-Type") or "").split(";", 1)[0]
        if media_type.strip().lower() != "application/json":
            raise ValueError("market-data content type mismatch")
        # The strict private client owns the v2 route; this parser cannot
        # turn an arbitrary path into a credentialed capability.
        qualified_v2 = re.fullmatch(
            r"/internal/v2/candles/qualified\?symbol=[A-Z0-9]{2,30}&limit=[1-5]",
            path) is not None and headers is not None
        qualified_mtf = re.fullmatch(
            r"/internal/v2/candles/qualified-rollup\?symbol=[A-Z0-9]{2,30}&timeframe=(?:5m|15m)&limit=[1-5]",
            path) is not None and headers is not None
        budget = (_QUALIFIED_MTF_MAX_JSON if qualified_mtf else
                  _QUALIFIED_V2_MAX_JSON if qualified_v2 else _MARKET_DATA_MAX_JSON)
        advertised = response.getheader("Content-Length")
        if advertised is not None:
            if (re.fullmatch(r"[0-9]{1,10}", advertised) is None
                    or int(advertised) > budget):
                raise ValueError("market-data response size exceeded")
        raw = response.read(budget + 1)
        if len(raw) > budget:
            raise ValueError("market-data response size exceeded")
        def unique_pairs(pairs):
            obj = {}
            for key, value in pairs:
                if key in obj:
                    raise ValueError("duplicate market-data JSON key")
                obj[key] = value
            return obj
        return json.loads(raw.decode("utf-8"), object_pairs_hook=unique_pairs,
                          parse_constant=lambda _value: (_ for _ in ()).throw(
                              ValueError("nonfinite market-data response")))
    finally:
        conn.close()


def market_data_source_status():
    """Conservative status for the existing MarketData v1 internal read API.

    Database reachability is not market provenance. Never promote legacy
    unqualified candles/footprints to LIVE or strategy-ready market data.
    The single source authority is MarketData; remote/LAN access must be mediated
    later by an authenticated Unified Gateway.
    """
    unavailable = {
        "api_version": {"major": 1, "minor": 0},
        "producer": "market_data",
        "connection": "UNAVAILABLE",
        "market_data": "UNAVAILABLE",
        "database": "UNAVAILABLE",
        "candles": "UNAVAILABLE",
        "footprint": "UNAVAILABLE",
        "live_l2": False,
        "execution_authority": False,
    }
    raw_port = _market_data_port()
    if raw_port is not None:raw_port=str(raw_port)
    if raw_port is None:
        return unavailable
    # Strict literal port. No URLs or addresses from environment, so SSRF,
    # proxy inheritance and DNS rebinding cannot redirect the request.
    if not re.fullmatch(r"[1-9][0-9]{0,4}", raw_port):
        return unavailable
    port = int(raw_port)
    if port > 65535:
        return unavailable
    try:
        caps = _market_data_internal_get(port, _MARKET_DATA_CAPS_PATH)
        health = _market_data_internal_get(port, _MARKET_DATA_HEALTH_PATH)
        for envelope in (caps, health):
            if (type(envelope) is not dict or
                envelope.get("api_version") != {"major": 1, "minor": 0} or
                envelope.get("producer") != "market_data" or
                envelope.get("read_only") is not True or
                envelope.get("status") != "UNAVAILABLE"):
                raise ValueError("unqualified market-data gateway contract")
        capabilities = caps.get("capabilities")
        if (type(capabilities) is not dict or
            capabilities.get("candles") != "UNAVAILABLE" or
            capabilities.get("footprint") != "UNAVAILABLE" or
            capabilities.get("live_l2") is not False):
            raise ValueError("unexpected market-data capabilities")
        db = health.get("database")
        if db not in ("READ_ONLY", "UNAVAILABLE"):
            raise ValueError("invalid market-data database status")
        return {
            **unavailable,
            "connection": "CONNECTED_UNQUALIFIED",
            "database": db,
        }
    except Exception:
        # This UI is read-only: do not leak exception text, configured ports,
        # credentials or internal source paths in an API response.
        return unavailable


def qualified_market_data_chart(symbol, limit=5):
    """Managed canonical Grid v2 PARTIAL receipts only; no v1 downgrade.

    The result is an observation display, never PaperEngine's authorization.
    Legacy MARKET_DATA_API_PORT is deliberately not a substitute for the
    Unified-admitted private read capability.
    """
    validate(symbol)
    if type(limit) is not int or not 1 <= limit <= 5:
        raise ValueError("QUALIFIED_CHART_BOUNDED_LIMIT_REQUIRED")
    unavailable = {
        "status": "UNAVAILABLE", "reason": "QUALIFIED_PARTIAL_SOURCE_UNAVAILABLE",
        "read_only": True, "source_authentication": "NOT_EVALUATED",
        "record_integrity": "NOT_EVALUATED",
        "source_authenticity": "NOT_INDEPENDENTLY_ATTESTED",
        "quality_attestation": "NOT_INDEPENDENTLY_ATTESTED",
        "storage_immutability": "NOT_ATTESTED",
        "exchange_completeness_attested": False, "paper_admitted": False,
        "execution_authority": False, "trading_authorized": False,
        "rows": [],
    }
    client = _private_market_data_client
    if type(client) is not MarketDataReadClient:
        return unavailable
    try:
        from .qualified_partial import validate_qualified_v2, chart_rows
        # Qualified chart never downgrades to the legacy v1 reader.
        envelope = client.get(f"/internal/v2/candles/qualified?symbol={symbol}&limit={limit}")
        checked = validate_qualified_v2(envelope, symbol, limit)
        return {
            "status": checked["status"], "reason": checked["reason"],
            "read_only": True, "source_authentication": checked["source_authentication"],
            "record_integrity": checked["record_integrity"],
            "source_authenticity": checked["source_authenticity"],
            "quality_attestation": checked["quality_attestation"],
            "storage_immutability": checked["storage_immutability"],
            "exchange_completeness_attested": False, "data_quality_status": "PARTIAL",
            "paper_admitted": False, "execution_authority": False,
            "trading_authorized": False, "coverage": checked["coverage"],
            "freshness_utc_ms": checked["freshness_utc_ms"],
            "dataset_fingerprint": checked["dataset_fingerprint"],
            "rows": chart_rows(checked),
        }
    except Exception:
        # Do not expose source tokens, exceptions or transport details in UI.
        return unavailable


def qualified_market_data_timeframe_chart(symbol, timeframe, *, bars=5):
    """Only Grid's qualified rollup, with D strict DTO validation; no fallback.

    The original 1m chart remains a separate managed source and no live,
    historical, paper or strategy authority is inferred from this snapshot.
    """
    validate(symbol)
    if type(timeframe) is not str or timeframe not in ("5m", "15m"):
        raise ValueError("QUALIFIED_TIMEFRAME_REQUEST_REQUIRED")
    if type(bars) is not int or not 1 <= bars <= 5:
        raise ValueError("QUALIFIED_TIMEFRAME_REQUEST_REQUIRED")
    unavailable = {
        "status": "UNAVAILABLE", "reason": "QUALIFIED_TIMEFRAME_SOURCE_UNAVAILABLE",
        "timeframe": timeframe, "source_timeframe": "1m",
        "read_only": True, "rows": [], "paper_admitted": False,
        "execution_authority": False, "trading_authorized": False,
        "exchange_completeness_attested": False,
    }
    client = _private_market_data_client
    if type(client) is not MarketDataReadClient:
        return unavailable
    try:
        from .qualified_rollup import validate_qualified_rollup, chart_rollup_rows
        envelope = client.get(
            f"/internal/v2/candles/qualified-rollup?symbol={symbol}&timeframe={timeframe}&limit={bars}"
        )
        checked = validate_qualified_rollup(envelope, symbol, timeframe, bars)
        return {
            "status": checked["status"], "reason": checked["reason"],
            "timeframe": timeframe, "source_timeframe": "1m",
            "source_minutes": checked["source_minutes"],
            "read_only": True, "rows": chart_rollup_rows(checked),
            "record_integrity": checked["record_integrity"],
            "dataset_fingerprint": checked["dataset_fingerprint"],
            "parent_dataset_fingerprint": checked["parent_dataset_fingerprint"],
            "source_revision_declared": checked["source_revision"],
            "source_epoch_declared": checked["producer_epoch"],
            "source_authenticity": checked["source_authenticity"],
            "exchange_completeness_attested": False,
            "coverage": dict(checked["coverage"]),
            "paper_admitted": False, "execution_authority": False,
            "trading_authorized": False,
        }
    except Exception:
        return unavailable

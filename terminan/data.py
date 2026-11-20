"""Read-only adapters; never mutate source databases."""
import http.client
import json
import os
import re
import sqlite3
from pathlib import Path

SYMBOL = re.compile(r"^[A-Z0-9]{2,30}$")
TIMEFRAMES = {"1m", "3m", "5m", "15m", "30m", "1h", "4h", "1d"}

def validate(symbol, timeframe="1m"):
    if not SYMBOL.fullmatch(symbol) or timeframe not in TIMEFRAMES:
        raise ValueError("invalid symbol or timeframe")

def sqlite_ro(env):
    path = os.environ.get(env)
    if not path or not Path(path).is_file():
        return None
    return sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True, timeout=2)

def candles(symbol, timeframe="1m", limit=300):
    validate(symbol,timeframe)
    # Qualified source API is the only active market-data boundary.
    return market_data_candles(symbol,limit) if timeframe=="1m" else []

def instruments():
    # Discovery is unavailable until a source-qualified immutable catalogue is admitted.
    return []

def research(symbol, limit=50):
    validate(symbol)
    con = sqlite_ro("TERMINAN_RESULTS_DB")
    if con is None:
        return []
    try:
        rows = con.execute("SELECT run_id,strategy_id,strategy_version,created_at,metrics FROM research_results WHERE symbol=? ORDER BY created_at DESC LIMIT ?", (symbol,max(1,min(int(limit),100)))).fetchall()
        return [dict(run_id=r[0], strategy=r[1], version=r[2], created_at=r[3], metrics=json.loads(r[4])) for r in rows]
    finally:
        con.close()

def _market_data_market_rows(dataset, symbol, limit):
    """Consume the existing MarketData v1 loopback market endpoint, never SQL directly.

    The current MarketData endpoint has no source-qualified dataset. Reject every
    unqualified/nonempty response; do not turn archived rows into live evidence.
    An authenticated Unified Gateway and qualified MarketData receipt are required
    before enabling actual strategy/chart data.
    """
    validate(symbol)
    count = max(1, min(int(limit), 1000))
    port_text = os.environ.get("MARKET_DATA_API_PORT", "")
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


def _market_data_internal_get(port, path):
    """One direct loopback GET; no DNS, redirects, proxy, credentials or writes."""
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
    try:
        conn.request("GET", path, headers={"Accept": "application/json",
                                           "Connection": "close"})
        response = conn.getresponse()
        if response.status != 200:
            raise ValueError("market-data gateway unavailable")
        if response.getheader("Content-Encoding"):
            raise ValueError("market-data compressed response unsupported")
        media_type = (response.getheader("Content-Type") or "").split(";", 1)[0]
        if media_type.strip().lower() != "application/json":
            raise ValueError("market-data content type mismatch")
        raw = response.read(_MARKET_DATA_MAX_JSON + 1)
        if len(raw) > _MARKET_DATA_MAX_JSON:
            raise ValueError("market-data response size exceeded")
        return json.loads(raw.decode("utf-8"),
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
    raw_port = os.environ.get("MARKET_DATA_API_PORT")
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

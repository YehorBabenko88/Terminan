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
    validate(symbol, timeframe)
    limit = max(1, min(int(limit), 1000))
    con = sqlite_ro("TERMINAN_STRATTESTER_DB")
    if con is None:
        return []
    try:
        rows = con.execute("SELECT open_time,open,high,low,close,volume FROM candles WHERE symbol=? AND timeframe=? ORDER BY open_time DESC LIMIT ?", (symbol, timeframe, limit)).fetchall()
        return [dict(zip(("t","o","h","l","c","v"), row)) for row in reversed(rows)]
    finally:
        con.close()

def instruments():
    con = sqlite_ro("TERMINAN_STRATTESTER_DB")
    if con is None:
        return []
    try:
        return [r[0] for r in con.execute("SELECT DISTINCT symbol FROM candles ORDER BY symbol LIMIT 2000")]
    finally:
        con.close()

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

def grid_query(sql, params):
    dsn = os.environ.get("TERMINAN_GRID_DSN")
    if not dsn:
        return []
    import psycopg
    with psycopg.connect(dsn, connect_timeout=3, options="-c default_transaction_read_only=on -c statement_timeout=3000") as con:
        with con.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

def _grid_market_rows(dataset, symbol, limit):
    """Consume the existing Grid v1 loopback market endpoint, never SQL directly.

    The current Grid endpoint has no source-qualified dataset. Reject every
    unqualified/nonempty response; do not turn archived rows into live evidence.
    An authenticated Unified Gateway and qualified Grid receipt are required
    before enabling actual strategy/chart data.
    """
    validate(symbol)
    count = max(1, min(int(limit), 1000))
    port_text = os.environ.get("TERMINAN_GRID_API_PORT", "")
    if not re.fullmatch(r"[1-9][0-9]{0,4}", port_text):
        return []
    port = int(port_text)
    if port > 65535:
        return []
    try:
        envelope = _grid_internal_get(
            port, f"/internal/v1/{dataset}?symbol={symbol}&limit={count}"
        )
        if (type(envelope) is not dict
                or envelope.get("api_version") != {"major": 1, "minor": 0}
                or envelope.get("producer") != "bybit-cluster-grid"
                or envelope.get("read_only") is not True
                or envelope.get("status") != "UNAVAILABLE"
                or envelope.get("reason") != "SOURCE_PROVENANCE_UNAVAILABLE"
                or envelope.get("rows") != []
                or envelope.get("limit") != count
                or envelope.get("symbol") != symbol
                or envelope.get("timeframe") != "1m"):
            raise ValueError("unqualified Grid market response")
    except Exception:
        # Fail closed without exposing remote errors, internal paths or DSNs.
        return []
    return []


def grid_candles(symbol, limit=300):
    return _grid_market_rows("candles", symbol, limit)


def footprint(symbol, limit=500):
    return _grid_market_rows("footprint", symbol, limit)

# Grid owns all exchange connectivity. This bounded probe consumes ONLY the
# existing Grid public-data capability API on the same host; it never retrieves
# exchange data, DB credentials, or grants strategy execution authority.
_GRID_CAPS_PATH = "/internal/v1/capabilities"
_GRID_HEALTH_PATH = "/internal/v1/health"
_GRID_MAX_JSON = 16384


def _grid_internal_get(port, path):
    """One direct loopback GET; no DNS, redirects, proxy, credentials or writes."""
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
    try:
        conn.request("GET", path, headers={"Accept": "application/json",
                                           "Connection": "close"})
        response = conn.getresponse()
        if response.status != 200:
            raise ValueError("grid gateway unavailable")
        if response.getheader("Content-Encoding"):
            raise ValueError("grid compressed response unsupported")
        media_type = (response.getheader("Content-Type") or "").split(";", 1)[0]
        if media_type.strip().lower() != "application/json":
            raise ValueError("grid content type mismatch")
        raw = response.read(_GRID_MAX_JSON + 1)
        if len(raw) > _GRID_MAX_JSON:
            raise ValueError("grid response size exceeded")
        return json.loads(raw.decode("utf-8"),
                          parse_constant=lambda _value: (_ for _ in ()).throw(
                              ValueError("nonfinite grid response")))
    finally:
        conn.close()


def grid_source_status():
    """Conservative status for the existing Grid v1 internal read API.

    Database reachability is not market provenance. Never promote legacy
    unqualified candles/footprints to LIVE or strategy-ready market data.
    The single source authority is Grid; remote/LAN access must be mediated
    later by an authenticated Unified Gateway.
    """
    unavailable = {
        "api_version": {"major": 1, "minor": 0},
        "producer": "bybit-cluster-grid",
        "connection": "UNAVAILABLE",
        "market_data": "UNAVAILABLE",
        "database": "UNAVAILABLE",
        "candles": "UNAVAILABLE",
        "footprint": "UNAVAILABLE",
        "live_l2": False,
        "execution_authority": False,
    }
    raw_port = os.environ.get("TERMINAN_GRID_API_PORT")
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
        caps = _grid_internal_get(port, _GRID_CAPS_PATH)
        health = _grid_internal_get(port, _GRID_HEALTH_PATH)
        for envelope in (caps, health):
            if (type(envelope) is not dict or
                envelope.get("api_version") != {"major": 1, "minor": 0} or
                envelope.get("producer") != "bybit-cluster-grid" or
                envelope.get("read_only") is not True or
                envelope.get("status") != "UNAVAILABLE"):
                raise ValueError("unqualified grid gateway contract")
        capabilities = caps.get("capabilities")
        if (type(capabilities) is not dict or
            capabilities.get("candles") != "UNAVAILABLE" or
            capabilities.get("footprint") != "UNAVAILABLE" or
            capabilities.get("live_l2") is not False):
            raise ValueError("unexpected grid capabilities")
        db = health.get("database")
        if db not in ("READ_ONLY", "UNAVAILABLE"):
            raise ValueError("invalid grid database status")
        return {
            **unavailable,
            "connection": "CONNECTED_UNQUALIFIED",
            "database": db,
        }
    except Exception:
        # This UI is read-only: do not leak exception text, configured ports,
        # credentials or internal source paths in an API response.
        return unavailable

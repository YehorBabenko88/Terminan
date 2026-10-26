"""Read-only adapters; never mutate source databases."""
import json
import math
import os
import re
import sqlite3
from decimal import Decimal, InvalidOperation
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

def _grid_number(value, *, timestamp=False):
    """Reject lossy/nonfinite source values instead of serializing invalid JSON."""
    if isinstance(value, bool) or value is None:
        raise ValueError("invalid Grid numeric field")
    if timestamp:
        try:
            exact = Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("invalid Grid UTC milliseconds") from exc
        if not exact.is_finite() or exact != exact.to_integral_value() or not 0 <= exact <= (1 << 53) - 1:
            raise ValueError("invalid Grid UTC milliseconds")
        return int(exact)
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("invalid Grid numeric field") from exc
    if not math.isfinite(result):
        raise ValueError("nonfinite Grid numeric field")
    return result


def _grid_row(row, expected_fields):
    if not isinstance(row, (tuple, list)) or len(row) != expected_fields:
        raise ValueError("malformed Grid row arity")
    return tuple(_grid_number(value, timestamp=index == 0)
                 for index, value in enumerate(row))


def grid_candles(symbol, limit=300):
    validate(symbol)
    rows = grid_query("SELECT extract(epoch from ts)*1000,open,high,low,close,buy_volume,sell_volume,delta,trade_count,poc_price FROM candles_1m WHERE symbol=%s ORDER BY ts DESC LIMIT %s", (symbol,max(1,min(int(limit),1000))))
    return [dict(zip(("t","o","h","l","c","buy","sell","delta","trades","poc"), _grid_row(r, 10))) for r in reversed(rows)]

def footprint(symbol, limit=500):
    validate(symbol)
    rows = grid_query("SELECT extract(epoch from ts)*1000,price,buy_volume,sell_volume,delta,volume FROM footprint_1m WHERE symbol=%s ORDER BY ts DESC,price DESC LIMIT %s", (symbol,max(1,min(int(limit),1000))))
    return [dict(zip(("t","price","buy","sell","delta","volume"),_grid_row(r, 6))) for r in rows]

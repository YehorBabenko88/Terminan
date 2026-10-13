"""Read-only adapters; never mutate source databases."""
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
        # Legacy adapters predate the completion column. Preserve their display
        # behavior while retaining authoritative completion from current stores.
        columns = {r[1] for r in con.execute('PRAGMA table_info(candles)')}
        completion = 'complete' if 'complete' in columns else '1'
        rows = con.execute(f"SELECT open_time,open,high,low,close,volume,{completion} FROM candles WHERE symbol=? AND timeframe=? ORDER BY open_time DESC LIMIT ?", (symbol, timeframe, limit)).fetchall()
        return [dict(zip(("t","o","h","l","c","v"), row[:6]), complete=bool(row[6])) for row in reversed(rows)]
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
    """Read stored results; do not infer current fencing or trading authority."""
    validate(symbol)
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("invalid research limit")
    con = sqlite_ro("TERMINAN_RESULTS_DB")
    if con is None:
        return []
    try:
        columns = {r[1] for r in con.execute("PRAGMA table_info(research_results)")}
        has_fencing = {"job_id", "lease_token", "node_generation"}.issubset(columns)
        extra = ",job_id,lease_token,node_generation" if has_fencing else ""
        rows = con.execute(
            "SELECT run_id,strategy_id,strategy_version,created_at,metrics" + extra +
            " FROM research_results WHERE symbol=? ORDER BY created_at DESC LIMIT ?",
            (symbol, limit),
        ).fetchall()
        results = []
        for row in rows:
            try:
                metrics = json.loads(row[4])
                if not isinstance(metrics, dict):
                    raise ValueError("metrics must be a JSON object")
                metrics_state = "PARSED"
            except (TypeError, ValueError, json.JSONDecodeError):
                metrics = {}
                metrics_state = "INVALID_METRICS"
            result = dict(run_id=row[0], strategy=row[1], version=row[2],
                          created_at=row[3], metrics=metrics,
                          metrics_state=metrics_state,
                          publication_authority="UNVERIFIED")
            if has_fencing:
                result["fencing"] = {
                    "state": "PRESENT_UNVERIFIED" if row[5] is not None else "LEGACY_UNFENCED",
                    "job_id": row[5], "lease_token_present": row[6] is not None,
                    "node_generation": row[7],
                }
            else:
                result["fencing"] = {"state": "SCHEMA_UNAVAILABLE"}
            results.append(result)
        return results
    finally:
        con.close()

def grid_available():
    return bool(os.environ.get("TERMINAN_GRID_DSN"))

def results_available():
    con = sqlite_ro("TERMINAN_RESULTS_DB")
    if con is None:
        return False
    con.close()
    return True

def grid_query(sql, params):
    dsn = os.environ.get("TERMINAN_GRID_DSN")
    if not dsn:
        return []
    import psycopg
    with psycopg.connect(dsn, connect_timeout=3, options="-c default_transaction_read_only=on -c statement_timeout=3000") as con:
        with con.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

def grid_candles(symbol, limit=300):
    validate(symbol)
    rows = grid_query("SELECT extract(epoch from ts)*1000,open,high,low,close,buy_volume,sell_volume,delta,trade_count,poc_price FROM candles_1m WHERE symbol=%s ORDER BY ts DESC LIMIT %s", (symbol,max(1,min(int(limit),1000))))
    return [dict(zip(("t","o","h","l","c","buy","sell","delta","trades","poc"), (float(v) if v is not None else None for v in r))) for r in reversed(rows)]

def footprint(symbol, limit=500):
    validate(symbol)
    rows = grid_query("SELECT extract(epoch from ts)*1000,price,buy_volume,sell_volume,delta,volume FROM footprint_1m WHERE symbol=%s ORDER BY ts DESC,price DESC LIMIT %s", (symbol,max(1,min(int(limit),1000))))
    return [dict(zip(("t","price","buy","sell","delta","volume"),map(float,r))) for r in rows]

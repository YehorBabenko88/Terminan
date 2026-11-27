"""Read-only adapters; never mutate source databases."""
import json
import os
import re
import sqlite3
from http.client import HTTPConnection
from pathlib import Path
from urllib.parse import urlencode, urlsplit

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
    if os.environ.get("TERMINAN_GRID_URL"):
        return grid_candles(symbol, limit) if timeframe == "1m" else []
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
    gateway = os.environ.get("TERMINAN_GRID_URL")
    if gateway:
        payload = read_source(gateway, "/v1/instruments", {})
        if (not isinstance(payload, dict) or payload.get("version") != 1
                or not isinstance(payload.get("symbols"), list) or len(payload["symbols"]) > 2000
                or any(not isinstance(symbol, str) or not SYMBOL.fullmatch(symbol) for symbol in payload["symbols"])):
            raise RuntimeError("Unexpected Grid instrument DTO")
        return payload["symbols"]
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


DECIMAL_TEXT = re.compile(r"-?[0-9]+(?:\.[0-9]+)?")
CANDLE_DECIMALS = ("o", "h", "l", "c", "buy", "sell", "delta", "poc")
FOOTPRINT_DECIMALS = ("price", "buy", "sell", "delta", "volume")


def read_source(base_url, path, params):
    base = urlsplit(base_url)
    if (base.scheme != "http" or base.hostname not in {"localhost", "127.0.0.1", "::1"}
            or base.username is not None or base.path not in {"", "/"} or base.query or base.fragment):
        raise RuntimeError("Expected a loopback HTTP source")
    max_bytes = 8 * 1024 * 1024
    connection = HTTPConnection(base.hostname, base.port, timeout=4)
    try:
        target = path + "?" + urlencode(params) if params else path
        connection.request("GET", target)
        response = connection.getresponse()
        if response.status != 200:
            raise RuntimeError("Read-only source unavailable")
        body = response.read(max_bytes + 1)
        if len(body) > max_bytes:
            raise RuntimeError("Source response too large")
        try:
            return json.loads(body)
        except (UnicodeError, json.JSONDecodeError) as error:
            raise RuntimeError("Invalid source JSON") from error
    finally:
        connection.close()


def grid_snapshot(route, symbol, limit, decimal_fields):
    validate(symbol)
    limit = max(1, min(int(limit), 1000))
    gateway = os.environ.get("TERMINAN_GRID_URL")
    if not gateway:
        raise RuntimeError("Grid gateway is not configured")
    payload = read_source(gateway, f"/v2/{route}", {"symbol": symbol, "limit": limit})
    if (not isinstance(payload, dict) or type(payload.get("version")) is not int
            or payload["version"] != 2 or payload.get("symbol") != symbol
            or payload.get("timeframe") != "1m"):
        raise RuntimeError("Unexpected Grid DTO")
    rows = payload.get("rows")
    if not isinstance(rows, list) or len(rows) > limit:
        raise RuntimeError("Unexpected Grid rows")
    for row in rows:
        if (not isinstance(row, dict) or type(row.get("t")) is not int or abs(row["t"]) > 2**53 - 1
                or (route == "candles" and ("trades" not in row or (row["trades"] is not None and type(row["trades"]) is not int)))
                or any(field not in row or (row[field] is not None and
                       (not isinstance(row[field], str) or not DECIMAL_TEXT.fullmatch(row[field])))
                       for field in decimal_fields)):
            raise RuntimeError("Unexpected Grid row")
    return payload


def grid_candles(symbol, limit=300):
    return grid_snapshot("candles", symbol, limit, CANDLE_DECIMALS)["rows"]


def footprint(symbol, limit=500):
    return grid_snapshot("footprint", symbol, limit, FOOTPRINT_DECIMALS)


def math_levels(symbol):
    validate(symbol)
    source = os.environ.get("TERMINAN_MATH_URL")
    if not source:
        raise RuntimeError("Math levels provider is not configured")
    payload = read_source(source, "/v1/levels", {"symbol": symbol})
    if (not isinstance(payload, dict) or payload.get("schema") != "math.market.levels.result.v1"
            or payload.get("symbol") != symbol or not isinstance(payload.get("levels"), list)):
        raise RuntimeError("Unexpected Math levels DTO")
    for row in payload["levels"]:
        if (not isinstance(row, dict) or row.get("timeframe") not in {"1h", "4h", "1d"}
                or row.get("side") not in {"low", "high"} or not isinstance(row.get("price"), str)
                or not DECIMAL_TEXT.fullmatch(row["price"])):
            raise RuntimeError("Unexpected Math level")
    return payload["levels"]

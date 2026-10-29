"""Isolated SQLite visualization cache, never the Grid/Strattester source of truth.

Opt-in CLI, local filesystem only. No network, PostgreSQL or upstream imports.
Entries are derived from operator-supplied bounded, immutable JSON snapshots.
A source revision + algorithm version is mandatory to avoid stale reuse.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

SCHEMA = 1
ALGORITHM = "saved-mtf-cache-v1"
MAX_INPUT = 4 * 1024 * 1024
MAX_OUTPUT = 4 * 1024 * 1024
MAX_ENTRIES = 256
MAX_AGE = 30 * 86400

class CacheError(ValueError):
    pass

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()

def digest(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()

def key_for(identity):
    if type(identity) is not dict or set(identity) != {
        "source", "source_revision", "dataset", "symbol", "timeframe",
        "from_ms", "to_ms", "algorithm", "parameters_hash"
    }:
        raise CacheError("INVALID_IDENTITY")
    if identity["source"] not in ("grid", "strattester"):
        raise CacheError("INVALID_SOURCE")
    if identity["algorithm"] != ALGORITHM:
        raise CacheError("UNSUPPORTED_ALGORITHM")
    for name in ("source_revision", "parameters_hash"):
        value = identity[name]
        if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise CacheError("INVALID_REVISION")
    for name in ("dataset", "symbol", "timeframe"):
        value = identity[name]
        if type(value) is not str or not 1 <= len(value) <= 80 or not all(c.isalnum() or c in "_-" for c in value):
            raise CacheError("INVALID_DIMENSION")
    a, b = identity["from_ms"], identity["to_ms"]
    if type(a) is not int or type(b) is not int or a < 946684800000 or b < a or b > 2**53 - 1:
        raise CacheError("INVALID_RANGE")
    return digest(identity)

def open_cache(path):
    path = Path(path)
    if not path.parent.is_dir():
        raise CacheError("PARENT_DIRECTORY_MISSING")
    con = sqlite3.connect(str(path), timeout=2, isolation_level=None)
    con.execute("PRAGMA busy_timeout=2000")
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=FULL")
    con.execute("""CREATE TABLE IF NOT EXISTS cache_entries(
        cache_key TEXT PRIMARY KEY, identity_json TEXT NOT NULL,
        source_revision TEXT NOT NULL, content_hash TEXT NOT NULL,
        payload BLOB NOT NULL, created_at INTEGER NOT NULL,
        expires_at INTEGER NOT NULL, last_access INTEGER NOT NULL
    )""")
    con.execute("CREATE INDEX IF NOT EXISTS cache_expiry_idx ON cache_entries(expires_at)")
    return con

def put(con, identity, payload, ttl_seconds=86400, now=None):
    cache_key = key_for(identity)
    if type(ttl_seconds) is not int or not 1 <= ttl_seconds <= MAX_AGE:
        raise CacheError("INVALID_TTL")
    if type(payload) is not dict or payload.get("state") != "HISTORICAL_ONLY":
        raise CacheError("UNVERIFIED_PAYLOAD")
    if payload.get("source_revision") != identity["source_revision"]:
        raise CacheError("SOURCE_REVISION_MISMATCH")
    if payload.get("complete") is not True:
        raise CacheError("INCOMPLETE_PAYLOAD")
    raw = canonical(payload)
    if len(raw) > MAX_OUTPUT:
        raise CacheError("OUTPUT_TOO_LARGE")
    now = int(time.time()) if now is None else now
    content_hash = hashlib.sha256(raw).hexdigest()
    with con:
        con.execute("DELETE FROM cache_entries WHERE expires_at<=?", (now,))
        con.execute("""INSERT INTO cache_entries
            (cache_key,identity_json,source_revision,content_hash,payload,created_at,expires_at,last_access)
            VALUES (?,?,?,?,?,?,?,?)
            ON CONFLICT(cache_key) DO UPDATE SET
            identity_json=excluded.identity_json,
            source_revision=excluded.source_revision,
            content_hash=excluded.content_hash,
            payload=excluded.payload,
            created_at=excluded.created_at,
            expires_at=excluded.expires_at,
            last_access=excluded.last_access""",
            (cache_key, canonical(identity).decode(), identity["source_revision"],
             content_hash, raw, now, now + ttl_seconds, now))
        con.execute("""DELETE FROM cache_entries WHERE cache_key IN
            (SELECT cache_key FROM cache_entries ORDER BY last_access DESC, cache_key DESC LIMIT -1 OFFSET ?)""",
            (MAX_ENTRIES,))
    return {"state": "READY", "cache_key": cache_key, "sha256": content_hash}

def get(con, identity, now=None):
    cache_key = key_for(identity)
    now = int(time.time()) if now is None else now
    row = con.execute("""SELECT identity_json,content_hash,payload,expires_at
        FROM cache_entries WHERE cache_key=?""", (cache_key,)).fetchone()
    if row is None:
        return {"state": "MISS"}
    ident, expected, raw, expires = row
    if expires <= now:
        return {"state": "EXPIRED"}
    if len(raw) > MAX_OUTPUT or hashlib.sha256(raw).hexdigest() != expected:
        return {"state": "CORRUPT"}
    try:
        if json.loads(ident) != identity:
            return {"state": "STALE"}
        payload = json.loads(raw)
        if payload.get("source_revision") != identity["source_revision"] or payload.get("complete") is not True:
            return {"state": "STALE"}
    except (ValueError, TypeError, AttributeError):
        return {"state": "CORRUPT"}
    with con:
        con.execute("UPDATE cache_entries SET last_access=? WHERE cache_key=?", (now, cache_key))
    return {"state": "HIT", "sha256": expected, "payload": payload}

def compute_mtf(identity, source):
    """Offline bounded 1m candle/footprint aggregation, no source database reads."""
    key_for(identity)
    if identity["source"] != "grid" or identity["dataset"] != "candles_1m":
        raise CacheError("UNSUPPORTED_DATASET")
    minutes = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440}.get(identity["timeframe"])
    if minutes is None:
        raise CacheError("UNSUPPORTED_TIMEFRAME")
    if type(source) is not dict or set(source) != {"source_revision", "candles", "footprint"}:
        raise CacheError("INVALID_INPUT")
    if source["source_revision"] != identity["source_revision"]:
        raise CacheError("SOURCE_REVISION_MISMATCH")
    candles, footprint = source["candles"], source["footprint"]
    if type(candles) is not list or type(footprint) is not list or len(candles) > 10000 or len(footprint) > 50000:
        raise CacheError("RESOURCE_LIMIT")
    groups, by_ts = {}, {}
    for c in candles:
        if type(c) is not dict or c.get("symbol") != identity["symbol"]:
            raise CacheError("INVALID_CANDLE")
        t = c.get("ts")
        if type(t) is not int or t % 60000 or not identity["from_ms"] <= t <= identity["to_ms"] or t in by_ts:
            raise CacheError("INVALID_CANDLE")
        for field in ("open", "high", "low", "close", "buy_volume", "sell_volume"):
            if type(c.get(field)) not in (int, float) or not __import__("math").isfinite(c[field]):
                raise CacheError("INVALID_CANDLE")
        if c["low"] > min(c["open"], c["close"]) or c["high"] < max(c["open"], c["close"]) or min(c["buy_volume"], c["sell_volume"]) < 0:
            raise CacheError("INVALID_CANDLE")
        by_ts[t] = c
        bucket = (t // (minutes * 60000)) * minutes * 60000
        groups.setdefault(bucket, []).append(c)
    levels = {}
    for r in footprint:
        if type(r) is not dict or r.get("symbol") != identity["symbol"]:
            raise CacheError("INVALID_FOOTPRINT")
        t, price = r.get("ts"), r.get("price")
        if type(t) is not int or t not in by_ts or type(price) not in (int, float) or not __import__("math").isfinite(price):
            raise CacheError("INVALID_FOOTPRINT")
        if any(type(r.get(k)) not in (int, float) or not __import__("math").isfinite(r[k]) or r[k] < 0 for k in ("buy_volume", "sell_volume")):
            raise CacheError("INVALID_FOOTPRINT")
        bucket = (t // (minutes * 60000)) * minutes * 60000
        cell = levels.setdefault(bucket, {}).setdefault(str(price), dict(price=price, buy_volume=0, sell_volume=0))
        cell["buy_volume"] += r["buy_volume"]
        cell["sell_volume"] += r["sell_volume"]
    result = []
    for bucket, rows in sorted(groups.items()):
        rows.sort(key=lambda c: c["ts"])
        complete = len(rows) == minutes and all(c["ts"] == bucket + i * 60000 for i, c in enumerate(rows))
        buy = sum(c["buy_volume"] for c in rows)
        sell = sum(c["sell_volume"] for c in rows)
        cells = [dict(x, volume=x["buy_volume"] + x["sell_volume"], delta=x["buy_volume"] - x["sell_volume"]) for x in levels.get(bucket, {}).values()]
        cells.sort(key=lambda x: -x["price"])
        footprint_complete = complete and all(any(r["ts"] == c["ts"] for r in footprint) for c in rows)
        result.append(dict(ts=bucket, open=rows[0]["open"], high=max(c["high"] for c in rows),
            low=min(c["low"] for c in rows), close=rows[-1]["close"],
            buy_volume=buy, sell_volume=sell, volume=buy + sell, delta=buy - sell,
            complete=complete, footprint_complete=footprint_complete, levels=cells,
            poc_price=(min((x for x in cells if x["volume"] == max(y["volume"] for y in cells)), key=lambda x: x["price"])["price"] if cells and footprint_complete else None)))
    # Partial periods are never written as complete authoritative cache entries.
    return dict(state="HISTORICAL_ONLY", source_revision=identity["source_revision"],
        complete=bool(result) and all(r["complete"] and r["footprint_complete"] for r in result),
        candles=result)

def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline visualization cache; no upstream I/O")
    parser.add_argument("--db", required=True)
    parser.add_argument("--identity", required=True)
    parser.add_argument("--payload")
    parser.add_argument("--ttl", type=int, default=86400)
    parser.add_argument("action", choices=("put", "get", "stats", "compute"))
    args = parser.parse_args(argv)
    try:
        if args.action != "stats":
            identity_path = Path(args.identity)
            if identity_path.stat().st_size > MAX_INPUT:
                raise CacheError("INPUT_TOO_LARGE")
            identity = json.loads(identity_path.read_text(encoding="utf8"))
        con = open_cache(args.db)
        try:
            if args.action in ("put", "compute"):
                if not args.payload:
                    raise CacheError("PAYLOAD_REQUIRED")
                path = Path(args.payload)
                if path.stat().st_size > MAX_INPUT:
                    raise CacheError("INPUT_TOO_LARGE")
                source = json.loads(path.read_text(encoding="utf8"))
                result = put(con, identity, compute_mtf(identity, source) if args.action == "compute" else source, args.ttl)
            elif args.action == "get":
                result = get(con, identity)
            else:
                result = {"state": "READY", "entries": con.execute("SELECT count(*) FROM cache_entries").fetchone()[0]}
        finally:
            con.close()
        print(json.dumps(result, sort_keys=True))
        return 0 if result["state"] in ("READY", "HIT") else 2
    except (CacheError, OSError, ValueError, sqlite3.Error) as exc:
        # Never print source file paths, DSNs or raw driver messages.
        print(json.dumps({"state": "ERROR", "code": exc.args[0] if isinstance(exc, CacheError) else "LOCAL_IO_ERROR"}))
        return 3

if __name__ == "__main__":
    sys.exit(main())

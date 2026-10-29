"""Isolated SQLite visualization cache, never the Grid/Strattester source of truth.

Opt-in CLI, local filesystem only. No network, PostgreSQL or upstream imports.
Entries are derived from operator-supplied bounded, immutable JSON snapshots.
A source revision + algorithm version is mandatory to avoid stale reuse.
"""
from __future__ import annotations
import argparse
import contextlib
import hashlib
import json
import os
import sqlite3
import sys
import time
import math
import uuid
from pathlib import Path

SCHEMA = 1
ALGORITHM = "saved-mtf-cache-v2"
EXACT_INDEX = 'cache_jobs_exact_v2_idx'
MAX_INPUT = 4 * 1024 * 1024
MAX_OUTPUT = 4 * 1024 * 1024
MAX_ENTRIES = 256
MAX_AGE = 30 * 86400

class CacheError(ValueError):
    pass

PERIODS={"1m":1,"5m":5,"15m":15,"1h":60,"4h":240,"1d":1440}

@contextlib.contextmanager
def transaction(con):
    """Connection is autocommit: `with con` alone is NOT a transaction."""
    nested=con.in_transaction;name='cache_'+uuid.uuid4().hex
    con.execute('SAVEPOINT '+name if nested else 'BEGIN IMMEDIATE')
    try:
        yield
        con.execute('RELEASE '+name if nested else 'COMMIT')
    except BaseException:
        if nested:
            con.execute('ROLLBACK TO '+name);con.execute('RELEASE '+name)
        elif con.in_transaction:con.execute('ROLLBACK')
        raise

def validate_payload(identity,payload):
    """Validate whole requested interval, not just the blocks that happen to exist."""
    key_for(identity)
    minutes=PERIODS.get(identity['timeframe']);start,end=identity['from_ms'],identity['to_ms']
    if not minutes or start%(minutes*60000) or (end+60000)%(minutes*60000):raise CacheError('INCOMPLETE_PAYLOAD')
    if type(payload) is not dict or set(payload)!={'state','source_revision','complete','candles'} or payload['state']!='HISTORICAL_ONLY' or payload['complete'] is not True:raise CacheError('UNVERIFIED_PAYLOAD')
    if payload['source_revision']!=identity['source_revision']:raise CacheError('SOURCE_REVISION_MISMATCH')
    rows=payload['candles'];expected=(end-start+60000)//(minutes*60000)
    if type(rows) is not list or not 1<=len(rows)<=10000 or len(rows)!=expected:raise CacheError('INCOMPLETE_PAYLOAD')
    def numeric(v):
        if type(v) not in (int,float) or not math.isfinite(v):raise CacheError('INVALID_PAYLOAD')
        return v
    def equal(a,b):return math.isclose(a,b,rel_tol=1e-8,abs_tol=1e-8)
    cells=0
    for i,row in enumerate(rows):
        if type(row) is not dict or type(row.get('ts')) is not int or row['ts']!=start+i*minutes*60000 or row.get('complete') is not True or row.get('footprint_complete') is not True:raise CacheError('INCOMPLETE_PAYLOAD')
        for k in ('open','high','low','close','buy_volume','sell_volume','volume','delta'):numeric(row.get(k))
        if min(row[k] for k in ('open','high','low','close'))<=0 or not row['low']<=min(row['open'],row['close'])<=max(row['open'],row['close'])<=row['high']:raise CacheError('INVALID_PAYLOAD')
        if min(row['buy_volume'],row['sell_volume'],row['volume'])<0 or not equal(row['volume'],row['buy_volume']+row['sell_volume']) or not equal(row['delta'],row['buy_volume']-row['sell_volume']):raise CacheError('INVALID_PAYLOAD')
        levels=row.get('levels')
        if type(levels) is not list:raise CacheError('INVALID_PAYLOAD')
        cells+=len(levels)
        if cells>50000:raise CacheError('RESOURCE_LIMIT')
        prices=set();buy=sell=0
        for level in levels:
            if type(level) is not dict:raise CacheError('INVALID_PAYLOAD')
            for k in ('price','buy_volume','sell_volume','volume','delta'):numeric(level.get(k))
            if level['price']<=0 or level['price'] in prices or min(level['buy_volume'],level['sell_volume'],level['volume'])<0 or not equal(level['volume'],level['buy_volume']+level['sell_volume']) or not equal(level['delta'],level['buy_volume']-level['sell_volume']):raise CacheError('INVALID_PAYLOAD')
            prices.add(level['price']);buy+=level['buy_volume'];sell+=level['sell_volume']
        if not equal(buy,row['buy_volume']) or not equal(sell,row['sell_volume']):raise CacheError('INCOMPLETE_PAYLOAD')
        maximum=max((x['volume'] for x in levels),default=0)
        poc=min((x['price'] for x in levels if x['volume']==maximum),default=None) if maximum>0 else None
        if poc is not None:numeric(row.get('poc_price'))
        if row.get('poc_price')!=poc:raise CacheError('INVALID_PAYLOAD')

def prepare(identity,payload):
    validate_payload(identity,payload)
    raw=canonical(payload)
    if len(raw)>MAX_OUTPUT:raise CacheError('OUTPUT_TOO_LARGE')
    h=hashlib.sha256(raw).hexdigest();rows=payload['candles']
    view=dict(state='READY',authority='OFFLINE_ONLY',dataset=identity['dataset'],symbol=identity['symbol'],
        timeframe=identity['timeframe'],source_revision=identity['source_revision'],sha256=h,
        from_ms=identity['from_ms'],to_ms=identity['to_ms'],algorithm=identity['algorithm'],
        parameters_hash=identity['parameters_hash'],total_candles=len(rows),truncated=len(rows)>64,
        integrity_scope='PREVIEW_SHA256_WORKER_VALIDATED_FULL_DIGEST',
        candles=[{k:c[k] for k in ('ts','open','high','low','close','volume','delta')} for c in rows[:64]])
    preview=canonical(view)
    if len(preview)>32768:raise CacheError('OUTPUT_TOO_LARGE')
    return key_for(identity),raw,h,preview,hashlib.sha256(preview).hexdigest()

def write_entry(con,identity,prepared,ttl,now):
    key,raw,h,preview,preview_hash=prepared
    preview,preview_hash=materialize_preview(prepared,now+ttl)
    con.execute('DELETE FROM cache_entries WHERE expires_at<=?',(now,))
    con.execute('''INSERT INTO cache_entries VALUES(?,?,?,?,?,?,?,?)
        ON CONFLICT(cache_key) DO UPDATE SET identity_json=excluded.identity_json,
        source_revision=excluded.source_revision,content_hash=excluded.content_hash,
        payload=excluded.payload,created_at=excluded.created_at,expires_at=excluded.expires_at,
        last_access=excluded.last_access''',(key,canonical(identity).decode(),identity['source_revision'],h,raw,now,now+ttl,now))
    con.execute('INSERT OR REPLACE INTO cache_previews VALUES(?,?,?,?,?)',(key,h,key,preview_hash,preview))
    con.execute('''DELETE FROM cache_entries WHERE cache_key IN
        (SELECT cache_key FROM cache_entries ORDER BY last_access DESC,cache_key DESC LIMIT -1 OFFSET ?)''',(MAX_ENTRIES,))

def materialize_preview(prepared,expires):
    view=json.loads(prepared[3]);view['expires_at']=expires;raw=canonical(view)
    if len(raw)>32768:raise CacheError('OUTPUT_TOO_LARGE')
    return raw,hashlib.sha256(raw).hexdigest()

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
    con.execute('''CREATE TABLE IF NOT EXISTS cache_previews(
        cache_key TEXT PRIMARY KEY,entry_hash TEXT NOT NULL,identity_hash TEXT NOT NULL,
        content_hash TEXT NOT NULL,payload BLOB NOT NULL)''')
    con.execute('''CREATE TRIGGER IF NOT EXISTS cache_preview_update AFTER UPDATE OF
        cache_key,payload,content_hash,identity_json,source_revision,expires_at ON cache_entries
        BEGIN DELETE FROM cache_previews WHERE cache_key=OLD.cache_key; END''')
    con.execute('''CREATE TRIGGER IF NOT EXISTS cache_preview_delete AFTER DELETE ON cache_entries
        BEGIN DELETE FROM cache_previews WHERE cache_key=OLD.cache_key; END''')
    return con

def put(con, identity, payload, ttl_seconds=86400, now=None):
    cache_key = key_for(identity)
    if type(ttl_seconds) is not int or not 1 <= ttl_seconds <= MAX_AGE:
        raise CacheError("INVALID_TTL")
    prepared=prepare(identity,payload)
    now=int(time.time()) if now is None else int(now)
    with transaction(con):write_entry(con,identity,prepared,ttl_seconds,now)
    content_hash=prepared[2]

    return {"state": "READY", "cache_key": cache_key, "sha256": content_hash}

def get(con, identity, now=None):
    cache_key = key_for(identity)
    now = int(time.time()) if now is None else now
    row = con.execute("""SELECT CASE WHEN length(identity_json)<=4096 THEN identity_json END,
        content_hash,CASE WHEN length(payload)<=4194304 THEN payload END,expires_at,source_revision
        FROM cache_entries WHERE cache_key=?""", (cache_key,)).fetchone()
    if row is None:
        return {"state": "MISS"}
    ident, expected, raw, expires, revision = row
    if type(expires) is not int:return {'state':'CORRUPT'}
    if revision!=identity['source_revision']:return {'state':'STALE'}
    if expires <= now:
        return {"state": "EXPIRED"}
    if not isinstance(raw,bytes) or len(raw) > MAX_OUTPUT or hashlib.sha256(raw).hexdigest() != expected:
        return {"state": "CORRUPT"}
    try:
        if json.loads(ident) != identity:
            return {"state": "STALE"}
        payload = json.loads(raw)
        validate_payload(identity,payload)
        if payload.get("source_revision") != identity["source_revision"] or payload.get("complete") is not True:
            return {"state": "STALE"}
    except (ValueError, TypeError, AttributeError):
        return {"state": "CORRUPT"}
    with transaction(con):
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
    if type(source) is not dict or set(source)-{"source_revision","candles","footprint","zero_trade_minutes"} or not {"source_revision","candles","footprint"}<=set(source):
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
        if min(c[k] for k in ("open","high","low","close"))<=0 or c["low"] > min(c["open"], c["close"]) or c["high"] < max(c["open"], c["close"]) or min(c["buy_volume"], c["sell_volume"]) < 0:
            raise CacheError("INVALID_CANDLE")
        by_ts[t] = c
        bucket = (t // (minutes * 60000)) * minutes * 60000
        groups.setdefault(bucket, []).append(c)
    zero_minutes=source.get('zero_trade_minutes',[])
    if type(zero_minutes) is not list or len(zero_minutes)>10000 or any(type(t) is not int or t not in by_ts or by_ts[t]['buy_volume']!=0 or by_ts[t]['sell_volume']!=0 for t in zero_minutes) or len(set(zero_minutes))!=len(zero_minutes):raise CacheError('INVALID_FOOTPRINT')
    zero_minutes=set(zero_minutes)
    levels = {};minute_totals={};seen_levels=set()
    for r in footprint:
        if type(r) is not dict or r.get("symbol") != identity["symbol"]:
            raise CacheError("INVALID_FOOTPRINT")
        t, price = r.get("ts"), r.get("price")
        if type(t) is not int or t not in by_ts or type(price) not in (int, float) or not __import__("math").isfinite(price):
            raise CacheError("INVALID_FOOTPRINT")
        if any(type(r.get(k)) not in (int, float) or not __import__("math").isfinite(r[k]) or r[k] < 0 for k in ("buy_volume", "sell_volume")):
            raise CacheError("INVALID_FOOTPRINT")
        if price<=0 or (t,price) in seen_levels:raise CacheError("INVALID_FOOTPRINT")
        seen_levels.add((t,price));totals=minute_totals.setdefault(t,[0,0])
        totals[0]+=r['buy_volume'];totals[1]+=r['sell_volume']
        bucket = (t // (minutes * 60000)) * minutes * 60000
        cell = levels.setdefault(bucket, {}).setdefault(price, dict(price=price, buy_volume=0, sell_volume=0))
        cell["buy_volume"] += r["buy_volume"]
        cell["sell_volume"] += r["sell_volume"]
    result = []
    for bucket, rows in sorted(groups.items()):
        rows.sort(key=lambda c: c["ts"])
        complete = len(rows) == minutes and all(c.get("complete",True) is True for c in rows) and all(c["ts"] == bucket + i * 60000 for i, c in enumerate(rows))
        buy = sum(c["buy_volume"] for c in rows)
        sell = sum(c["sell_volume"] for c in rows)
        cells = [dict(x, volume=x["buy_volume"] + x["sell_volume"], delta=x["buy_volume"] - x["sell_volume"]) for x in levels.get(bucket, {}).values()]
        cells.sort(key=lambda x: -x["price"])
        footprint_complete = complete and all(c['ts'] in minute_totals or c['ts'] in zero_minutes for c in rows) and all(math.isclose(minute_totals.get(c['ts'],[0,0])[i],c[k],rel_tol=1e-8,abs_tol=1e-8) for c in rows for i,k in enumerate(('buy_volume','sell_volume')))
        max_volume=max((x['volume'] for x in cells),default=0)
        result.append(dict(ts=bucket, open=rows[0]["open"], high=max(c["high"] for c in rows),
            low=min(c["low"] for c in rows), close=rows[-1]["close"],
            buy_volume=buy, sell_volume=sell, volume=buy + sell, delta=buy - sell,
            complete=complete, footprint_complete=footprint_complete, levels=cells,
            poc_price=(min((x for x in cells if x["volume"] == max_volume), key=lambda x: x["price"])["price"] if max_volume>0 and footprint_complete else None)))
    # Partial periods are never written as complete authoritative cache entries.
    return dict(state="HISTORICAL_ONLY", source_revision=identity["source_revision"],
        complete=bool(result) and identity['from_ms']%(minutes*60000)==0 and (identity['to_ms']+60000)%(minutes*60000)==0 and len(by_ts)==(identity['to_ms']-identity['from_ms'])//60000+1 and all(r["complete"] and r["footprint_complete"] for r in result),
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

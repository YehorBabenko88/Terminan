"""Strict read-only future source boundary; no I/O, DB drivers or network calls.

Consumers pass decoded, trusted-transport JSON envelopes here after an explicit
operator-authorized adapter is implemented. This module does not activate one.
"""
from __future__ import annotations
import math
import re
from datetime import datetime, timezone

SOURCES = frozenset(("grid", "strattester"))
KINDS = {"grid": frozenset(("candles", "footprint", "book")),
         "strattester": frozenset(("candles", "research"))}
STATES = frozenset(("HISTORICAL_ONLY", "NO_DATA", "PARTIAL", "STALE", "DISCONNECTED"))
SYMBOL = re.compile(r"^[A-Z0-9]{2,30}$")
TIMEFRAMES = frozenset(("1m", "5m", "15m", "1h", "4h", "1d"))
MAX_ROWS = 1000

class SourceContractError(ValueError):
    """Untrusted or unsupported source payload; never silently substitute data."""

def unavailable(source: str, kind: str) -> dict:
    if source not in SOURCES or kind not in KINDS[source]:
        raise SourceContractError("unsupported source")
    return {"version": 1, "source": source, "kind": kind,
            "state": "DISCONNECTED", "authority": "UNVERIFIED",
            "rows": [], "runtime_source": "NONE"}

def _timestamp(value: object) -> int:
    if type(value) is not int or not 946684800000 <= value <= 2**53 - 1:
        raise SourceContractError("invalid UTC millisecond timestamp")
    return value

def _number(value: object) -> None:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise SourceContractError("invalid numeric field")

def validate_envelope(payload: object, *, expected_source: str,
                      expected_kind: str, expected_symbol: str,
                      now_ms: int) -> dict:
    """Validate a bounded, explicitly sourced historical response.

    This checks transport-neutral identity, structure, chronology and semantics.
    Source-specific schema/provenance and publication authority must ALSO be
    verified by a future adapter before this envelope can be trusted.
    """
    _timestamp(now_ms)
    if expected_source not in SOURCES or expected_kind not in KINDS[expected_source]:
        raise SourceContractError("unsupported source")
    if not isinstance(expected_symbol, str) or not SYMBOL.fullmatch(expected_symbol):
        raise SourceContractError("invalid symbol")
    keys = {"version", "source", "kind", "symbol", "timeframe", "state",
            "authority", "runtime_source", "source_revision", "as_of_ms",
            "coverage", "rows"}
    if type(payload) is not dict or set(payload) != keys:
        raise SourceContractError("invalid envelope fields")
    if type(payload["version"]) is not int or payload["version"] != 1:
        raise SourceContractError("unsupported version")
    if (payload["source"], payload["kind"], payload["symbol"]) != (
        expected_source, expected_kind, expected_symbol):
        raise SourceContractError("source identity mismatch")
    if payload["state"] not in STATES or payload["authority"] != "HISTORICAL_ONLY":
        raise SourceContractError("invalid authority")
    if payload["runtime_source"] not in ("POSTGRESQL_READ_ONLY", "SQLITE_READ_ONLY"):
        raise SourceContractError("invalid runtime source")
    if (expected_source == "grid" and payload["runtime_source"] != "POSTGRESQL_READ_ONLY"
        or expected_source == "strattester" and payload["runtime_source"] != "SQLITE_READ_ONLY"):
        raise SourceContractError("source transport mismatch")
    if not isinstance(payload["source_revision"], str) or not re.fullmatch(
        r"[a-f0-9]{40}", payload["source_revision"]):
        raise SourceContractError("invalid revision")
    timeframe = payload["timeframe"]
    if expected_kind == "research":
        if timeframe is not None:
            raise SourceContractError("research timeframe must be null")
    elif timeframe not in TIMEFRAMES:
        raise SourceContractError("unsupported timeframe")
    as_of = _timestamp(payload["as_of_ms"])
    if as_of > now_ms:
        raise SourceContractError("future observation")
    coverage = payload["coverage"]
    if type(coverage) is not dict or set(coverage) != {"from_ms", "to_ms", "complete"}:
        raise SourceContractError("invalid coverage")
    start, end = _timestamp(coverage["from_ms"]), _timestamp(coverage["to_ms"])
    if start > end or end > as_of or type(coverage["complete"]) is not bool:
        raise SourceContractError("invalid coverage chronology")
    rows = payload["rows"]
    if type(rows) is not list or len(rows) > MAX_ROWS:
        raise SourceContractError("unbounded rows")
    if payload["state"] in ("NO_DATA", "DISCONNECTED") and rows:
        raise SourceContractError("rows present for unavailable source")
    if payload["state"] == "HISTORICAL_ONLY" and not coverage["complete"]:
        raise SourceContractError("incomplete coverage")
    if payload["state"] == "PARTIAL" and coverage["complete"]:
        raise SourceContractError("partial state contradiction")
    for row in rows:
        if type(row) is not dict or row.get("symbol") != expected_symbol:
            raise SourceContractError("row identity mismatch")
        if expected_kind == "research":
            if not {"run_id", "strategy_id", "strategy_version", "created_at_ms", "metrics", "publication_state"} <= set(row):
                raise SourceContractError("invalid research row")
            if row["publication_state"] != "PUBLISHED_UNVERIFIED":
                raise SourceContractError("unpublished research")
            if type(row["metrics"]) is not dict:
                raise SourceContractError("invalid metrics")
            _timestamp(row["created_at_ms"])
            if row["created_at_ms"] > as_of:
                raise SourceContractError("future research")
            for value in row["metrics"].values():
                if value is not None:
                    _number(value)
        else:
            if "t" not in row:
                raise SourceContractError("missing timestamp")
            t = _timestamp(row["t"])
            if not start <= t <= end:
                raise SourceContractError("row outside coverage")
            if expected_kind == "candles":
                for field in ("open", "high", "low", "close", "volume"):
                    _number(row.get(field))
                if not row["low"] <= min(row["open"], row["close"]) <= max(row["open"], row["close"]) <= row["high"]:
                    raise SourceContractError("invalid OHLC")
                if row["volume"] < 0:
                    raise SourceContractError("negative volume")
            elif expected_kind == "footprint":
                for field in ("price", "buy_volume", "sell_volume", "volume", "delta"):
                    _number(row.get(field))
                if min(row["buy_volume"], row["sell_volume"], row["volume"]) < 0:
                    raise SourceContractError("negative footprint")
                if not math.isclose(row["buy_volume"] + row["sell_volume"], row["volume"], rel_tol=1e-8, abs_tol=1e-8):
                    raise SourceContractError("volume mismatch")
            elif expected_kind == "book":
                raise SourceContractError("book requires separate snapshot sequence contract")
    return payload

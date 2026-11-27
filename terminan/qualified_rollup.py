"""Strict non-authorizing consumer of canonical Grid 5m/15m rollup DTO.

B owns source qualification, windows and numeric aggregation. This adapter
validates declared fields, provenance digests, clock/coverage and Math numeric
integrity independently; it does NOT reaggregate 1m records or grant trust.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import time
import uuid

from market_math import candle_ohlcv_valid, executed_volume_delta, exact_sum
from decimal import Decimal

_WINDOWS = {"5m": 5, "15m": 15}
_SHA = re.compile(r"[a-f0-9]{64}\Z")
_SHA40 = re.compile(r"[a-f0-9]{40}\Z")
_SYMBOL = re.compile(r"[A-Z0-9]{2,30}\Z")
_TOP = frozenset({
    "schema", "api_version", "producer", "symbol", "timeframe", "limit",
    "status", "reason", "source_timeframe", "source_minutes",
    "parent_dataset_fingerprint", "source_revision", "producer_epoch",
    "coverage", "record_integrity", "source_authenticity",
    "exchange_completeness", "quality_attestation", "storage_immutability",
    "immutable", "read_only", "execution_authority", "trading_authorized",
    "paper_admitted", "rows", "dataset_fingerprint", "source_declared_quality",
})
_ROW = frozenset({
    "start_ms", "end_ms", "open", "high", "low", "close",
    "buy_volume", "sell_volume", "delta", "trade_count",
    "source_minute_fingerprints",
})
_MAX_TIME = 2**53-1
_MAX_RESPONSE_BYTES = 8_388_608
_HISTORICAL_ONLY = frozenset({"freshness_mode", "as_of_ms", "live_freshness", "historical_source_trust"})


def _digest(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False).encode("ascii")).hexdigest()


def _need(condition):
    if condition is not True:
        raise ValueError("QUALIFIED_ROLLUP_UNAVAILABLE")


def _amount(value, *, positive=False):
    # JSON floats are already normalized by B's binary64 DTO. The canonical
    # Math kernel owns numerical domain; consumer never rounds or sums.
    _need(type(value) in (int, float))
    number = Decimal(str(value))
    _need(number.is_finite())
    if positive:
        _need(number > 0)
    else:
        _need(number >= 0)
    return number


def validate_qualified_rollup(envelope, symbol, timeframe, limit, *,
                              now_ms=None, historical=False,
                              before_ms=None, as_of_ms=None):
    """Validate one already managed B rollup page, then detach its rows.

    This is an integrity/shape check, NOT source authenticity attestation.
    Exact LIVE and HISTORICAL_AS_OF contracts are separate. A historical
    observation cutoff never supplies exchange or historical snapshot trust.
    """
    try:
        _need(type(symbol) is str and _SYMBOL.fullmatch(symbol) is not None)
        _need(type(timeframe) is str and timeframe in _WINDOWS)
        _need(type(limit) is int and 1 <= limit <= 5)
        _need(type(historical) is bool)
        now = int(time.time()*1000) if now_ms is None else now_ms
        _need(type(now) is int and 0 < now <= _MAX_TIME)
        period = _WINDOWS[timeframe] * 60000
        if historical:
            _need(type(before_ms) is int and type(as_of_ms) is int
                  and 0 < before_ms <= as_of_ms <= now
                  and before_ms % period == 0 and as_of_ms % 60000 == 0
                  and as_of_ms - before_ms <= 30 * 86400000)
        else:
            _need(before_ms is None and as_of_ms is None)
        _need(type(envelope) is dict
              and set(envelope) == (_TOP | _HISTORICAL_ONLY if historical else _TOP))
        _need(len(json.dumps(envelope, ensure_ascii=True,
                             separators=(",", ":"), allow_nan=False).encode("ascii")) <= _MAX_RESPONSE_BYTES)
        _need(envelope["schema"] ==
              ("market_data.historical-as-of-mtf-envelope.v1" if historical
               else "market_data.qualified-mtf-envelope.v1"))
        _need(type(envelope["source_declared_quality"]) is list
              and envelope["source_declared_quality"] == ["GOOD"])
        if historical:
            _need(envelope["freshness_mode"] == "HISTORICAL_AS_OF"
                  and envelope["live_freshness"] == "NOT_APPLICABLE"
                  and envelope["historical_source_trust"] == "NOT_INDEPENDENTLY_ATTESTED"
                  and type(envelope["as_of_ms"]) is int
                  and envelope["as_of_ms"] == as_of_ms)
        _need(type(envelope["api_version"]) is dict
              and envelope["api_version"] == {"major": 2, "minor": 0}
              and type(envelope["api_version"]["major"]) is int
              and type(envelope["api_version"]["minor"]) is int)
        for field, literal in (
            ("producer", "market_data"), ("symbol", symbol),
            ("timeframe", timeframe), ("limit", limit),
            ("status", "PARTIAL"),
            ("reason", "HISTORICAL_AS_OF_SOURCE_ONLY" if historical
             else "EXCHANGE_COMPLETENESS_UNATTESTED"),
            ("source_timeframe", "1m"),
            ("source_minutes", limit * _WINDOWS[timeframe]),
            ("record_integrity", "VERIFIED"),
            ("source_authenticity", "NOT_INDEPENDENTLY_ATTESTED"),
            ("exchange_completeness", "NOT_ATTESTED"),
            ("quality_attestation", "NOT_INDEPENDENTLY_ATTESTED"),
            ("storage_immutability", "NOT_ATTESTED"),
            ("immutable", False), ("read_only", True),
            ("execution_authority", False), ("trading_authorized", False),
            ("paper_admitted", False),
        ):
            _need(type(envelope[field]) is type(literal) and envelope[field] == literal)
        _need(type(envelope["source_revision"]) is str
              and _SHA40.fullmatch(envelope["source_revision"]) is not None)
        epoch = envelope["producer_epoch"]
        _need(type(epoch) is str and str(uuid.UUID(epoch)) == epoch
              and uuid.UUID(epoch).version == 4)
        _need(type(envelope["parent_dataset_fingerprint"]) is str
              and _SHA.fullmatch(envelope["parent_dataset_fingerprint"]) is not None)
        _need(type(envelope["dataset_fingerprint"]) is str
              and _SHA.fullmatch(envelope["dataset_fingerprint"]) is not None)
        _need(_digest({key:value for key,value in envelope.items()
                       if key != "dataset_fingerprint"}) == envelope["dataset_fingerprint"])
        expected = limit * _WINDOWS[timeframe]
        _need(type(envelope["coverage"]) is dict
              and set(envelope["coverage"]) == {"expected_minutes", "observed_minutes", "missing_minutes"}
              and all(type(envelope["coverage"][key]) is int for key in envelope["coverage"])
              and envelope["coverage"] == {"expected_minutes": expected, "observed_minutes": expected, "missing_minutes": 0})
        rows = envelope["rows"]
        _need(type(rows) is list and len(rows) == limit)
        previous = None
        observed_fingerprints = set()
        for row in rows:
            _need(type(row) is dict and set(row) == _ROW)
            start, end = row["start_ms"], row["end_ms"]
            _need(type(start) is int and type(end) is int
                  and 0 <= start <= _MAX_TIME and start % period == 0
                  and end == start + period - 1
                  and end < (as_of_ms if historical else now))
            if previous is not None:
                _need(start == previous + period)
            previous = start
            fps = row["source_minute_fingerprints"]
            _need(type(fps) is list and len(fps) == _WINDOWS[timeframe]
                  and all(type(value) is str and _SHA.fullmatch(value) is not None for value in fps))
            _need(all(value not in observed_fingerprints for value in fps)
                  and len(set(fps)) == len(fps))
            observed_fingerprints.update(fps)
            _need(type(row["trade_count"]) is int and 0 <= row["trade_count"] < 2**63)
            o,h,l,c = (_amount(row[k], positive=True) for k in ("open","high","low","close"))
            buy,sell,delta = (_amount(row[k]) if k!="delta"
                              else Decimal(str(row[k])) for k in ("buy_volume","sell_volume","delta"))
            _need(type(row["delta"]) in (int,float) and delta.is_finite())
            _need(candle_ohlcv_valid(o,h,l,c,buy) and candle_ohlcv_valid(o,h,l,c,sell))
            # B computes exact Decimal delta BEFORE rounding displayed buy/sell
            # to binary64. 1e16 + 0.01 can round back to 1e16, while the
            # original valid delta remains 0.01. Enforce the uncertainty of
            # the three displayed binary64 values instead of false equality.
            canonical_delta = executed_volume_delta(buy, sell)
            uncertainty = sum((
                Decimal(str(math.ulp(float(row[key])))) / 2
                for key in ("buy_volume", "sell_volume", "delta")
            ), Decimal(0))
            _need(abs(canonical_delta - delta) <= uncertainty)
        if historical:
            # A missing final bucket must not masquerade as the requested
            # historical cursor. Original B SQL uses start_ms < before_ms.
            _need(rows[-1]["end_ms"] == before_ms - 1)
        else:
            # Grid LIVE freshness remains 120s; never accept stale as live.
            _need(now - rows[-1]["end_ms"] <= 120000)
        return copy.deepcopy(envelope)
    except (KeyError, TypeError, ValueError, OverflowError, ArithmeticError,
            RecursionError, UnicodeError, AttributeError):
        raise ValueError("QUALIFIED_ROLLUP_UNAVAILABLE") from None


def chart_rollup_rows(checked):
    """Only detached bounded OHLCV/delta presentation, without POC or trade data."""
    return [{
        "t": row["start_ms"], "o": row["open"], "h": row["high"],
        "l": row["low"], "c": row["close"],
        "closed_at_ms": row["end_ms"] + 1,
        # Both directional totals have already been rounded by B's binary64
        # DTO. Math addition is exact *for these floats*, NOT original trade
        # volume precision. No retrospective source-value reconstruction.
        "v": str(exact_sum((Decimal(str(row["buy_volume"])),
                            Decimal(str(row["sell_volume"]))))),
        "volume_precision": "BINARY64_PRESENTATION_NOT_SOURCE_EXACT",
        "buy_volume": row["buy_volume"], "sell_volume": row["sell_volume"],
        "delta": row["delta"], "trade_count": row["trade_count"],
        "source_minute_fingerprints": tuple(row["source_minute_fingerprints"]),
    } for row in checked["rows"]]

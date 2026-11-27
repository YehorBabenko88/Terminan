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
_EXACT_TOP = frozenset({
    "decimal_contract", "numeric_presentation", "source_numeric_precision",
})
_EXACT_ROW = frozenset({
    "buy_volume_decimal", "sell_volume_decimal", "volume_decimal",
    "delta_decimal",
})
# Canonical Grid v2: fixed decimal, no exponent, leading zero, or trailing
# fractional zeros. Decimal string length and Math domain remain bounded.
_FIXED_DECIMAL = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?\Z")


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


def _exact_amount(value, *, signed=False):
    _need(type(value) is str and 0 < len(value) <= 4300)
    _need(_FIXED_DECIMAL.fullmatch(value) is not None)
    number = Decimal(value)
    _need(number.is_finite() and (signed or number >= 0))
    _need(not (number.is_zero() and value.startswith("-")))
    # Preserve normalized fixed ASCII: no Decimal context rounding, aliases,
    # or client-owned summation. Math checks all numeric domain constraints.
    canonical = "0" if number.is_zero() else format(number, "f")
    if "." in canonical:
        canonical = canonical.rstrip("0").rstrip(".")
    _need(canonical == value)
    return number


def _presentation_matches(exact_value, shown):
    # Source-exact Decimal is always authoritative. Only check that the
    # OPTIONAL B binary64 presentation corresponds to it when representable.
    try:
        rounded = float(exact_value)
    except OverflowError:
        rounded = float("inf")
    representable = math.isfinite(rounded) and (
        exact_value == 0 or rounded != 0)
    if representable:
        _need(type(shown) is float and math.isfinite(shown)
              and shown == rounded)
    else:
        _need(shown is None)


def validate_qualified_rollup(envelope, symbol, timeframe, limit, *,
                              now_ms=None, historical=False,
                              before_ms=None, as_of_ms=None, exact=False):
    """Validate one already managed B rollup page, then detach its rows.

    This is an integrity/shape check, NOT source authenticity attestation.
    Exact LIVE and HISTORICAL_AS_OF contracts are separate. A historical
    observation cutoff never supplies exchange or historical snapshot trust.
    """
    try:
        _need(type(symbol) is str and _SYMBOL.fullmatch(symbol) is not None)
        _need(type(timeframe) is str and timeframe in _WINDOWS)
        _need(type(limit) is int and 1 <= limit <= 5)
        _need(type(historical) is bool and type(exact) is bool)
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
        expected_top = (_TOP - {"source_declared_quality"} | _EXACT_TOP
                        if exact else _TOP)
        if historical:
            expected_top = expected_top | _HISTORICAL_ONLY
        _need(type(envelope) is dict and set(envelope) == expected_top)
        _need(len(json.dumps(envelope, ensure_ascii=True,
                             separators=(",", ":"), allow_nan=False).encode("ascii")) <= _MAX_RESPONSE_BYTES)
        schema = ("market_data.historical-as-of-mtf-envelope"
                  if historical else "market_data.qualified-mtf-envelope")
        _need(envelope["schema"] == schema + (".v2" if exact else ".v1"))
        if exact:
            _need(envelope["decimal_contract"] == "CANONICAL_MATH_EXACT_STORED_1M"
                  and envelope["numeric_presentation"] == "DECIMAL_STRING_EXACT_STORED_INPUTS"
                  and envelope["source_numeric_precision"] ==
                  "STORED_1M_JSON_NUMBERS_NOT_PROVIDER_RAW")
        else:
            _need(type(envelope["source_declared_quality"]) is list
                  and envelope["source_declared_quality"] == ["GOOD"])
        if historical:
            _need(envelope["freshness_mode"] == "HISTORICAL_AS_OF"
                  and envelope["live_freshness"] == "NOT_APPLICABLE"
                  and envelope["historical_source_trust"] == "NOT_INDEPENDENTLY_ATTESTED"
                  and type(envelope["as_of_ms"]) is int
                  and envelope["as_of_ms"] == as_of_ms)
        _need(type(envelope["api_version"]) is dict
              and envelope["api_version"] == {"major": 2, "minor": 1 if exact else 0}
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
            _need(type(row) is dict and set(row) ==
                  (_ROW | _EXACT_ROW if exact else _ROW))
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
            if exact:
                buy = _exact_amount(row["buy_volume_decimal"])
                sell = _exact_amount(row["sell_volume_decimal"])
                volume = _exact_amount(row["volume_decimal"])
                delta = _exact_amount(row["delta_decimal"], signed=True)
                # Only canonical Math computes the exact total and delta.
                _need(exact_sum((buy, sell)) == volume)
                _need(executed_volume_delta(buy, sell) == delta)
                # Canonical Math's OHLCV predicate limits a *single* candle
                # volume to 128 coefficient digits. A valid Math sum of up
                # to 15 stored 1m candles may need 129 digits. Check prices
                # using Math and check exact signed/nonnegative totals with
                # exact_sum/executed_volume_delta above, not the single-minute
                # amount cap on an already aggregated source.
                _need(candle_ohlcv_valid(o,h,l,c,Decimal(0)))
                for name, amount in (("buy_volume", buy),
                                     ("sell_volume", sell), ("delta", delta)):
                    _presentation_matches(amount, row[name])
            else:
                buy,sell,delta = (_amount(row[k]) if k!="delta"
                                  else Decimal(str(row[k])) for k in
                                 ("buy_volume","sell_volume","delta"))
                _need(type(row["delta"]) in (int,float) and delta.is_finite())
                _need(candle_ohlcv_valid(o,h,l,c,buy)
                      and candle_ohlcv_valid(o,h,l,c,sell))
                # Original Grid v1 had only lossy binary64 presentation.
                # ULP is a display-consistency check, not source proof.
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
    """Detached source-exact Math rows; never permission, POC or fake OI."""
    exact = checked.get("numeric_presentation") == "DECIMAL_STRING_EXACT_STORED_INPUTS"
    return [{
        "t": row["start_ms"], "o": row["open"], "h": row["high"],
        "l": row["low"], "c": row["close"],
        "closed_at_ms": row["end_ms"] + 1,
        # Both directional totals have already been rounded by B's binary64
        # DTO. Math addition is exact *for these floats*, NOT original trade
        # volume precision. No retrospective source-value reconstruction.
        "v": (row["volume_decimal"] if exact else
              str(exact_sum((Decimal(str(row["buy_volume"])),
                             Decimal(str(row["sell_volume"])))))),
        "volume_precision": ("EXACT_STORED_1M_JSON_NUMBERS_NOT_PROVIDER_RAW" if exact
                             else "BINARY64_PRESENTATION_NOT_SOURCE_EXACT"),
        "buy_volume": row["buy_volume"], "sell_volume": row["sell_volume"],
        "delta": row["delta"], "trade_count": row["trade_count"],
        "source_minute_fingerprints": tuple(row["source_minute_fingerprints"]),
        **({
            "buy_volume_decimal": row["buy_volume_decimal"],
            "sell_volume_decimal": row["sell_volume_decimal"],
            "volume_decimal": row["volume_decimal"],
            "delta_decimal": row["delta_decimal"],
        } if exact else {}),
    } for row in checked["rows"]]

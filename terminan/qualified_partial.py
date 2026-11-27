"""Strict presentation-only read of Grid's immutable 1m provenance envelope.

SHA256 protects against accidental/transit mutation, NOT against a forged source.
The managed private capability is the transport identity gate. PARTIAL can be
displayed as unqualified observation only; no paper/strategy authorization.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import time
import uuid
from types import MappingProxyType

MAX_BYTES = 8 * 1024 * 1024
MAX_ROWS = 1000
_SHA40 = re.compile(r"[a-f0-9]{40}\Z")
_SHA64 = re.compile(r"[a-f0-9]{64}\Z")
_SYMBOL = re.compile(r"[A-Z0-9]{2,30}\Z")
_MAX_TIME = 2**53 - 1
_RECORD_KEYS = frozenset({
    "api_version", "producer", "source", "symbol", "timeframe",
    "start_ms", "end_ms", "source_event_start_ms", "source_event_end_ms",
    "ingestion_ms", "representation", "execution_authority",
    "quality_status", "quality_reasons", "coverage", "source_identity_verified",
    "status", "reason", "candle", "levels", "dataset_fingerprint"
})
_SOURCE_KEYS = frozenset({
    "identity", "source_revision", "epoch", "market_type", "representation"
})
_CANDLE_KEYS = frozenset({
    "open", "high", "low", "close", "buy_volume", "sell_volume",
    "delta", "trade_count", "poc_price"
})


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _digest(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def _clock(value):
    return type(value) is int and 0 <= value <= _MAX_TIME


def _version(value, major, minor):
    return (type(value) is dict and set(value) == {"major", "minor"}
            and type(value["major"]) is int and type(value["minor"]) is int
            and value["major"] == major and value["minor"] == minor)


def _nontrading(value):
    return (type(value) is dict
            and value.get("execution_authority") is False
            and value.get("trading_authorized", False) is False)


def _source(value):
    if (type(value) is not dict or set(value) != _SOURCE_KEYS
            or type(value.get("identity")) is not str
            or not 1 <= len(value["identity"]) <= 256):
        raise ValueError("SOURCE_IDENTITY_REQUIRED")
    if type(value.get("source_revision")) is not str or not _SHA40.fullmatch(value["source_revision"]):
        raise ValueError("SOURCE_REVISION_REQUIRED")
    try:
        epoch = value["epoch"]
        if type(epoch) is not str or str(uuid.UUID(epoch)) != epoch or uuid.UUID(epoch).version != 4:
            raise ValueError("epoch")
    except (ValueError, KeyError, TypeError, AttributeError):
        raise ValueError("SOURCE_EPOCH_REQUIRED") from None
    if value.get("market_type") != "linear" or value.get("representation") != "live_trade_aggregate":
        raise ValueError("SOURCE_MARKET_REPRESENTATION_REQUIRED")
    return value["identity"], value["source_revision"], value["epoch"]


def validate_partial(envelope, symbol, limit, *, now_ms=None):
    """Legacy v1.1 read receipt, retained for exact producer regression parity."""
    return _validate_page(envelope, symbol, limit, version="v1", now_ms=now_ms)


def validate_qualified_v2(envelope, symbol, limit, *, now_ms=None):
    """Consume B-owned qualified v2 DTO; no raw-v1 downgrade on failure."""
    return _validate_page(envelope, symbol, limit, version="v2", now_ms=now_ms)


_V2_KEYS = frozenset({
    "schema", "api_version", "producer", "read_only", "symbol", "timeframe",
    "limit", "status", "reason", "record_integrity",
    "source_declared_quality", "quality_attestation", "source_authenticity",
    "exchange_completeness", "coverage", "freshness_utc_ms",
    "source_revision", "producer_epoch", "dataset_fingerprint",
    "rows", "immutable", "storage_immutability",
    "execution_authority", "trading_authorized", "paper_admitted"
})


def _validate_page(envelope, symbol, limit, *, version, now_ms=None):
    """Return detached, display-only receipt, with one Math/record validator.

    This validates BOTH the page digest and every constituent record digest.
    Freshness is based on source-event time; local reception time is not proof.
    The sender remains EXTERNALLY_UNATTESTED even with matching hashes.
    """
    if type(symbol) is not str or not _SYMBOL.fullmatch(symbol):
        raise ValueError("SYMBOL_REQUIRED")
    if type(limit) is not int or not 1 <= limit <= MAX_ROWS:
        raise ValueError("LIMIT_REQUIRED")
    if now_ms is None:
        now_ms = int(time.time() * 1000)
    if not _clock(now_ms):
        raise ValueError("CURRENT_TIME_REQUIRED")
    if type(envelope) is not dict:
        raise ValueError("ENVELOPE_REQUIRED")
    try:
        if version == "v1":
            if (not _version(envelope.get("api_version"), 1, 1)
                    or envelope.get("producer") != "market_data"
                    or envelope.get("read_only") is not True
                    or envelope.get("status") != "PARTIAL"
                    or envelope.get("reason") != "EXCHANGE_COMPLETENESS_UNATTESTED"
                    or envelope.get("data_quality_status") != "PARTIAL"
                    or envelope.get("representation") != "historical_aggregate"
                    or envelope.get("symbol") != symbol
                    or envelope.get("timeframe") != "1m"
                    or type(envelope.get("limit")) is not int
                    or envelope["limit"] != limit
                    or envelope.get("immutable") is not True
                    or not _nontrading(envelope)):
                raise ValueError("ENVELOPE_NOT_PARTIAL")
        elif version == "v2":
            if (set(envelope) != _V2_KEYS
                    or envelope.get("schema") != "market_data.qualified-read-envelope.v1"
                    or not _version(envelope.get("api_version"), 2, 0)
                    or envelope.get("producer") != "market_data"
                    or envelope.get("read_only") is not True
                    or envelope.get("status") != "PARTIAL"
                    or envelope.get("reason") != "EXCHANGE_COMPLETENESS_UNATTESTED"
                    or envelope.get("record_integrity") != "VERIFIED"
                    or envelope.get("source_declared_quality") != ["GOOD"]
                    or envelope.get("source_authenticity") != "NOT_INDEPENDENTLY_ATTESTED"
                    or envelope.get("quality_attestation") != "NOT_INDEPENDENTLY_ATTESTED"
                    or envelope.get("storage_immutability") != "NOT_ATTESTED"
                    or envelope.get("exchange_completeness") != "NOT_ATTESTED"
                    or envelope.get("immutable") is not False
                    or envelope.get("paper_admitted") is not False
                    or envelope.get("symbol") != symbol
                    or envelope.get("timeframe") != "1m"
                    or type(envelope.get("limit")) is not int
                    or envelope["limit"] != limit
                    or not _nontrading(envelope)):
                raise ValueError("QUALIFIED_V2_NOT_PARTIAL")
        else:
            raise ValueError("UNSUPPORTED_QUALIFIED_VERSION")
        rows = envelope.get("rows")
        if type(rows) is not list or not 1 <= len(rows) <= limit:
            raise ValueError("BOUNDED_ROWS_REQUIRED")
        raw = _canonical(envelope)
        if len(raw) > MAX_BYTES:
            raise ValueError("RESPONSE_BYTES_EXCEEDED")
        coverage = envelope.get("coverage")
        if type(coverage) is not dict or set(coverage) != {
            "expected_minutes", "observed_minutes", "missing_minutes"
        }:
            raise ValueError("COVERAGE_REQUIRED")
        if any(type(coverage[key]) is not int for key in (
                "expected_minutes", "observed_minutes", "missing_minutes")):
            raise ValueError("COVERAGE_LITERAL_INTEGERS_REQUIRED")
        starts = []
        source_id = _source(envelope.get("source") if version == "v1"
                            else rows[0].get("source"))
        if version == "v1":
            epochs = envelope.get("producer_epochs")
            if type(epochs) is not list or epochs != [source_id[2]]:
                raise ValueError("EPOCH_SET_REQUIRED")
        if envelope.get("source_revision") != source_id[1] or envelope.get("producer_epoch") != source_id[2]:
            raise ValueError("SOURCE_PIN_MISMATCH")
        for row in rows:
            if (type(row) is not dict
                    or set(row) != _RECORD_KEYS
                    or not _version(row.get("api_version"), 1, 1)
                    or row.get("producer") != "market_data"
                    or row.get("symbol") != symbol
                    or row.get("timeframe") != "1m"
                    or row.get("status") != "PARTIAL"
                    or row.get("reason") != "EXCHANGE_COMPLETENESS_UNATTESTED"
                    or row.get("representation") != "historical_aggregate"
                    or row.get("quality_status") != "GOOD"
                    or row.get("quality_reasons") != []
                    or row.get("source_identity_verified") is not True
                    or not _nontrading(row)
                    or _source(row.get("source")) != source_id):
                raise ValueError("RECORD_SOURCE_REQUIRED")
            if len(_canonical(row)) > 1048576:
                raise ValueError("RECORD_BYTE_BOUND_REQUIRED")
            if (type(row.get("dataset_fingerprint")) is not str
                    or not _SHA64.fullmatch(row["dataset_fingerprint"])
                    or _digest({k: v for k, v in row.items()
                                if k != "dataset_fingerprint"}) != row["dataset_fingerprint"]):
                raise ValueError("RECORD_INTEGRITY_FAILED")
            start, end = row.get("start_ms"), row.get("end_ms")
            first, last = row.get("source_event_start_ms"), row.get("source_event_end_ms")
            ingestion = row.get("ingestion_ms")
            if (not all(_clock(v) for v in (start, end, first, last, ingestion))
                    or start % 60000 != 0 or end != start + 59999
                    or not start <= first <= last <= end < ingestion
                    or last > now_ms or ingestion > now_ms + 3000):
                raise ValueError("RECORD_CLOCKS_INVALID")
            local_cover = row.get("coverage")
            if (type(local_cover) is not dict
                    or set(local_cover) != {"expected_minutes", "observed_minutes",
                                            "missing_minutes", "exchange_completeness_attested"}
                    or any(type(local_cover[key]) is not int for key in (
                        "expected_minutes", "observed_minutes", "missing_minutes"))
                    or local_cover.get("exchange_completeness_attested") is not False
                    or local_cover["expected_minutes"] != 1
                    or local_cover["observed_minutes"] != 1
                    or local_cover["missing_minutes"] != 0):
                raise ValueError("RECORD_COVERAGE_NOT_ATTESTED")
            if (type(row.get("candle")) is not dict
                    or set(row["candle"]) != _CANDLE_KEYS
                    or type(row.get("levels")) is not list
                    or not 0 < len(row["levels"]) <= 4096):
                raise ValueError("RECORD_PAYLOAD_REQUIRED")
            # Math owns financial numeric validation. Non-admitted raw rows are
            # retained for DISPLAY only; this adapter does not compute candles.
            from market_math import historical_aggregate_integrity
            numeric = dict(row["candle"], levels=row["levels"])
            if historical_aggregate_integrity(numeric) is not True:
                raise ValueError("MATH_AGGREGATE_INTEGRITY_REQUIRED")
            starts.append(start)
        if len(set(starts)) != len(starts):
            raise ValueError("AMBIGUOUS_REVISIONS")
        ordered = sorted(starts)
        expected = (ordered[-1] - ordered[0]) // 60000 + 1
        if expected != len(rows) or coverage != {
            "expected_minutes": expected,
            "observed_minutes": len(rows), "missing_minutes": 0
        }:
            raise ValueError("MINUTE_GAP")
        watermark = max(row["source_event_end_ms"] for row in rows)
        if (type(envelope.get("freshness_utc_ms")) is not int
                or envelope["freshness_utc_ms"] != watermark
                or now_ms - watermark > 120000):
            raise ValueError("SOURCE_STALE")
        if version == "v1":
            if (type(envelope.get("next_before_ms")) is not int
                    or envelope["next_before_ms"] != ordered[0]):
                raise ValueError("V1_CURSOR_INVALID")
        else:
            if starts != ordered:
                raise ValueError("V2_CANONICAL_ROW_ORDER_REQUIRED")
            if any(row["ingestion_ms"] > now_ms for row in rows):
                raise ValueError("V2_FUTURE_INGESTION")
        if (type(envelope.get("dataset_fingerprint")) is not str
                or not _SHA64.fullmatch(envelope["dataset_fingerprint"])
                or _digest(rows) != envelope["dataset_fingerprint"]):
            raise ValueError("PAGE_INTEGRITY_FAILED")
        # Do not return mutable nested objects received from untrusted JSON.
        observations = tuple(_freeze(copy.deepcopy(row)) for row in sorted(rows, key=lambda r: r["start_ms"]))
        return {
            "status": "PARTIAL", "reason": "EXCHANGE_COMPLETENESS_UNATTESTED",
            "source_authentication": "MANAGED_TRANSPORT_ONLY_EXTERNAL_NOT_ATTESTED",
            "source_authenticity": "NOT_INDEPENDENTLY_ATTESTED",
            "quality_attestation": "NOT_INDEPENDENTLY_ATTESTED",
            "storage_immutability": "NOT_ATTESTED", "record_integrity": "VERIFIED",
            "data_quality_status": "PARTIAL", "chart_read_only": True,
            "paper_admitted": False, "execution_authority": False,
            "trading_authorized": False, "dataset_fingerprint": envelope["dataset_fingerprint"],
            "coverage": dict(coverage), "freshness_utc_ms": watermark,
            "rows": observations,
        }
    except (KeyError, TypeError, ValueError, OverflowError, RecursionError):
        raise ValueError("QUALIFIED_PARTIAL_UNAVAILABLE") from None



def _freeze(value):
    """Freeze every mutable container after validation, not just the row list."""
    if type(value) is dict:
        return MappingProxyType({key: _freeze(child) for key, child in value.items()})
    if type(value) is list:
        return tuple(_freeze(child) for child in value)
    if type(value) is tuple:
        return tuple(_freeze(child) for child in value)
    return value


def chart_rows(validated_receipt):
    """Project only already verified data. No calculation or trade admission."""
    return [{"t": r["start_ms"], "o": r["candle"]["open"], "h": r["candle"]["high"],
             "l": r["candle"]["low"], "c": r["candle"]["close"],
             "poc": r["candle"]["poc_price"]} for r in validated_receipt["rows"]]


_MTF_WINDOWS = {"5m": 5, "15m": 15}
_MTF_MAX_SOURCE_ROWS = 75
_MTF_MAX_BARS = 5


def qualified_timeframe_rows(validated_receipt, timeframe, *, max_bars=5):
    """Bounded full-minute aggregation for a provenance-checked display receipt.

    The authenticated managed transport does not attest exchange completeness.
    No strategy authorization, delta/POC derivation, trades or OI are invented.
    """
    from decimal import Decimal
    from market_math import aggregate_closed_minute_ohlcv

    step = _MTF_WINDOWS.get(timeframe) if type(timeframe) is str else None
    if step is None or type(max_bars) is not int or not 1 <= max_bars <= _MTF_MAX_BARS:
        raise ValueError("MTF_REQUEST_UNSUPPORTED")
    if (type(validated_receipt) is not dict
            or validated_receipt.get("status") != "PARTIAL"
            or validated_receipt.get("chart_read_only") is not True
            or validated_receipt.get("execution_authority") is not False
            or validated_receipt.get("paper_admitted") is not False
            or validated_receipt.get("trading_authorized") is not False
            or validated_receipt.get("source_authenticity") != "NOT_INDEPENDENTLY_ATTESTED"
            or validated_receipt.get("record_integrity") != "VERIFIED"):
        raise ValueError("MTF_UNQUALIFIED_RECEIPT")
    rows = validated_receipt.get("rows")
    if (type(rows) is not tuple
            or len(rows) != step * max_bars
            or len(rows) > _MTF_MAX_SOURCE_ROWS
            or len(rows) % step):
        raise ValueError("MTF_INCOMPLETE_SOURCE_WINDOW")
    window_ms = step * 60000
    starts = [row["start_ms"] for row in rows]
    if (starts[0] % window_ms
            or any(starts[i] != starts[0] + i * 60000 for i in range(len(rows)))):
        raise ValueError("MTF_UNALIGNED_OR_GAPPED_MINUTES")
    result = []
    for at in range(0, len(rows), step):
        group = rows[at:at + step]
        prices = [(Decimal(str(row["candle"]["open"])),
                   Decimal(str(row["candle"]["high"])),
                   Decimal(str(row["candle"]["low"])),
                   Decimal(str(row["candle"]["close"])),
                   Decimal(str(row["candle"]["buy_volume"])),
                   Decimal(str(row["candle"]["sell_volume"])))
                  for row in group]
        opened, high, low, closed, volume = aggregate_closed_minute_ohlcv(prices)
        result.append({
            "t": starts[at], "o": str(opened), "h": str(high),
            "l": str(low), "c": str(closed), "v": str(volume),
            "closed_at_ms": starts[at] + window_ms,
        })
    return {
        "status": "PARTIAL", "reason": "EXCHANGE_COMPLETENESS_UNATTESTED",
        "timeframe": timeframe, "source_timeframe": "1m",
        "source_minutes": len(rows), "coverage": dict(validated_receipt["coverage"]),
        "record_integrity": "VERIFIED",
        "source_authenticity": "NOT_INDEPENDENTLY_ATTESTED",
        "exchange_completeness_attested": False, "read_only": True,
        "paper_admitted": False, "execution_authority": False,
        "trading_authorized": False, "rows": result,
    }

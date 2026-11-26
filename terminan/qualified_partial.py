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

MAX_BYTES = 8 * 1024 * 1024
MAX_ROWS = 1000
_SHA40 = re.compile(r"[a-f0-9]{40}\Z")
_SHA64 = re.compile(r"[a-f0-9]{64}\Z")
_SYMBOL = re.compile(r"[A-Z0-9]{2,30}\Z")
_MAX_TIME = 2**53 - 1


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _digest(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def _clock(value):
    return type(value) is int and 0 <= value <= _MAX_TIME


def _nontrading(value):
    return (type(value) is dict
            and value.get("execution_authority") is False
            and value.get("trading_authorized", False) is False)


def _source(value):
    if type(value) is not dict or type(value.get("identity")) is not str or not value["identity"]:
        raise ValueError("SOURCE_IDENTITY_REQUIRED")
    if type(value.get("source_revision")) is not str or not _SHA40.fullmatch(value["source_revision"]):
        raise ValueError("SOURCE_REVISION_REQUIRED")
    try:
        epoch = value["epoch"]
        if type(epoch) is not str or str(uuid.UUID(epoch)) != epoch.lower() or uuid.UUID(epoch).version != 4:
            raise ValueError("epoch")
    except (ValueError, KeyError, TypeError, AttributeError):
        raise ValueError("SOURCE_EPOCH_REQUIRED") from None
    if value.get("market_type") != "linear" or value.get("representation") != "live_trade_aggregate":
        raise ValueError("SOURCE_MARKET_REPRESENTATION_REQUIRED")
    return value["identity"], value["source_revision"], value["epoch"]


def validate_partial(envelope, symbol, limit, *, now_ms=None):
    """Return detached, display-only immutable-receipt data or fail closed.

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
        if (envelope.get("api_version") != {"major": 1, "minor": 1}
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
        starts = []
        source_id = _source(envelope.get("source"))
        epochs = envelope.get("producer_epochs")
        if type(epochs) is not list or epochs != [source_id[2]]:
            raise ValueError("EPOCH_SET_REQUIRED")
        if envelope.get("source_revision") != source_id[1] or envelope.get("producer_epoch") != source_id[2]:
            raise ValueError("SOURCE_PIN_MISMATCH")
        for row in rows:
            if (type(row) is not dict
                    or row.get("api_version") != {"major": 1, "minor": 1}
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
                    or local_cover != {"expected_minutes": 1, "observed_minutes": 1,
                                      "missing_minutes": 0,
                                      "exchange_completeness_attested": False}):
                raise ValueError("RECORD_COVERAGE_NOT_ATTESTED")
            if type(row.get("candle")) is not dict or type(row.get("levels")) is not list:
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
        if (type(envelope.get("next_before_ms")) is not int
                or envelope["next_before_ms"] != ordered[0]
                or type(envelope.get("dataset_fingerprint")) is not str
                or not _SHA64.fullmatch(envelope["dataset_fingerprint"])
                or _digest(rows) != envelope["dataset_fingerprint"]):
            raise ValueError("PAGE_INTEGRITY_FAILED")
        # Do not return mutable nested objects received from untrusted JSON.
        observations = tuple(copy.deepcopy(row) for row in sorted(rows, key=lambda r: r["start_ms"]))
        return {
            "status": "PARTIAL", "reason": "EXCHANGE_COMPLETENESS_UNATTESTED",
            "source_authentication": "MANAGED_TRANSPORT_ONLY_EXTERNAL_NOT_ATTESTED",
            "data_quality_status": "PARTIAL", "chart_read_only": True,
            "paper_admitted": False, "execution_authority": False,
            "trading_authorized": False, "dataset_fingerprint": envelope["dataset_fingerprint"],
            "coverage": dict(coverage), "freshness_utc_ms": watermark,
            "rows": observations,
        }
    except (KeyError, TypeError, ValueError, OverflowError, RecursionError):
        raise ValueError("QUALIFIED_PARTIAL_UNAVAILABLE") from None


def chart_rows(validated_receipt):
    """Project only already verified data. No calculation or trade admission."""
    return [{"t": r["start_ms"], "o": r["candle"]["open"], "h": r["candle"]["high"],
             "l": r["candle"]["low"], "c": r["candle"]["close"],
             "poc": r["candle"]["poc_price"]} for r in validated_receipt["rows"]]

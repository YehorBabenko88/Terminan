"""Presentation adapter for Math-owned levels on explicitly supplied candles."""

from hashlib import sha256
from hmac import compare_digest
from math import isfinite
import re

from .paper_ledger import canonical_json


# Grid v2 multipin calendar widths. The HTTP route remains fenced until
# an authenticated provider supplies the expected rollup pins.
_DAY = 86_400_000
_GRID_LEVEL_WIDTHS = {"1h": 3_600_000, "4h": 14_400_000, "1d": _DAY, "1w": 7 * _DAY}
_MAX_GRID_LEVEL_CANDLES = 1000
_MAX_GRID_SERIES_CANDLES = 32
_MAX_GRID_SERIES_SPAN_MS = 14 * _DAY
_GRID_MAX_TIMESTAMP = 2**53 - 1


def _fingerprint(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _valid_parent(parent):
    return (type(parent) is dict and type(parent.get("dataset_id")) is str
            and bool(parent["dataset_id"]) and _fingerprint(parent.get("dataset_fingerprint")))


def _grid_window_width(timeframe, start_ms, end_ms, as_of_ms):
    if type(timeframe) is not str or timeframe not in _GRID_LEVEL_WIDTHS:
        raise ValueError("unsupported Grid levels timeframe")
    width = _GRID_LEVEL_WIDTHS[timeframe]
    anchor = 4 * _DAY if timeframe == "1w" else 0
    if (any(type(value) is not int for value in (start_ms, end_ms, as_of_ms))
            or not 0 <= start_ms < end_ms <= as_of_ms <= _GRID_MAX_TIMESTAMP
            or (start_ms - anchor) % width or (end_ms - anchor) % width
            or (end_ms - start_ms) // width > _MAX_GRID_LEVEL_CANDLES):
        raise ValueError("invalid Grid levels window")
    return width


def grid_level_candles(snapshot, *, trusted_fingerprint, symbol, market_type,
                       timeframe, start_ms, end_ms, as_of_ms):
    """Map a pinned Grid rollup to Math input after the caller authenticates its pin.

    The trusted fingerprint comes from independent source admission, never from
    the same response as the snapshot. This function does not authenticate a
    transport or qualify a bare Grid HTTP response.
    """
    if not _fingerprint(trusted_fingerprint):
        raise ValueError("independent Grid fingerprint required")
    if (type(symbol) is not str or not re.fullmatch(r"[A-Z0-9]{2,30}", symbol)
            or type(market_type) is not str or not market_type):
        raise ValueError("invalid Grid levels instrument")
    width = _grid_window_width(timeframe, start_ms, end_ms, as_of_ms)

    if (type(snapshot) is not dict or snapshot.get("schema") not in
            ("grid.history.rollup.v1", "grid.history.rollup.v2", "grid.history.rollup.v3")
            or snapshot.get("evidence_class") != "HISTORICAL"
            or snapshot.get("timeframe") != timeframe
            or type(snapshot.get("source")) is not dict
            or snapshot.get("dataset_fingerprint") != trusted_fingerprint):
        raise ValueError("Grid rollup does not match trusted selection")
    request = snapshot.get("request")
    expected = {"venue": "bybit", "symbol": symbol, "market_type": market_type,
                "start_ms": start_ms, "end_ms": end_ms}
    if (type(request) is not dict or any(type(request.get(key)) is not type(value)
                                       or request[key] != value for key, value in expected.items())):
        raise ValueError("Grid rollup request mismatch")
    if snapshot["schema"] == "grid.history.rollup.v1":
        if (timeframe != "1h" or type(request.get("as_of_ms")) is not int
                or request["as_of_ms"] != as_of_ms
                or not _valid_parent({"dataset_id": snapshot.get("parent_dataset_id"),
                                      "dataset_fingerprint": snapshot.get("parent_dataset_fingerprint")})):
            raise ValueError("invalid Grid single-pin lineage")
    else:
        parents = snapshot.get("parents")
        span = end_ms - start_ms
        sequence = snapshot["schema"] == "grid.history.rollup.v3"
        if sequence:
            if (request.get("schema") != "grid.history.selection.v4"
                    or span > min(_MAX_GRID_SERIES_CANDLES * width, _MAX_GRID_SERIES_SPAN_MS)):
                raise ValueError("invalid Grid levels series window")
        elif span != width:
            raise ValueError("invalid Grid single-candle window")
        if (type(snapshot.get("as_of_ms")) is not int
                or snapshot["as_of_ms"] != as_of_ms or request.get("timeframe") != timeframe
                or type(snapshot.get("units")) is not dict or type(parents) is not list
                or not 1 <= len(parents) <= (16 if sequence else 8)
                or any(not _valid_parent(parent) or not _fingerprint(parent.get("snapshot_id"))
                       for parent in parents)):
            raise ValueError("invalid Grid multipin lineage")
        pins = [parent["snapshot_id"] for parent in parents]
        if request.get("snapshot_ids") != pins or len(set(pins)) != len(pins):
            raise ValueError("invalid Grid parent order")
        if sequence and any(
            type(record.get(key)) is not str or not record[key]
            for record, fields in ((snapshot["source"], ("identity", "source_revision", "epoch")),
                                   (snapshot["units"], ("price", "volume")))
            for key in fields
        ):
            raise ValueError("Grid levels series source lineage is incomplete")
    rows = snapshot.get("rows")
    if type(rows) is not list or len(rows) != (end_ms - start_ms) // width:
        raise ValueError("incomplete Grid levels window")
    payload = canonical_json({key: value for key, value in snapshot.items()
                              if key != "dataset_fingerprint"})
    if len(payload) > 2_097_152 or not compare_digest(sha256(payload).hexdigest(), trusted_fingerprint):
        raise ValueError("Grid rollup fingerprint mismatch")

    candles = []
    for index, row in enumerate(rows):
        lower = start_ms + index * width
        upper = lower + width
        if (type(row) is not dict or row.get("complete", True) is not True
                or any(type(row.get(field)) is not int for field in
                       ("event_start_ms", "event_end_ms", "available_at_ms", "watermark_ms"))
                or row["event_start_ms"] != lower or row["event_end_ms"] != upper
                or not upper <= row["watermark_ms"] <= row["available_at_ms"] <= as_of_ms):
            raise ValueError("incomplete or unavailable Grid candle")
        high, low = row.get("high"), row.get("low")
        try:
            valid = all(type(price) in (int, float) and isfinite(price)
                        and price > 0 for price in (high, low))
        except OverflowError:
            valid = False
        if not valid or high < low:
            raise ValueError("invalid Grid candle prices")
        candles.append({"t": lower, "h": high, "l": low, "complete": True})
    return candles


def levels_from_grid_series(snapshot, *, trusted_fingerprint, symbol, market_type,
                            timeframe, start_ms, end_ms, as_of_ms, tick_size=0,
                            max_levels=200):
    """Calculate levels over Grid's contiguous, independently pinned v3 rollup.

    The caller authenticates the pin independently of the response.
    """
    if type(snapshot) is not dict or snapshot.get("schema") != "grid.history.rollup.v3":
        raise ValueError("Grid levels series requires a v3 rollup")
    candles = grid_level_candles(
        snapshot, trusted_fingerprint=trusted_fingerprint, symbol=symbol,
        market_type=market_type, timeframe=timeframe, start_ms=start_ms,
        end_ms=end_ms, as_of_ms=as_of_ms,
    )
    return untouched_levels(candles, timeframe, as_of_ms,
                            tick_size=tick_size, max_levels=max_levels)


def untouched_levels(candles, timeframe, as_of_ms, *, tick_size=0, max_levels=200):
    from market_compute_api import TIMEFRAME_LEVELS_ABI, untouched_timeframe_levels

    if TIMEFRAME_LEVELS_ABI != "math.market.levels.binary64.v1":
        raise RuntimeError("unsupported Math levels ABI")
    return untouched_timeframe_levels(candles, timeframe, as_of_ms,
                                     tick_size=tick_size, max_levels=max_levels)


def merge_levels(series, as_of_ms, *, tick_size=0):
    levels = []
    for timeframe, rows in series.items():
        levels.extend(untouched_levels(rows, timeframe, as_of_ms, tick_size=tick_size))
    return sorted(levels, key=lambda level: (level['price'], level['timeframe'], level['side']))

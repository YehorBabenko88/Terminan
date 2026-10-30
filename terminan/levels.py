"""Bounded historical untouched high/low levels from verified closed candles."""
import math

PERIODS = {"1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000, "1w": 604_800_000}
MAX_CANDLES = 10_000


def untouched_levels(candles, timeframe, as_of_ms, *, tick_size=0, max_levels=200):
    if timeframe not in PERIODS:
        raise ValueError("unsupported timeframe")
    if type(as_of_ms) is not int or as_of_ms < 0:
        raise ValueError("invalid as_of_ms")
    if type(tick_size) not in (int, float) or not math.isfinite(tick_size) or tick_size < 0:
        raise ValueError("invalid tick size")
    if type(max_levels) is not int or not 1 <= max_levels <= 2000:
        raise ValueError("invalid max_levels")
    if not isinstance(candles, (list, tuple)) or len(candles) > MAX_CANDLES:
        raise ValueError("invalid candle batch")

    parsed = []
    seen = set()
    duration = PERIODS[timeframe]
    for candle in candles:
        if not isinstance(candle, dict):
            raise ValueError("invalid candle")
        if candle.get("complete") is False:
            continue
        t = candle.get("t")
        if type(t) is not int or t < 0 or t % duration or t in seen:
            raise ValueError("invalid or duplicate candle timestamp")
        seen.add(t)
        high, low = candle.get("h"), candle.get("l")
        if type(high) not in (int, float) or type(low) not in (int, float):
            raise ValueError("invalid price")
        high, low = float(high), float(low)
        if not math.isfinite(high) or not math.isfinite(low) or high < low:
            raise ValueError("invalid candle prices")
        parsed.append((t, high, low))
    parsed.sort()

    active = []
    for t, high, low in parsed:
        if t + duration > as_of_ms:
            continue
        # A subsequent candle touching a previous high/low invalidates it.
        active = [
            level for level in active
            if (high < level["price"] - tick_size if level["side"] == "high"
                else low > level["price"] + tick_size)
        ]
        active.append(dict(timeframe=timeframe, side="high", price=high,
                           origin_ms=t, confirmed_ms=t + duration))
        active.append(dict(timeframe=timeframe, side="low", price=low,
                           origin_ms=t, confirmed_ms=t + duration))
        if len(active) > 2 * MAX_CANDLES:
            raise ValueError("level resource limit")
    return active[-max_levels:]


def merge_levels(series, as_of_ms, *, tick_size=0):
    if not isinstance(series, dict) or len(series) > len(PERIODS):
        raise ValueError("invalid series")
    levels = []
    for timeframe, candles in series.items():
        levels.extend(untouched_levels(candles, timeframe, as_of_ms, tick_size=tick_size))
    return sorted(levels, key=lambda item: (item["price"], item["timeframe"], item["side"]))

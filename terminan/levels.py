"""Presentation adapter for Math-owned levels on explicitly supplied candles."""


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

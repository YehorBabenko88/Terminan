"""Versioned, read-only source projections; never infer live L2 from candles."""
import json
from . import data


def grid_market_view(symbol: str, candle_limit=200, footprint_limit=400):
    data.validate(symbol)
    if not (1 <= int(candle_limit) <= 1000 and 1 <= int(footprint_limit) <= 1000):
        raise ValueError("limits out of range")
    if not data.grid_available():
        return {"version": 1, "source": "cluster-grid", "symbol": symbol,
                "state": "NOT_CONFIGURED", "candles": [], "footprint": [],
                "l2": {"state": "UNAVAILABLE", "reason": "No verified L2 snapshot source"}}
    candles = data.grid_candles(symbol, int(candle_limit))
    footprint = data.footprint(symbol, int(footprint_limit))
    # Market data is recorded one-minute aggregates, not an exchange book.
    return {"version": 1, "source": "cluster-grid", "symbol": symbol,
            "state": "HISTORICAL_AGGREGATES" if candles or footprint else "EMPTY",
            "candles": candles, "footprint": footprint,
            "l2": {"state": "UNAVAILABLE", "reason": "Minute footprint is not a live orderbook"}}


def strattester_research_view(symbol: str, limit=50):
    data.validate(symbol)
    if not 1 <= int(limit) <= 100:
        raise ValueError("limit out of range")
    if not data.results_available():
        return {"version": 1, "source": "strattester", "symbol": symbol,
                "state": "NOT_CONFIGURED", "runs": []}
    rows = data.research(symbol, int(limit))
    return {"version": 1, "source": "strattester", "symbol": symbol,
            "state": "HISTORICAL_RESEARCH" if rows else "EMPTY",
            "runs": rows}

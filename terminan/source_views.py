"""Versioned, read-only source projections; never infer live L2 from candles."""
from datetime import datetime, timezone
from . import data


def _freshness(rows, now_ms):
    """Expose observed timestamps without claiming minute aggregates are live L2."""
    times = [int(row["t"]) for row in rows if row.get("t") is not None]
    if not times:
        return {"state": "NO_DATA", "latest_ms": None, "age_seconds": None}
    latest = max(times)
    age = (now_ms - latest) / 1000
    return {"state": "FUTURE_TIMESTAMP" if age < -60 else "STALE" if age > 180 else "RECENT_AGGREGATE",
            "latest_ms": latest, "age_seconds": round(age, 1)}


def grid_market_view(symbol: str, candle_limit=200, footprint_limit=400, now_ms=None):
    data.validate(symbol)
    if (type(candle_limit) is not int or type(footprint_limit) is not int
            or not (1 <= candle_limit <= 1000 and 1 <= footprint_limit <= 1000)) :
        raise ValueError("limits out of range")
    if now_ms is None:
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    if type(now_ms) is not int or now_ms < 0:
        raise ValueError("invalid observation timestamp")
    if not data.grid_available():
        return {"version": 1, "source": "cluster-grid", "symbol": symbol,
                "state": "NOT_CONFIGURED", "candles": [], "footprint": [],
                "freshness": {"state": "NO_DATA", "latest_ms": None, "age_seconds": None},
                "l2": {"state": "UNAVAILABLE", "reason": "No verified L2 snapshot source"}}
    candles = data.grid_candles(symbol, int(candle_limit))
    footprint = data.footprint(symbol, int(footprint_limit))
    # Market data is recorded one-minute aggregates, not an exchange book.
    return {"version": 1, "source": "cluster-grid", "symbol": symbol,
            "state": "HISTORICAL_AGGREGATES" if candles or footprint else "EMPTY",
            "candles": candles, "footprint": footprint,
            "freshness": {"candles": _freshness(candles, now_ms), "footprint": _freshness(footprint, now_ms)},
            "l2": {"state": "UNAVAILABLE", "reason": "Minute footprint is not a live orderbook"}}


def strattester_research_view(symbol: str, limit=50):
    data.validate(symbol)
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("limit out of range")
    if not data.results_available():
        return {"version": 1, "source": "strattester", "symbol": symbol,
                "state": "NOT_CONFIGURED", "runs": []}
    rows = [dict(row) for row in data.research(symbol, limit)]
    for row in rows:
        metrics = row.get("metrics")
        fingerprint = metrics.get("fingerprint") if isinstance(metrics, dict) else None
        coverage = metrics.get("coverage") if isinstance(metrics, dict) else None
        row["dataset"] = {
            "fingerprint": fingerprint if isinstance(fingerprint, str) and fingerprint else None,
            "coverage": coverage if isinstance(coverage, str) and coverage else "UNSPECIFIED",
            "comparability": "IDENTIFIED" if isinstance(fingerprint, str) and fingerprint else "UNVERIFIED",
        }
        # Publication authority requires a source-owned lease validator. No
        # historical metric, fencing token or status field can replace it.
        row["validation"] = {
            "historical_research": "RECORDED",
            "publication_authority": "UNVERIFIED",
            "live_validation": "NOT_VERIFIED",
            "simulation_pass": "NOT_VERIFIED",
            "trading_authority": "NONE",
        }
    return {"version": 1, "source": "strattester", "symbol": symbol,
            "state": "HISTORICAL_RESEARCH" if rows else "EMPTY",
            "runs": rows}


def strattester_comparison_view(symbol: str, left_run: str, right_run: str):
    """Compare two identified runs from the same symbol, never authorize trading."""
    from .research_compare import compare_runs
    data.validate(symbol)
    if not isinstance(left_run, str) or not isinstance(right_run, str):
        raise ValueError("invalid run identifiers")
    if not (1 <= len(left_run) <= 128 and 1 <= len(right_run) <= 128):
        raise ValueError("invalid run identifiers")
    if left_run == right_run:
        raise ValueError("choose two distinct runs")
    if not data.results_available():
        return {"version": 1, "source": "strattester", "state": "NOT_CONFIGURED",
                "symbol": symbol, "comparison": None}
    # The adapter intentionally only exposes its bounded recent research window.
    runs = strattester_research_view(symbol, limit=100)["runs"]
    left = next((r for r in runs if r.get("run_id") == left_run), None)
    right = next((r for r in runs if r.get("run_id") == right_run), None)
    if left is None or right is None:
        return {"version": 1, "source": "strattester", "state": "RUN_NOT_FOUND",
                "symbol": symbol, "comparison": None}
    return {"version": 1, "source": "strattester", "state": "COMPARISON",
            "symbol": symbol, "left_run": left_run, "right_run": right_run,
            "comparison": compare_runs(left, right)}

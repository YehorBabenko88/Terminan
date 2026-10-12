"""Source provenance and read-only availability, with no probing of external services."""
import os
from . import data


def source_health():
    return {
        "schema_version": 1,
        "mode": "READ_ONLY",
        "sources": {
            "cluster_grid": {
                "configured": data.grid_available(),
                "state": "CONFIGURED_NOT_PROBED" if data.grid_available() else "NOT_CONFIGURED",
                "ownership": ["market_ingestion", "candles_1m", "footprint_1m", "fleet"],
                "l2": "NOT_EXPOSED",
            },
            "strattester_market": {
                "configured": bool(os.environ.get("TERMINAN_STRATTESTER_DB")),
                "state": "CONFIGURED_NOT_PROBED" if os.environ.get("TERMINAN_STRATTESTER_DB") else "NOT_CONFIGURED",
                "ownership": ["historical_candles"],
            },
            "strattester_research": {
                "configured": bool(os.environ.get("TERMINAN_RESULTS_DB")),
                "state": "CONFIGURED_NOT_PROBED" if os.environ.get("TERMINAN_RESULTS_DB") else "NOT_CONFIGURED",
                "ownership": ["research_results", "strategy_versions"],
                "authority": "UNVERIFIED",
            },
        },
        "trading_enabled": False,
    }

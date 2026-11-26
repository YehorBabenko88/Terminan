"""Causally admissible POC-family study using the *existing* Math and Terminan.

Historical Strattester trade_profile/proxy_profile arithmetic was migrated to
market_math.trade_value_area_metrics and candle_proxy_value_area_metrics. This
adapter only composes those canonical owners with the already existing
generate_profile_reclaim_entries; it DOES NOT calculate a second POC, does
not implement historical SPEC_ONLY trade strategies, and never enables a
PaperEngine or admits trading.

All timestamps and data availability are caller-declared and unauthenticated.
An output is an offline research observation, not a tradable signal.
"""
from dataclasses import dataclass, fields
from .entry_context import ProfileSummary
from .historical_research_specifications import historical_research_specification
from .market_structure import OHLCObservation, MarketTimeframe
from .profile_analysis import analyze_trade_profile, analyze_candle_proxy_profile
from .strategy_entries import (
    ResearchEntry, SignedFlowObservation, generate_profile_reclaim_entries,
)


@dataclass(frozen=True, slots=True)
class HistoricalPocStudy:
    profile: ProfileSummary
    entries: tuple[ResearchEntry, ...]
    profile_source: str
    historical_family: str = "poc"
    historical_strategy_availability: str = "SPEC_ONLY"
    source_authentication: str = "NOT_EVALUATED"
    execution_authority: bool = False
    trading_authorized: bool = False


def _closed_rows(rows, keys):
    if type(rows) not in (list, tuple) or not 1 <= len(rows) <= 4096:
        raise ValueError("POC_STUDY_BOUNDED_ROWS_REQUIRED")
    out = []
    for value in tuple(rows):
        if type(value) is not dict or len(value) != len(keys) or set(value) != keys:
            raise ValueError("POC_STUDY_EXACT_ROW_FIELDS_REQUIRED")
        # Snapshot all leaves before ANY Math call; require exact primitive
        # types (never user-defined coercion, aliasing, callbacks or SQL).
        frozen = {}
        for key in keys:
            item = value[key]
            if type(item) not in (int, float):
                raise ValueError("POC_STUDY_EXACT_NUMERIC_LEAVES_REQUIRED")
            frozen[key] = item
        out.append(frozen)
    return tuple(out)


def _candles(bars):
    if type(bars) not in (list, tuple) or not 2 <= len(bars) <= 4096:
        raise ValueError("POC_STUDY_BOUNDED_CANDLES_REQUIRED")
    out = []
    for bar in tuple(bars):
        if type(bar) is not OHLCObservation:
            raise ValueError("POC_STUDY_EXACT_OHLC_REQUIRED")
        leaves = tuple(getattr(bar, field.name) for field in fields(OHLCObservation))
        if any(type(v) not in (int, float) for v in leaves):
            raise ValueError("POC_STUDY_LITERAL_CANDLE_FIELDS_REQUIRED")
        out.append(OHLCObservation(*leaves))
    return tuple(out)


def research_historical_poc(
    symbol, bars, source_rows, *,
    source_kind, as_of_ms, timeframe, flow=(),
):
    """Project original POC math into the single canonical research generator.

    source_kind = "TRADE" or "CANDLE_PROXY"; no default (avoid silently
    substituting approximate candles for true trade bins). Every source row
    declares actual available_at_ms; Math controls causal eligibility.
    The legacy family POC_MEAN_REVERSION remains SPEC_ONLY. A "reclaim"
    research entry is not an assertion of historical mean-reversion parity.
    """
    if type(source_kind) is not str or source_kind not in ("TRADE", "CANDLE_PROXY"):
        raise ValueError("POC_STUDY_EXPLICIT_SOURCE_REQUIRED")
    if type(as_of_ms) is not int or not 0 <= as_of_ms <= 2**53 - 1:
        raise ValueError("POC_STUDY_LITERAL_AS_OF_REQUIRED")
    if type(timeframe) is not MarketTimeframe:
        raise ValueError("POC_STUDY_EXPLICIT_TIMEFRAME_REQUIRED")
    old = historical_research_specification("POC_MEAN_REVERSION")
    if (old.execution_status != "SPEC_ONLY"
            or old.signal_generator is not None
            or old.trading_authorized is not False):
        raise ValueError("POC_STUDY_LEGACY_SPEC_MUST_REMAIN_INERT")
    captured_bars = _candles(bars)
    if source_kind == "TRADE":
        source = _closed_rows(
            source_rows, frozenset(("event_ms", "available_at_ms", "price", "volume"))
        )
        profile = analyze_trade_profile(source, decision_ms=as_of_ms)
    else:
        source = _closed_rows(
            source_rows,
            frozenset(("event_start_ms", "event_end_ms",
                       "available_at_ms", "high", "low", "close", "volume")),
        )
        profile = analyze_candle_proxy_profile(source, decision_ms=as_of_ms)
    # Strict canonical generator verifies the entire candle batch's closure,
    # causal availability, symbol, timestamp cadence, typed flow and signal.
    entries = generate_profile_reclaim_entries(
        symbol, captured_bars, (profile,), flow=flow,
        as_of_ms=as_of_ms, timeframe=timeframe,
    )
    if (type(profile) is not ProfileSummary
            or any(type(entry) is not ResearchEntry or
                   entry.trading_authorized is not False or
                   entry.execution_authority is not False for entry in entries)):
        raise ValueError("POC_STUDY_CANONICAL_OUTPUT_REQUIRED")
    return HistoricalPocStudy(profile, entries, source_kind)

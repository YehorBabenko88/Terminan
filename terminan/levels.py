"""Presentation adapters for Math-owned levels and closed historical versions."""
from .history_protocol import legacy_rollup_candles,validate_rollup_v12,_snapshot_literal,_MARKET_DATA_LEVEL_WIDTHS

def market_data_level_candles(snapshot,*,trusted_fingerprint,symbol,market_type,timeframe,start_ms,end_ms,as_of_ms):
    return legacy_rollup_candles(snapshot,trusted_fingerprint=trusted_fingerprint,symbol=symbol,market_type=market_type,timeframe=timeframe,start_ms=start_ms,end_ms=end_ms,as_of_ms=as_of_ms)

def market_data_level_candles_v12(snapshot,*,trusted_fingerprint,selection,catalog,as_of_ms):
    p,_=validate_rollup_v12(snapshot,trusted_fingerprint=trusted_fingerprint,selection=selection,catalog=catalog,as_of_ms=as_of_ms,options={})
    if p['timeframe'] not in _MARKET_DATA_LEVEL_WIDTHS:raise ValueError('MATH_LEVELS_TIMEFRAME_UNSUPPORTED')
    return [{'t':r['event_start_ms'],'h':r['high'],'l':r['low'],'complete':True} for r in p['rows']]

def levels_from_market_data_series_v12(snapshot,*,trusted_fingerprint,selection,catalog,decision_ms,tick_size=0,max_levels=200):
    p,options=validate_rollup_v12(snapshot,trusted_fingerprint=trusted_fingerprint,selection=selection,catalog=catalog,as_of_ms=None,
        options={'decision_ms':decision_ms,'tick_size':tick_size,'max_levels':max_levels})
    if p['operation']!='series' or p['timeframe'] not in _MARKET_DATA_LEVEL_WIDTHS:raise ValueError('HISTORY_LEVELS_SERIES_OPERATION')
    decision=options['decision_ms'];width=_MARKET_DATA_LEVEL_WIDTHS[p['timeframe']]
    known=[r for r in p['rows'] if r['event_end_ms']<=decision and r['available_at_ms']<=decision]
    if any(r['event_start_ms']!=p['selection']['start_ms']+i*width for i,r in enumerate(known)):return []
    candles=[{'t':r['event_start_ms'],'h':r['high'],'l':r['low'],'complete':True} for r in known]
    return untouched_levels(candles,p['timeframe'],decision,tick_size=options['tick_size'],max_levels=options['max_levels'])

def levels_from_market_data_series(snapshot, *, trusted_fingerprint, symbol, market_type,
                            timeframe, start_ms, end_ms, as_of_ms, tick_size=0,
                            max_levels=200):
    """Calculate levels over MarketData's contiguous, independently pinned v3 rollup.

    The caller authenticates the pin independently of the response.
    """
    snapshot=_snapshot_literal(snapshot)
    if type(snapshot) is not dict or snapshot.get("schema") != "market_data.history.rollup.v3":
        raise ValueError("MarketData levels series requires a v3 rollup")
    candles = market_data_level_candles(
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

"""Historical untouched high/low levels, using only closed candles."""
from math import isfinite
PERIODS={'1h':3600000,'4h':14400000,'1d':86400000,'1w':604800000}

def untouched_levels(candles,timeframe,as_of_ms,*,tick_size=0,max_levels=200):
    if timeframe not in PERIODS: raise ValueError('unsupported timeframe')
    if not isfinite(tick_size) or tick_size<0 or not 1<=max_levels<=2000: raise ValueError('invalid parameters')
    if type(as_of_ms) is not int or not 0<=as_of_ms<=2**63-1: raise ValueError('invalid observation timestamp')
    active=[]
    seen={}
    for c in sorted(candles,key=lambda v:int(v['t'])):
        t=int(c['t']); high=float(c['h']); low=float(c['l'])
        if t<0 or t>2**63-1: raise ValueError('invalid candle timestamp')
        if not isfinite(high) or not isfinite(low) or high<low: raise ValueError('invalid candle')
        if t+PERIODS[timeframe]>as_of_ms or c.get('complete') is False: continue
        candle_key=(high,low)
        if t in seen:
            if seen[t]!=candle_key: raise ValueError('conflicting duplicate candle')
            continue
        seen[t]=candle_key
        active=[v for v in active if high<v['price']-tick_size if v['side']=='high'] + [v for v in active if low>v['price']+tick_size if v['side']=='low']
        active.extend([dict(timeframe=timeframe,side='high',price=high,origin_ms=t,confirmed_ms=t+PERIODS[timeframe]),dict(timeframe=timeframe,side='low',price=low,origin_ms=t,confirmed_ms=t+PERIODS[timeframe])])
    return active[-max_levels:]

def merge_levels(series,as_of_ms,*,tick_size=0):
    levels=[]
    for tf,rows in series.items():levels.extend(untouched_levels(rows,tf,as_of_ms,tick_size=tick_size))
    return sorted(levels,key=lambda v:(v['price'],v['timeframe'],v['side']))


def missing_candle_intervals(candles, timeframe, as_of_ms):
    """Report gaps between observed closed candles, without inventing missing prices.

    Gaps preceding the first available candle or following the last observed
    closed candle cannot be inferred from this bounded history.
    """
    if timeframe not in PERIODS: raise ValueError('unsupported timeframe')
    if type(as_of_ms) is not int or not 0 <= as_of_ms <= 2**63-1:
        raise ValueError('invalid observation timestamp')
    period = PERIODS[timeframe]
    times = set()
    for candle in candles:
        t = candle['t']
        if type(t) is not int or not 0 <= t <= 2**63-1:
            raise ValueError('invalid candle timestamp')
        if candle.get('complete') is not False and t + period <= as_of_ms:
            times.add(t)
    times = sorted(times)
    gaps = []
    for left, right in zip(times, times[1:]):
        if right - left > period:
            gaps.append({'after_ms': left, 'before_ms': right,
                         'missing_intervals': (right - left) // period - 1})
    return gaps


def level_history_quality(series, as_of_ms):
    """Shared read-only quality contract for chart and DOM consumers."""
    gaps = {tf: missing_candle_intervals(rows, tf, as_of_ms)
            for tf, rows in series.items()}
    has_closed = any(
        any(c.get('complete') is not False
            and int(c['t']) >= 0
            and int(c['t']) + PERIODS[tf] <= as_of_ms
            for c in rows)
        for tf, rows in series.items()
    )
    has_gaps = any(gaps.values())
    timeframe_states = {
        tf: ('GAPS_DETECTED' if gaps[tf] else 'CLOSED_CANDLES_PRESENT'
             if any(c.get('complete') is not False and int(c['t']) >= 0
                    and int(c['t']) + PERIODS[tf] <= as_of_ms for c in rows)
             else 'NO_CLOSED_CANDLES')
        for tf, rows in series.items()
    }
    latest_closed_ms = {
        tf: max((int(c['t']) + PERIODS[tf] for c in rows
                 if c.get('complete') is not False and int(c['t']) >= 0
                 and int(c['t']) + PERIODS[tf] <= as_of_ms), default=None)
        for tf, rows in series.items()
    }
    stale_timeframes = [tf for tf, end in latest_closed_ms.items()
                        if end is not None and as_of_ms - end >= 2 * PERIODS[tf]]
    missing_timeframes = [tf for tf, state in timeframe_states.items()
                          if state == 'NO_CLOSED_CANDLES']
    return {
        'state': 'GAPS_DETECTED' if has_gaps else 'NO_INTERNAL_GAPS_DETECTED',
        'coverage': 'BOUNDED_WINDOW_ONLY',
        'gaps': gaps,
        'timeframe_states': timeframe_states,
        'missing_timeframes': missing_timeframes,
        'latest_closed_ms': latest_closed_ms,
        'stale_timeframes': stale_timeframes,
        'level_validation': ('UNVERIFIED_DUE_TO_GAPS' if has_gaps
                             else 'UNVERIFIED_MISSING_TIMEFRAMES' if missing_timeframes
                             else 'UNVERIFIED_STALE_TIMEFRAMES' if stale_timeframes
                             else 'UNVERIFIED_BOUNDED_HISTORY'),
        'data_state': 'CLOSED_CANDLES_PRESENT' if has_closed else 'NO_CLOSED_CANDLES',
        'trading_authority': 'NONE',
    }

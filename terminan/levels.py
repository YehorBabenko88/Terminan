"""Historical untouched high/low levels, using only closed candles."""
from math import isfinite
PERIODS={'1h':3600000,'4h':14400000,'1d':86400000,'1w':604800000}

def untouched_levels(candles,timeframe,as_of_ms,*,tick_size=0,max_levels=200):
    if timeframe not in PERIODS: raise ValueError('unsupported timeframe')
    if not isfinite(tick_size) or tick_size<0 or not 1<=max_levels<=2000: raise ValueError('invalid parameters')
    if type(as_of_ms) is not int or as_of_ms<0: raise ValueError('invalid observation timestamp')
    active=[]
    seen={}
    for c in sorted(candles,key=lambda v:int(v['t'])):
        t=int(c['t']); high=float(c['h']); low=float(c['l'])
        if t<0: raise ValueError('invalid candle timestamp')
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
    if type(as_of_ms) is not int or as_of_ms < 0:
        raise ValueError('invalid observation timestamp')
    period = PERIODS[timeframe]
    times = sorted({int(c['t']) for c in candles
                    if c.get('complete') is not False
                    and int(c['t']) >= 0
                    and int(c['t']) + period <= as_of_ms})
    gaps = []
    for left, right in zip(times, times[1:]):
        if right - left > period:
            gaps.append({'after_ms': left, 'before_ms': right,
                         'missing_intervals': (right - left) // period - 1})
    return gaps

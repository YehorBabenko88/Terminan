"""Historical untouched high/low levels, using only closed candles."""
PERIODS={'1h':3600000,'4h':14400000,'1d':86400000,'1w':604800000}

def untouched_levels(candles,timeframe,as_of_ms,*,tick_size=0,max_levels=200):
    if timeframe not in PERIODS: raise ValueError('unsupported timeframe')
    if tick_size<0 or not 1<=max_levels<=2000: raise ValueError('invalid parameters')
    active=[]
    for c in sorted(candles,key=lambda v:int(v['t'])):
        t=int(c['t']); high=float(c['h']); low=float(c['l'])
        if high<low: raise ValueError('invalid candle')
        if t+PERIODS[timeframe]>as_of_ms or c.get('complete') is False: continue
        active=[v for v in active if high<v['price']-tick_size if v['side']=='high'] + [v for v in active if low>v['price']+tick_size if v['side']=='low']
        active.extend([dict(timeframe=timeframe,side='high',price=high,origin_ms=t,confirmed_ms=t+PERIODS[timeframe]),dict(timeframe=timeframe,side='low',price=low,origin_ms=t,confirmed_ms=t+PERIODS[timeframe])])
    return active[-max_levels:]

def merge_levels(series,as_of_ms,*,tick_size=0):
    levels=[]
    for tf,rows in series.items():levels.extend(untouched_levels(rows,tf,as_of_ms,tick_size=tick_size))
    return sorted(levels,key=lambda v:(v['price'],v['timeframe'],v['side']))

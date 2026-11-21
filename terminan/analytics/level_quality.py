"""Closed supplied-candle eligibility; completeness is not source authentication.

Ported from Meta Analyse b1a4d6a41054f0040a88dc80b585380fb6b4f323
level_quality.py and history.validate_fixed_interval. Math owns all level prices.
"""
from dataclasses import dataclass
from datetime import datetime,timedelta,timezone
from .core import Candle,Level,untouched_levels
from market_math import candle_ohlcv_valid

FIXED_STEPS={'M1':timedelta(minutes=1),'H1':timedelta(hours=1),'D1':timedelta(days=1)}
@dataclass(frozen=True)
class LevelReport:
    levels: tuple[Level,...]
    verified: bool
    missing: int
    reason: str

def _utc(value):
    if not isinstance(value,datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('timezone-aware candle bounds required')
    return value.astimezone(timezone.utc)

def verified_levels(candles,timeframe,start,end,*,as_of):
    """Report M1/H1/D1 completeness only for an explicitly closed requested range.

    The caller authenticates the input source separately. Duplicate/unclosed or
    unaligned inputs cannot become a verified report. No calendar inference.
    """
    if type(timeframe) is not str or timeframe not in FIXED_STEPS:
        return LevelReport((),False,0,'calendar intervals need explicit boundary validation')
    start,end,as_of=map(_utc,(start,end,as_of));step=FIXED_STEPS[timeframe]
    epoch=datetime(1970,1,1,tzinfo=timezone.utc)
    if (not start<end<=as_of or (start-epoch)%step or (end-start)%step
            or (end-start)//step>20000):
        raise ValueError('invalid closed candle range')
    if not isinstance(candles,(list,tuple)) or len(candles)>20000:
        raise ValueError('bounded candle sequence required')
    eligible={}
    for candle in candles:
        if not isinstance(candle,Candle):raise ValueError('Candle DTO required')
        if not candle_ohlcv_valid(candle.open,candle.high,candle.low,candle.close,candle.volume):
            raise ValueError('invalid Candle OHLCV domain')
        stamp=_utc(candle.start)
        if start<=stamp<end:
            if (stamp-start)%step or stamp in eligible:raise ValueError('duplicate or unaligned candle')
            eligible[stamp]=candle
    expected=(end-start)//step
    missing=expected-len(eligible)
    if not eligible:return LevelReport((),False,missing,'no historical candles')
    if missing:return LevelReport((),False,missing,'missing historical candles')
    levels=untouched_levels([eligible[key] for key in sorted(eligible)],timeframe)
    return LevelReport(tuple(levels),True,0,'verified requested range')

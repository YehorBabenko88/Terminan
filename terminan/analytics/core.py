"""Deterministic price/volume logic shared by live runtime and tests."""
from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from market_math import (price_bucket, volume_profile_poc, untouched_decimal_levels,
    flow_window_metrics, wall_turnover_ratios, minute_volume_update, wall_notional)
from datetime import datetime, timezone, timedelta
from collections import deque

D = Decimal

def floor_minute(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        raise ValueError("UTC offset required")
    return ts.astimezone(timezone.utc).replace(second=0, microsecond=0)

@dataclass(frozen=True)
class Candle:
    start: datetime
    high: Decimal
    low: Decimal
    open: Decimal
    close: Decimal
    volume: Decimal = D("0")

@dataclass(frozen=True)
class Level:
    price: Decimal
    kind: str
    source_start: datetime
    timeframe: str

def untouched_levels(candles: list[Candle], timeframe: str) -> list[Level]:
    """Only CLOSED candles; equal wick touch invalidates a previous level."""
    rows = [(int(c.start.timestamp()*1000),c.high,c.low) for c in candles]
    results = untouched_decimal_levels(rows)
    dates = {int(c.start.timestamp()*1000): c.start for c in candles}
    return [Level(price,kind,dates[start],timeframe) for kind,price,start in results]

@dataclass(frozen=True)
class Trade:
    symbol: str
    time: datetime
    price: Decimal
    size: Decimal
    side: str
    high: Decimal | None = None
    low: Decimal | None = None

@dataclass
class Minute:
    start: datetime
    tick: Decimal
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal = D(0)
    quote_volume: Decimal = D(0)
    buy_volume: Decimal = D(0)
    sell_volume: Decimal = D(0)
    profile: dict[Decimal, Decimal] = field(default_factory=dict)
    complete: bool = True

    @property
    def poc(self) -> Decimal:
        return volume_profile_poc(self.profile, close=self.close)

    def add(self, t: Trade) -> None:
        if not isinstance(t,Trade) or floor_minute(t.time)!=self.start:
            raise ValueError("trade outside candle minute")
        if type(t.side) is not str or t.side.lower() not in ('buy','sell','unknown','1','2'):
            raise ValueError("invalid trade side")
        high=t.high if t.high is not None else t.price
        low=t.low if t.low is not None else t.price
        if any(not isinstance(value,Decimal) or not value.is_finite() or value<=0
               for value in (t.price,high,low)) or not low<=t.price<=high:
            raise ValueError("invalid trade OHLC")
        bucket=price_bucket(t.price,self.tick)
        totals=minute_volume_update(self.volume,self.quote_volume,
            self.buy_volume,self.sell_volume,self.profile.get(bucket,D(0)),
            t.price,t.size,t.side)
        candidate_high,candidate_low=max(self.high,high),min(self.low,low)
        # Refusals above leave every mutable field unchanged. Math alone owns
        # numeric accumulation; this is one DTO/state commit after validation.
        self.high,self.low,self.close=candidate_high,candidate_low,t.price
        self.volume,self.quote_volume,self.buy_volume,self.sell_volume,bucket_total=totals
        self.profile[bucket]=bucket_total


def new_minute(t: Trade, tick: Decimal, complete: bool = True) -> Minute:
    minute = Minute(floor_minute(t.time), tick, t.price, t.price, t.price, t.price, complete=complete)
    minute.add(t)
    return minute

class RollingFlow:
    def __init__(self):
        self.trades: deque[tuple[datetime, Decimal, str]] = deque()

    def add(self, t: Trade):
        self.trades.append((t.time, wall_notional(t.price, t.size), t.side.lower()))
        cutoff = t.time - timedelta(hours=1)
        while self.trades and self.trades[0][0] < cutoff:
            self.trades.popleft()

    def metrics(self, now: datetime) -> dict:
        out = {}
        for seconds in (60, 300, 3600):
            rows=[(int(ts.timestamp()*1000),amt,side) for ts,amt,side in self.trades]
            out[seconds] = flow_window_metrics(rows,int(now.timestamp()*1000),seconds)
        return out

    def wall_score(self, price: Decimal, size: Decimal, now: datetime) -> dict:
        metrics = self.metrics(now)
        return wall_turnover_ratios(price,size,
                    {window:data["turnover_usd"] for window,data in metrics.items()})

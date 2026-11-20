"""Rolling trade velocity and signed volume around verified price levels."""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass
from decimal import Decimal
from market_profile_math import tape_velocity_metrics, tick_distance, within_tick_distance, wall_notional

@dataclass(frozen=True)
class TapeSnapshot:
    trades_per_second: Decimal
    notional_per_second: Decimal
    buy_notional: Decimal
    sell_notional: Decimal
    distance_ticks: Decimal
    trusted: bool

class TapeVelocity:
    def __init__(self, tick_size: Decimal, window_ms=5000, proximity_ticks=20):
        if type(window_ms) is not int or not 0<window_ms<=2**63-1:
            raise ValueError("invalid tape settings")
        if (type(proximity_ticks) not in (int,str,Decimal)
                or type(proximity_ticks) is str and len(proximity_ticks)>128
                or type(proximity_ticks) is int and proximity_ticks.bit_length()>426):
            raise ValueError("invalid tape proximity")
        try:
            proximity=Decimal(proximity_ticks)
        except (ArithmeticError,TypeError,ValueError):
            raise ValueError("invalid tape proximity") from None
        # The canonical Math predicate validates finite/domain/positive settings
        # before this object publishes mutable event state.
        within_tick_distance(tick_size,tick_size,tick_size,proximity)
        self.tick_size=tick_size
        self.window_ms=window_ms
        self.proximity_ticks=proximity
        self.events=deque()
        self.last_ms=None

    def reset(self):
        self.events.clear()
        self.last_ms=None

    def add(self,execution,level_price:Decimal,*,contiguous:bool):
        if type(contiguous) is not bool:
            raise ValueError("literal contiguous flag required")
        stamp=execution.timestamp_ms
        if (type(stamp) is not int or not 0<=stamp<=2**63-1
                or type(execution.taker_side) is not str
                or execution.taker_side not in ('Buy','Sell')):
            raise ValueError("invalid tape execution DTO")
        # Quantity/price validation is Math-owned, including on reset paths.
        # An invalid gap/regression DTO must not destroy a valid prior window.
        wall_notional(execution.price,execution.quantity)
        distance=tick_distance(execution.price,level_price,self.tick_size)
        near=within_tick_distance(execution.price,level_price,self.tick_size,self.proximity_ticks)
        if not contiguous or self.last_ms is not None and stamp<self.last_ms:
            snapshot=TapeSnapshot(Decimal(0),Decimal(0),Decimal(0),Decimal(0),distance,False)
            self.reset()
            return snapshot
        cutoff=stamp-self.window_ms
        candidate=[event for event in self.events if event.timestamp_ms>=cutoff]
        candidate.append(execution)
        rows=[(event.timestamp_ms,event.price,event.quantity,event.taker_side) for event in candidate]
        trades,notional,buys,sells,distance=tape_velocity_metrics(
            rows,level_price,self.tick_size,self.window_ms,self.proximity_ticks,
            stamp,observed_price=execution.price)
        snapshot=TapeSnapshot(trades,notional,buys,sells,distance,near)
        # All DTO, Math and snapshot work succeeds before one state commit.
        self.events,self.last_ms=deque(candidate),stamp
        return snapshot

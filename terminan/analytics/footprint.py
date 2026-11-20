"""Per-price bid/ask executed volume footprint, not resting orderbook liquidity."""
from __future__ import annotations
from dataclasses import dataclass,field
from decimal import Decimal
from market_profile_math import (price_bucket, volume_profile_poc, executed_volume_delta,
    footprint_cell_update, exact_sum)

@dataclass
class FootprintCell:
    buy: Decimal=Decimal(0)
    sell: Decimal=Decimal(0)
    count: int=0

    @property
    def delta(self):
        return executed_volume_delta(self.buy,self.sell)

@dataclass
class Footprint:
    symbol: str
    start_ms: int
    interval_ms: int
    tick_size: Decimal
    cells: dict[Decimal,FootprintCell]=field(default_factory=dict)
    trusted: bool=True
    last_ts: int | None=None

    def add(self,event,*,contiguous):
        if event.symbol!=self.symbol or event.timestamp_ms<self.start_ms or event.timestamp_ms>=self.start_ms+self.interval_ms:
            raise ValueError("trade outside footprint")
        price=price_bucket(event.price,self.tick_size)
        previous=self.cells.get(price)
        buy,sell=footprint_cell_update(previous.buy if previous else Decimal(0),
            previous.sell if previous else Decimal(0),event.quantity,event.taker_side)
        trusted=self.trusted and bool(contiguous) and (self.last_ts is None or event.timestamp_ms>=self.last_ts)
        cell=FootprintCell(buy,sell,(previous.count if previous else 0)+1)
        self.cells[price]=cell
        self.trusted,self.last_ts=trusted,event.timestamp_ms

    @property
    def poc(self):
        if not self.cells:
            return None
        return volume_profile_poc({price: exact_sum((cell.buy,cell.sell)) for price,cell in self.cells.items()})

    @property
    def delta(self):
        return exact_sum(c.delta for c in self.cells.values())

    def snapshot(self):
        return {"symbol":self.symbol,"start_ms":self.start_ms,
                "trusted":self.trusted,"poc":str(self.poc) if self.poc is not None else None,
                "delta":str(self.delta),
                "prices":{str(p):{"buy":str(c.buy),"sell":str(c.sell),
                                   "delta":str(c.delta),"trades":c.count}
                          for p,c in sorted(self.cells.items())}}

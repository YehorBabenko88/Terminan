"""Per-price bid/ask executed volume footprint, not resting orderbook liquidity."""
from __future__ import annotations
from dataclasses import dataclass,field
from decimal import Decimal
from market_math import (price_bucket, volume_profile_poc, executed_volume_delta,
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

    def __post_init__(self):
        if (type(self.symbol) is not str or not 1<=len(self.symbol)<=30
                or type(self.start_ms) is not int or not 0<=self.start_ms<=2**63-1
                or type(self.interval_ms) is not int or not 0<self.interval_ms<=604800000
                or type(self.trusted) is not bool or type(self.cells) is not dict
                or len(self.cells)>20000):
            raise ValueError("invalid footprint settings")
        if self.last_ts is not None and (type(self.last_ts) is not int
                or not self.start_ms<=self.last_ts<self.start_ms+self.interval_ms):
            raise ValueError("invalid footprint clock")
        price_bucket(self.tick_size,self.tick_size)
        for price,cell in self.cells.items():
            if (not isinstance(price,Decimal) or not price.is_finite() or price<=0
                    or type(cell) is not FootprintCell or type(cell.count) is not int or cell.count<0):
                raise ValueError("invalid footprint cell")
            footprint_cell_update(cell.buy,cell.sell,Decimal(0),'Buy')

    def add(self,event,*,contiguous):
        if type(contiguous) is not bool:
            raise ValueError("literal contiguous flag required")
        if type(event.timestamp_ms) is not int:
            raise ValueError("invalid footprint execution clock")
        if event.symbol!=self.symbol or event.timestamp_ms<self.start_ms or event.timestamp_ms>=self.start_ms+self.interval_ms:
            raise ValueError("trade outside footprint")
        price=price_bucket(event.price,self.tick_size)
        previous=self.cells.get(price)
        buy,sell=footprint_cell_update(previous.buy if previous else Decimal(0),
            previous.sell if previous else Decimal(0),event.quantity,event.taker_side)
        trusted=self.trusted and contiguous and (self.last_ts is None or event.timestamp_ms>=self.last_ts)
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

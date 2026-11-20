"""Bounded multi-symbol footprint accumulation with explicit gaps."""
from __future__ import annotations
from collections import deque
from .footprint import Footprint

class FootprintEngine:
    def __init__(self,tick_sizes,interval_ms=60000,max_closed=500):
        if interval_ms<=0 or max_closed<=0:
            raise ValueError("invalid footprint retention")
        self.tick_sizes=tick_sizes
        self.interval_ms=interval_ms
        self.current={}
        self.closed=deque(maxlen=max_closed)

    def execution(self,event,*,contiguous):
        tick=self.tick_sizes.get(event.symbol)
        if tick is None:
            raise ValueError("unknown instrument")
        if type(event.timestamp_ms) is not int or event.timestamp_ms<0:
            raise ValueError("invalid execution timestamp")
        slot=(event.timestamp_ms//self.interval_ms)*self.interval_ms
        old=self.current.get(event.symbol)
        if old is not None and slot==old.start_ms:
            old.add(event,contiguous=contiguous)
            return old
        # Validate and aggregate into an unpublished candidate. A refused next
        # or late event must not close, replace, or untrust the current bucket.
        candidate=Footprint(event.symbol,slot,self.interval_ms,tick,trusted=bool(contiguous))
        candidate.add(event,contiguous=contiguous)
        if old is not None and slot<old.start_ms:
            old.trusted=False
            return None
        if old is not None:
            if slot-old.start_ms!=self.interval_ms:
                old.trusted=False
            self.closed.append(old)
        self.current[event.symbol]=candidate
        return candidate

    def gap(self,symbol):
        old=self.current.pop(symbol,None)
        if old:
            old.trusted=False
            self.closed.append(old)

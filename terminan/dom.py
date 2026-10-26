"""Independent, offline-first order-book engine. No exchange or order-submission access."""
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Iterable, Mapping


class BookStatus(str, Enum):
    AWAITING_SNAPSHOT = "AWAITING_SNAPSHOT"
    LIVE = "LIVE"
    GAP = "GAP"
    DISCONNECTED = "DISCONNECTED"
    STALE = "STALE"


@dataclass(frozen=True)
class Level:
    side: str
    price_ticks: int
    quantity_lots: int

    def __post_init__(self):
        if self.side not in ("bid", "ask"):
            raise ValueError("side must be bid or ask")
        if type(self.price_ticks) is not int or type(self.quantity_lots) is not int:
            raise ValueError("price_ticks and quantity_lots must be integers")
        if self.price_ticks < 0 or self.quantity_lots < 0:
            raise ValueError("negative price/quantity")


@dataclass(frozen=True)
class Snapshot:
    epoch: str
    sequence: int
    levels: tuple[Level, ...]


@dataclass(frozen=True)
class Delta:
    epoch: str
    sequence: int
    previous_sequence: int
    levels: tuple[Level, ...]


@dataclass(frozen=True)
class BookView:
    version: int
    epoch: str | None
    sequence: int | None
    status: BookStatus
    bids: tuple[tuple[int, int], ...]
    asks: tuple[tuple[int, int], ...]
    error: str | None = None

    @property
    def best_bid(self):
        return self.bids[0][0] if self.bids else None

    @property
    def best_ask(self):
        return self.asks[0][0] if self.asks else None

    @property
    def crossed(self):
        return self.best_bid is not None and self.best_ask is not None and self.best_bid >= self.best_ask


def _validate_header(epoch, sequence):
    if not isinstance(epoch, str) or not epoch or len(epoch) > 128:
        raise ValueError("invalid epoch")
    if type(sequence) is not int or sequence < 0:
        raise ValueError("invalid sequence")


def _changes(levels: Iterable[Level]):
    updates = []
    for level in levels:
        if not isinstance(level, Level):
            raise ValueError("invalid level")
        updates.append(level)
        if len(updates) > 100_000:
            raise ValueError("batch too large")
    return updates


class BookEngine:
    """Single-writer engine: validate before committing, reject sequence gaps."""

    def __init__(self, max_levels=100000):
        if type(max_levels) is not int or not 1<=max_levels<=100000:
            raise ValueError('invalid book limit')
        self.max_levels=max_levels
        self._retired_epochs=set()
        self._bids = {}
        self._asks = {}
        self._version = 0
        self._epoch = None
        self._sequence = None
        self._status = BookStatus.AWAITING_SNAPSHOT
        self._error = None

    @property
    def view(self):
        return BookView(
            self._version, self._epoch, self._sequence, self._status,
            tuple(sorted(self._bids.items(), reverse=True)),
            tuple(sorted(self._asks.items())), self._error
        )

    def snapshot(self, msg: Snapshot):
        _validate_header(msg.epoch, msg.sequence)
        if msg.epoch in self._retired_epochs:return False
        if self._epoch is not None and msg.epoch!=self._epoch and len(self._retired_epochs)>=128:
            raise ValueError('epoch history limit exceeded; replace engine')
        changes = _changes(msg.levels)
        # Invalidating the book does not erase its sequence watermark.
        # Recovery must not promote a delayed or duplicate snapshot to LIVE.
        if self._epoch == msg.epoch and self._sequence is not None and msg.sequence <= self._sequence:
            return False
        bids, asks = {}, {}
        for level in changes:
            side = bids if level.side == "bid" else asks
            if level.quantity_lots:
                side[level.price_ticks] = level.quantity_lots
            else:
                side.pop(level.price_ticks, None)
        if len(bids)+len(asks)>self.max_levels:raise ValueError('book limit exceeded')
        self._bids, self._asks = bids, asks
        if self._epoch is not None and self._epoch!=msg.epoch:self._retired_epochs.add(self._epoch)
        self._epoch, self._sequence = msg.epoch, msg.sequence
        self._status, self._error = BookStatus.LIVE, None
        self._version += 1
        return True

    def delta(self, msg: Delta):
        _validate_header(msg.epoch, msg.sequence)
        if msg.epoch in self._retired_epochs:return False
        if type(msg.previous_sequence) is not int or msg.previous_sequence < 0:
            raise ValueError("invalid previous_sequence")
        changes = _changes(msg.levels)
        if self._status != BookStatus.LIVE:
            return False
        if msg.epoch != self._epoch:
            self._status, self._error = BookStatus.GAP, "epoch mismatch"
            return False
        if msg.sequence <= self._sequence:
            return False
        if msg.previous_sequence != self._sequence:
            self._status, self._error = BookStatus.GAP, "sequence gap"
            return False
        bids, asks = self._bids.copy(), self._asks.copy()
        for level in changes:
            side = bids if level.side == "bid" else asks
            if level.quantity_lots == 0:
                side.pop(level.price_ticks, None)
            else:
                side[level.price_ticks] = level.quantity_lots
        if len(bids)+len(asks)>self.max_levels:raise ValueError('book limit exceeded')
        self._bids, self._asks = bids, asks
        self._sequence = msg.sequence
        self._version += 1
        return True

    def disconnected(self):
        self._status, self._error = BookStatus.DISCONNECTED, "source disconnected"

    def stale(self):
        if self._status == BookStatus.LIVE:
            self._status, self._error = BookStatus.STALE, "market data stale"


def grouped(view: BookView, width: int, anchor: int = 0):
    """Aggregate complete book before clipping; keep bid and ask separate."""
    if type(width) is not int or width <= 0 or type(anchor) is not int:
        raise ValueError("invalid aggregation")
    def one(levels, descending):
        buckets = {}
        for price, qty in levels:
            key = anchor + ((price - anchor) // width) * width
            buckets[key] = buckets.get(key, 0) + qty
        return tuple(sorted(buckets.items(), reverse=descending))
    return {"bids": one(view.bids, True), "asks": one(view.asks, False)}


def viewport(view: BookView, top_tick: int, rows: int, width: int = 1, anchor: int = 0):
    if type(top_tick) is not int or type(rows) is not int or not 0 < rows <= 10000:
        raise ValueError("invalid viewport")
    buckets = grouped(view, width, anchor)
    top_tick=anchor+((top_tick-anchor)//width)*width
    lo = top_tick - (rows - 1) * width
    bids, asks = dict(buckets["bids"]), dict(buckets["asks"])
    return tuple(
        {"price_ticks": price, "bid_lots": bids.get(price, 0), "ask_lots": asks.get(price, 0)}
        for price in range(top_tick, lo - 1, -width)
    )


def serializable(view: BookView, width: int = 1):
    buckets = grouped(view, width)
    return {
        "version": view.version, "epoch": view.epoch, "sequence": view.sequence,
        "status": view.status.value, "error": view.error,
        "crossed": view.crossed,
        "best_bid": view.best_bid, "best_ask": view.best_ask,
        "bids": buckets["bids"], "asks": buckets["asks"],
    }

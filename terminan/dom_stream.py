"""Bounded, deterministic single-writer stream bridge for the offline DOM engine.

No networking, threading, credentials or order submission. Feed adapter is external.
"""
from collections import deque
from dataclasses import dataclass
from .dom import BookEngine, BookStatus, Delta, Snapshot, serializable


@dataclass(frozen=True)
class FeedEnvelope:
    symbol: str
    payload: Snapshot | Delta

    def __post_init__(self):
        if not isinstance(self.symbol, str) or not self.symbol or len(self.symbol) > 64:
            raise ValueError("invalid symbol")
        if not isinstance(self.payload, (Snapshot, Delta)):
            raise ValueError("invalid payload")


class BoundedFeed:
    """A single writer drains events; overflow invalidates the book until a snapshot."""

    def __init__(self, capacity=4096):
        if type(capacity) is not int or capacity < 1:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._queue = deque()
        self._engines = {}
        self._invalid = set()
        self.dropped = 0

    def engine(self, symbol):
        if not isinstance(symbol, str) or not symbol or len(symbol) > 64:
            raise ValueError("invalid symbol")
        return self._engines.setdefault(symbol, BookEngine())

    def publish(self, envelope: FeedEnvelope):
        if not isinstance(envelope, FeedEnvelope):
            raise ValueError("invalid envelope")
        if len(self._queue) >= self.capacity:
            # Dropping any delta destroys sequence continuity. Clear all queued
            # messages and invalidate all affected books rather than replay partial data.
            affected = {item.symbol for item in self._queue}
            affected.add(envelope.symbol)
            self.dropped += len(self._queue) + 1
            self._queue.clear()
            self._invalid.update(affected)
            for symbol in affected:
                self.engine(symbol).disconnected()
            return False
        self._queue.append(envelope)
        return True

    def drain(self, limit=1000):
        if type(limit) is not int or limit < 1:
            raise ValueError("invalid drain limit")
        applied = 0
        for _ in range(min(limit, len(self._queue))):
            envelope = self._queue.popleft()
            engine = self.engine(envelope.symbol)
            if envelope.symbol in self._invalid:
                if not isinstance(envelope.payload, Snapshot):
                    continue
                self._invalid.discard(envelope.symbol)
            if isinstance(envelope.payload, Snapshot):
                applied += bool(engine.snapshot(envelope.payload))
            else:
                applied += bool(engine.delta(envelope.payload))
        return applied

    @property
    def queued(self):
        return len(self._queue)


class FrameGate:
    """Coalesce unchanged versions; caller supplies monotonic timestamps in nanoseconds."""

    def __init__(self, max_fps=30):
        if type(max_fps) is not int or not 1 <= max_fps <= 240:
            raise ValueError("max_fps out of range")
        self.interval_ns = (1_000_000_000 + max_fps - 1) // max_fps
        self._last_time = None
        self._last_key = None

    def ready(self, symbol, view, now_ns):
        if type(now_ns) is not int or now_ns < 0:
            raise ValueError("invalid monotonic timestamp")
        key = (symbol, view.version, view.status, view.error)
        if self._last_key == key:
            return False
        if self._last_time is not None and now_ns - self._last_time < self.interval_ns:
            return False
        self._last_key, self._last_time = key, now_ns
        return True

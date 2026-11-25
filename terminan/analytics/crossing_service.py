"""Event-driven, fail-closed crossing cleanup for app-owned terminal levels.

Ported from Meta Analyse b1a4d6a41054f0040a88dc80b585380fb6b4f323
src/meta_analyse/crossing_service.py (git blob
81791e39e22c00adedf311bf5d2896c2603dfaa8).
The only adaptation: Terminan's LevelSync.crossed requires an explicit literal
continuity flag and the "exchange_execution" source, so this service passes
them for the observed, contiguous execution pair it already verified. The
service never bridges gaps, reconnects or reorderings, and never places orders.
"""
from __future__ import annotations

import asyncio
from decimal import Decimal

SOURCE = "exchange_execution"


class CrossingService:
    def __init__(self, level_sync, connection_for_symbol):
        self.sync = level_sync
        self.connection_for_symbol = connection_for_symbol
        self.last = {}
        self.locks = {}

    async def execution(self, event, *, contiguous: bool):
        symbol = event.symbol
        lock = self.locks.setdefault(symbol, asyncio.Lock())
        async with lock:
            previous = self.last.get(symbol)
            current = Decimal(event.price)
            # Never bridge reconnects, reorderings, or unverified continuity.
            if not contiguous:
                self.last.pop(symbol, None)
                return 0
            self.last[symbol] = current
            if previous is None:
                return 0
            connection = self.connection_for_symbol(symbol)
            if connection is None:
                return 0
            try:
                return await self.sync.crossed(connection, symbol, previous, current,
                                               contiguous=True, source=SOURCE)
            except Exception:
                # Terminal state uncertain: stop assuming continuity; reread on next valid tick.
                self.last.pop(symbol, None)
                raise

    def gap(self, symbol):
        self.last.pop(symbol, None)

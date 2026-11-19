"""Offline-only Meta PaperEngine compatibility in the single Terminan strategy owner.

Ported from meta_analyse/src/meta_analyse/core.py at pinned source
9d0fb5c79a5da13b23f8daa066035b09f676a6fc.

Expects a CLOSED minute whose POC has already been calculated by the
canonical Math SDK from Grid-sourced data. It never computes POC, connects
to an exchange, persists market rows, or submits an order. Its trade
arithmetic is execution-fill accounting, not a statistical/math kernel.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

D = Decimal


@dataclass(frozen=True)
class Position:
    symbol: str
    side: str
    entry: Decimal
    target: Decimal
    stop: Decimal
    size: Decimal
    entry_time: datetime
    entry_fee: Decimal


@dataclass(frozen=True)
class PaperFill:
    symbol: str
    side: str
    entry: Decimal
    exit: Decimal
    reason: str
    gross: Decimal
    fees: Decimal
    net: Decimal
    exit_time: datetime


@dataclass(frozen=True)
class ClosedMinute:
    """Math-computed POC; source authenticity is NOT implied by this DTO."""
    start: datetime
    poc: Decimal
    complete: bool
    source: str = "UNATTESTED"


@dataclass(frozen=True)
class ExecutionTrade:
    symbol: str
    time: datetime
    price: Decimal


class PaperEngine:
    """Deterministic paper-only next-minute POC strategy; starts disabled."""

    def __init__(self, *, notional=D("100"), threshold=D("0.015"),
                 stop_pct=D("0.005"), fee_rate=D("0.0006"),
                 slippage_bps=D("2")):
        self.notional = D(notional)
        self.threshold = D(threshold)
        self.stop_pct = D(stop_pct)
        self.fee_rate = D(fee_rate)
        self.slippage = D(slippage_bps) / D(10000)
        if (not self.notional.is_finite() or self.notional <= 0
                or any(not value.is_finite() or value < 0 for value in
                       (self.threshold, self.stop_pct, self.fee_rate, self.slippage))
                or self.fee_rate >= 1 or self.slippage >= 1):
            raise ValueError("invalid paper execution parameters")
        self.reference: dict[str, tuple[datetime, Decimal]] = {}
        self.positions: dict[str, Position] = {}
        self.fills: list[PaperFill] = []
        self.enabled = False

    @staticmethod
    def _minute_start(timestamp: datetime) -> datetime:
        if not isinstance(timestamp, datetime) or timestamp.tzinfo is None:
            raise ValueError("aware execution timestamp required")
        return timestamp.astimezone(timezone.utc).replace(second=0, microsecond=0)

    def on_closed_minute(self, symbol: str, minute: ClosedMinute) -> None:
        if not isinstance(symbol, str) or not symbol:
            raise ValueError("invalid symbol")
        if minute.complete is not True:
            self.reference.pop(symbol, None)
            return
        start = self._minute_start(minute.start)
        if start != minute.start.astimezone(timezone.utc):
            raise ValueError("minute start not aligned")
        poc = D(minute.poc)
        if not poc.is_finite() or poc <= 0:
            raise ValueError("invalid math POC")
        self.reference[symbol] = (start, poc)

    def on_gap(self, symbol: str) -> None:
        """Invalidate possible new entries; retain existing positions."""
        self.reference.pop(symbol, None)

    def on_trade(self, trade: ExecutionTrade) -> PaperFill | None:
        if not self.enabled:
            return None
        if not isinstance(trade.symbol, str) or not trade.symbol:
            raise ValueError("invalid symbol")
        timestamp = self._minute_start(trade.time)
        price = D(trade.price)
        if not price.is_finite() or price <= 0:
            raise ValueError("invalid execution price")
        symbol = trade.symbol
        position = self.positions.get(symbol)
        if position:
            if position.side == "long":
                triggered = ("stop" if price <= position.stop else
                             "target" if price >= position.target else "")
                if not triggered:
                    return None
                exit_price = (min(price, position.stop) if triggered == "stop"
                              else position.target)
                exit_price *= D(1) - self.slippage
                gross = (exit_price - position.entry) * position.size
            else:
                triggered = ("stop" if price >= position.stop else
                             "target" if price <= position.target else "")
                if not triggered:
                    return None
                exit_price = (max(price, position.stop) if triggered == "stop"
                              else position.target)
                exit_price *= D(1) + self.slippage
                gross = (position.entry - exit_price) * position.size
            exit_fee = position.size * exit_price * self.fee_rate
            fill = PaperFill(
                symbol, position.side, position.entry, exit_price,
                triggered, gross, position.entry_fee + exit_fee,
                gross - position.entry_fee - exit_fee, trade.time,
            )
            self.fills.append(fill)
            del self.positions[symbol]
            return fill
        ref = self.reference.get(symbol)
        if not ref or timestamp != ref[0] + timedelta(minutes=1):
            return None
        poc = ref[1]
        if price >= poc * (D(1) + self.threshold):
            side = "short"
            entry = price * (D(1) - self.slippage)
            stop = entry * (D(1) + self.stop_pct)
        elif price <= poc * (D(1) - self.threshold):
            side = "long"
            entry = price * (D(1) + self.slippage)
            stop = entry * (D(1) - self.stop_pct)
        else:
            return None
        if entry == poc:
            return None
        size = self.notional / entry
        self.positions[symbol] = Position(
            symbol, side, entry, poc, stop, size, trade.time,
            self.notional * self.fee_rate,
        )
        self.reference.pop(symbol, None)
        return None

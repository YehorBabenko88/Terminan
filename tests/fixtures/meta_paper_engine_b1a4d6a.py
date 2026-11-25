"""FROZEN REFERENCE FIXTURE - do not edit; used only by test_meta_paper_differential.py.

Provenance (verbatim byte copy of four top-level definitions):
  repository: YehorBabenko88/meta_analyse
  commit:     b1a4d6a41054f0040a88dc80b585380fb6b4f323 (branch codex/stage10-e-meta)
  path:       src/meta_analyse/core.py
  git blob:   ea9d2acee3fadf94bfce4ea9865d10d8896b6794
  file sha256: 5b79a1c700400fb0259e40373018c71f4e208cce81b54049b3bb5a5212f3bc88
Segments (source line ranges in that file, sha256 of the exact bytes):
  floor_minute: lines 11-14 sha256 1fb36693d9a09fa66a0b48fa968f83e5e33f3b99fd517578a4564e5677cfdf65
  Position: lines 88-97 sha256 098bcd9c73488874e732529263e96e09b8738ecc3344e1c245915954320def63
  PaperFill: lines 99-109 sha256 5823a88bc96dec6feea11e71c76fdf2428bbbec9bb381bfaebbfa34005e9dcb7
  PaperEngine: lines 111-175 sha256 319877804493e4ef7cdab2ca17afcc39fbfd0dc1e88d0e419423afb561750b92

Only the imports these definitions need are added above them; no other
Meta code (Minute/POC computation, market_profile_math) is copied. This is
NOT runtime code: Terminan's terminan.paper.PaperEngine is the only engine.
"""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime, timezone, timedelta

D = Decimal

SEGMENT_SHA256 = {
    'floor_minute': '1fb36693d9a09fa66a0b48fa968f83e5e33f3b99fd517578a4564e5677cfdf65',
    'Position': '098bcd9c73488874e732529263e96e09b8738ecc3344e1c245915954320def63',
    'PaperFill': '5823a88bc96dec6feea11e71c76fdf2428bbbec9bb381bfaebbfa34005e9dcb7',
    'PaperEngine': '319877804493e4ef7cdab2ca17afcc39fbfd0dc1e88d0e419423afb561750b92',
}

def floor_minute(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        raise ValueError("UTC offset required")
    return ts.astimezone(timezone.utc).replace(second=0, microsecond=0)

@dataclass
class Position:
    symbol: str
    side: str
    entry: Decimal
    target: Decimal
    stop: Decimal
    size: Decimal
    entry_time: datetime
    entry_fee: Decimal

@dataclass
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

class PaperEngine:
    """Next-minute POC paper mean reversion, one position per instrument."""
    def __init__(self, *, notional=D("100"), threshold=D("0.015"), stop_pct=D("0.005"), fee_rate=D("0.0006"), slippage_bps=D("2")):
        self.notional = D(notional)
        self.threshold = D(threshold)
        self.stop_pct = D(stop_pct)
        self.fee_rate = D(fee_rate)
        self.slippage = D(slippage_bps) / D(10000)
        self.reference: dict[str, tuple[datetime, Decimal]] = {}
        self.positions: dict[str, Position] = {}
        self.fills: list[PaperFill] = []
        self.enabled = False

    def on_closed_minute(self, symbol: str, minute: Minute) -> None:
        if not minute.complete:
            self.reference.pop(symbol, None)
            return
        self.reference[symbol] = (minute.start, minute.poc)

    def on_trade(self, trade: Trade) -> PaperFill | None:
        if not self.enabled:
            return None
        symbol = trade.symbol
        position = self.positions.get(symbol)
        if position:
            if position.side == "long":
                triggered = "stop" if trade.price <= position.stop else ("target" if trade.price >= position.target else "")
                exit_price = min(trade.price, position.stop) if triggered == "stop" else position.target
                exit_price *= (D(1) - self.slippage)
                gross = (exit_price - position.entry) * position.size
            else:
                triggered = "stop" if trade.price >= position.stop else ("target" if trade.price <= position.target else "")
                exit_price = max(trade.price, position.stop) if triggered == "stop" else position.target
                exit_price *= (D(1) + self.slippage)
                gross = (position.entry - exit_price) * position.size
            if not triggered:
                return None
            exit_fee = position.size * exit_price * self.fee_rate
            fill = PaperFill(symbol, position.side, position.entry, exit_price, triggered, gross,
                             position.entry_fee + exit_fee, gross - position.entry_fee - exit_fee, trade.time)
            self.fills.append(fill)
            del self.positions[symbol]
            return fill
        ref = self.reference.get(symbol)
        if not ref or floor_minute(trade.time) != ref[0] + timedelta(minutes=1):
            return None
        poc = ref[1]
        if poc <= 0:
            return None
        if trade.price >= poc * (D(1) + self.threshold):
            side = "short"
            entry = trade.price * (D(1) - self.slippage)
            stop = entry * (D(1) + self.stop_pct)
        elif trade.price <= poc * (D(1) - self.threshold):
            side = "long"
            entry = trade.price * (D(1) + self.slippage)
            stop = entry * (D(1) - self.stop_pct)
        else:
            return None
        if entry == poc:
            return None
        size = self.notional / entry
        self.positions[symbol] = Position(symbol, side, entry, poc, stop, size, trade.time, self.notional * self.fee_rate)
        self.reference.pop(symbol, None)
        return None

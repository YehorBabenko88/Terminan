"""Offline-only Meta PaperEngine compatibility in the single Terminan strategy owner.

Ported from meta_analyse/src/meta_analyse/core.py at pinned source
9d0fb5c79a5da13b23f8daa066035b09f676a6fc.

Expects a CLOSED minute whose POC has already been calculated by the
canonical Math SDK from Grid-sourced data. It never computes POC, connects
to an exchange, persists market rows, or submits an order. Its trade
arithmetic is execution-fill accounting, not a statistical/math kernel.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from .contracts import (DataRequirement, StrategyDefinition,
                        StrategyRegistry, strategy_fingerprint)
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
import json
import re

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
        self.last_trade_time: dict[str, datetime] = {}
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
        previous = self.reference.get(symbol)
        if previous is not None and start < previous[0]:
            raise ValueError("out-of-order closed minute")
        self.reference[symbol] = (start, poc)

    def on_math_closed_minute(self, symbol, start, request, *, compute=None):
        """Consume the installed canonical Math SDK, never a local POC copy.

        Caller-supplied snapshot digest is UNATTESTED by the SDK. This method
        is offline/paper-only and does not qualify public Grid market feeds.
        """
        if (not isinstance(request, dict)
                or request.get("schema") != "math.market.compute.v1"
                or request.get("execution_authority") is not False
                or not isinstance(request.get("operations"), list)
                or len(request["operations"]) != 1
                or not isinstance(request["operations"][0], dict)
                or request["operations"][0].get("operation") != "volume_profile_poc"):
            raise ValueError("invalid Math POC request")
        if compute is None:
            from market_compute_api import compute_batch
            compute = compute_batch
        result = compute(request)
        if (not isinstance(result, dict)
                or result.get("schema") != "math.market.result.v1"
                or result.get("execution_authority") is not False
                or result.get("trading_authorized") is not False
                or result.get("provenance") != "CALLER_SUPPLIED_UNATTESTED"
                or result.get("source") != request.get("source")
                or not isinstance(result.get("results"), list)
                or len(result["results"]) != 1
                or not isinstance(result["results"][0], dict)
                or result["results"][0].get("operation") != "volume_profile_poc"
                or result["results"][0].get("value") is None):
            raise ValueError("Math POC result not admitted")
        minute = ClosedMinute(
            self._minute_start(start),
            D(result["results"][0]["value"]),
            True,
            "CALLER_SUPPLIED_UNATTESTED",
        )
        self.on_closed_minute(symbol, minute)

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
        prior = self.last_trade_time.get(symbol)
        if prior is not None and trade.time < prior:
            raise ValueError("out-of-order paper execution")
        self.last_trade_time[symbol] = trade.time
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


# One application registry instance, using the ONLY implementation owned by
# terminan.contracts. Registration is inert: no workers, collectors or orders.
STRATEGIES = StrategyRegistry()
STRATEGIES.register(StrategyDefinition(
    id="meta.poc.next_minute",
    version="1",
    requirements=(
        DataRequirement("public_trades"),
        DataRequirement("candles", ("1m",), required=False),
    ),
    implementation=PaperEngine,
))


REPLAY_SCHEMA = "terminan.paper.replay.v1"
REPLAY_RESULT = "terminan.paper.result.v1"
_MAX_EVENTS = 1024
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_SYMBOL = re.compile(r"[A-Z0-9]{2,30}")
_RUN_ID = re.compile(r"[A-Za-z0-9_.:-]{1,64}")


def _timestamp(value):
    if type(value) is not int or not 0 <= value <= 4102444800000:
        raise ValueError("invalid UTC millisecond timestamp")
    return _EPOCH + timedelta(milliseconds=value)


def _canonical_json(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid JSON replay request") from exc


def _serialize(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_serialize(item) for item in value]
    return value


def replay_paper(request, *, compute=None):
    """Run bounded deterministic *offline* paper replay, never market orders.

    Every closed minute obtains POC from the installed canonical Math SDK.
    The request's source SHA is caller-supplied, NOT authenticated Grid data.
    This API cannot advertise live/history qualification or persist results.
    """
    expected = {"schema", "run_id", "source", "parameters", "events"}
    if (type(request) is not dict or
            set(request) not in (expected, expected | {"strategy"}) or
            request["schema"] != REPLAY_SCHEMA or
            type(request["run_id"]) is not str or
            not _RUN_ID.fullmatch(request["run_id"])):
        raise ValueError("invalid paper replay contract")
    # Binding to the same real registry used by Terminan, not a second
    # replay-only strategy map. The optional strategy descriptor is backward
    # compatible with v1 offline request fixtures.
    definition = STRATEGIES.discover()[0]
    choice = request.get("strategy", {
        "id": definition.id, "version": definition.version,
    })
    if (type(choice) is not dict or set(choice) != {"id", "version"}
            or type(choice["id"]) is not str
            or type(choice["version"]) is not str
            or choice["id"] != definition.id
            or choice["version"] != definition.version
            or not definition.enabled):
        raise ValueError("strategy not registered or disabled")
    if len(_canonical_json(request)) > 262144:
        raise ValueError("paper replay body limit")
    events = request["events"]
    params = request["parameters"]
    if (type(events) is not list or not 1 <= len(events) <= _MAX_EVENTS or
            type(params) is not dict or
            not set(params).issubset({
                "notional", "threshold", "stop_pct", "fee_rate", "slippage_bps"
            }) or any(type(value) is not str for value in params.values())):
        raise ValueError("paper replay policy or event limit")
    if (type(request["source"]) is not dict or
            set(request["source"]) != {"snapshot_sha256", "as_of_ms", "units"}):
        raise ValueError("invalid Math source envelope")
    source = request["source"]
    digest = source["snapshot_sha256"]
    if (type(digest) is not str or len(digest) != 64
            or any(char not in "0123456789abcdef" for char in digest)
            or type(source["as_of_ms"]) is not int
            or not 0 <= source["as_of_ms"] <= 2**63 - 1
            or source["units"] != {"price": "quote/base", "volume": "base"}):
        raise ValueError("invalid source identity or units")
    engine = PaperEngine(**params)
    engine.enabled = True  # Only offline simulated fills; no live order route.
    previous_ms = -1
    for event in events:
        if type(event) is not dict or "kind" not in event:
            raise ValueError("invalid paper replay event")
        kind = event["kind"]
        stamp = event.get("event_ms")
        timestamp = _timestamp(stamp)
        if stamp < previous_ms:
            raise ValueError("out-of-order replay events")
        previous_ms = stamp
        symbol = event.get("symbol")
        if type(symbol) is not str or not _SYMBOL.fullmatch(symbol):
            raise ValueError("invalid paper replay symbol")
        if kind == "closed_minute":
            if set(event) != {"kind", "event_ms", "symbol", "profile", "close"}:
                raise ValueError("invalid closed-minute event")
            if stamp % 60000:
                raise ValueError("closed minute must be published at minute boundary")
            math_request = {
                "schema": "math.market.compute.v1",
                "execution_authority": False,
                "source": request["source"],
                "operations": [{
                    "operation": "volume_profile_poc",
                    "input": {"profile": event["profile"], "close": event["close"]},
                }],
            }
            engine.on_math_closed_minute(
                symbol, timestamp - timedelta(minutes=1),
                math_request, compute=compute,
            )
        elif kind == "trade":
            if set(event) != {"kind", "event_ms", "symbol", "price"}:
                raise ValueError("invalid trade event")
            if type(event["price"]) is not str:
                raise ValueError("invalid execution price encoding")
            engine.on_trade(ExecutionTrade(symbol, timestamp, D(event["price"])))
        elif kind == "gap":
            if set(event) != {"kind", "event_ms", "symbol"}:
                raise ValueError("invalid source gap event")
            engine.on_gap(symbol)
        else:
            raise ValueError("unknown replay event kind")
    result = {
        "schema": REPLAY_RESULT,
        "run_id": request["run_id"],
        "strategy": {
            "id": definition.id,
            "version": definition.version,
            "fingerprint": strategy_fingerprint(definition),
        },
        "status": "OFFLINE_UNATTESTED",
        "provenance": "CALLER_SUPPLIED_UNATTESTED",
        "execution_authority": False,
        "trading_authorized": False,
        "source": request["source"],
        "request_sha256": sha256(_canonical_json(request)).hexdigest(),
        "events_processed": len(events),
        "fills": [_serialize(asdict(fill)) for fill in engine.fills],
        "open_positions": {
            symbol: _serialize(asdict(position))
            for symbol, position in sorted(engine.positions.items())
        },
    }
    result["result_sha256"] = sha256(_canonical_json(result)).hexdigest()
    return result


# Historical trade sizing/equity policy transferred from the old Math research
# helpers (math PR #121 / python/history_sizing.py). These are trading
# execution/portfolio accounting decisions and belong exclusively to Terminan.
# Legacy float behavior and return fields are preserved for existing receipts;
# they are NOT mathematical statistics or live order quantities.


def apply_sizing(trades, mode="FIXED", base_size=1.0, multiplier=2.0,
                 max_steps=3, max_size=4.0):
    """Apply legacy FIXED/MARTINGALE/ANTI_MARTINGALE paper sizing policy."""
    out = []
    step = 0
    for row in trades:
        x = dict(row)
        if mode == "FIXED":
            size = float(base_size)
        elif mode in ("MARTINGALE", "ANTI_MARTINGALE"):
            size = min(float(max_size), float(base_size) * (float(multiplier) ** step))
        else:
            raise ValueError("unknown sizing mode")
        x["sizing_mode"] = mode
        x["size_multiplier"] = size
        for k in ("pnl", "fees", "slippage", "mfe", "mae"):
            if k in x and x[k] is not None:
                x[k] = float(x[k]) * size
        net = trade_net_pnl(x)
        out.append(x)
        if mode == "MARTINGALE":
            step = min(int(max_steps), step + 1) if net < 0 else 0
        elif mode == "ANTI_MARTINGALE":
            step = min(int(max_steps), step + 1) if net > 0 else 0
    return out


def ruin_stats(trades, starting_equity=100.0, ruin_fraction=.5):
    """Legacy simulated trading account equity/ruin ledger, NOT Math research."""
    equity = peak = float(starting_equity)
    min_eq = equity
    max_dd = 0.0
    ruined = False
    threshold = starting_equity * float(ruin_fraction)
    for x in trades:
        equity += trade_net_pnl(x)
        peak = max(peak, equity)
        min_eq = min(min_eq, equity)
        max_dd = max(max_dd, peak - equity)
        if equity <= threshold:
            ruined = True
    return {
        "ending_equity": equity,
        "min_equity": min_eq,
        "max_drawdown": max_dd,
        "ruin_threshold": threshold,
        "ruined": ruined,
    }


def trade_net_pnl(row):
    """Old Math history_statistics._net: virtual execution PnL accounting only."""
    return float(row.get("pnl", 0)) - float(row.get("fees", 0)) - float(row.get("slippage", 0))

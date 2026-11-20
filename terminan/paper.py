"""Canonical offline paper execution in the single Terminan strategy owner.

Ported from meta_analyse/src/meta_analyse/core.py at pinned source
9d0fb5c79a5da13b23f8daa066035b09f676a6fc.

Expects a CLOSED minute whose POC has already been calculated by the
canonical Math SDK from MarketData-sourced data. It never computes POC, connects
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
import os
import json
import re
from .paper_ledger import PaperReplayLedger, canonical_json

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


def _paper_math():
    import market_profile_math
    return market_profile_math


def _policy_decimal(value):
    if type(value) not in (str,int,Decimal):raise ValueError('Decimal policy value required')
    return D(value)


class PaperEngine:
    """Deterministic paper-only next-minute POC strategy; starts disabled."""

    def __init__(self, *, notional=D("100"), threshold=D("0.015"),
                 stop_pct=D("0.005"), fee_rate=D("0.0006"),
                 slippage_bps=D("2")):
        owner=_paper_math()
        values=tuple(_policy_decimal(value) for value in (notional,threshold,stop_pct,fee_rate,slippage_bps))
        amount,threshold_value,stop_value,rate,bps=values
        owner.paper_position_size(amount,D(1));owner.paper_entry_side(D(1),D(1),threshold_value)
        owner.paper_stop_price(D(1),'short',stop_value);owner.paper_entry_fee(amount,rate)
        owner.adverse_execution_price(D(1),'long',bps,True)
        self.notional,self.threshold,self.stop_pct,self.fee_rate,self.slippage_bps=values
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
        if type(minute.complete) is not bool:raise ValueError('literal minute completeness required')
        if not minute.complete:
            self.reference.pop(symbol, None)
            return
        start = self._minute_start(minute.start)
        if start != minute.start.astimezone(timezone.utc):
            raise ValueError("minute start not aligned")
        if not isinstance(minute.poc,Decimal):raise ValueError('Decimal POC required')
        poc=_paper_math().adverse_execution_price(minute.poc,'long',D(0),True)
        previous = self.reference.get(symbol)
        if previous is not None and start < previous[0]:
            raise ValueError("out-of-order closed minute")
        self.reference[symbol] = (start, poc)

    def on_math_closed_minute(self, symbol, start, request, *, compute=None):
        """Consume the installed canonical Math SDK, never a local POC copy.

        Caller-supplied snapshot digest is UNATTESTED by the SDK. This method
        is offline/paper-only and does not qualify public MarketData market feeds.
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
        if not self.enabled:return None
        if not isinstance(trade.symbol,str) or not trade.symbol:raise ValueError('invalid symbol')
        timestamp=self._minute_start(trade.time)
        if not isinstance(trade.price,Decimal):raise ValueError('Decimal execution price required')
        owner=_paper_math();price=owner.adverse_execution_price(trade.price,'long',D(0),True)
        symbol=trade.symbol;prior=self.last_trade_time.get(symbol)
        if prior is not None and trade.time<prior:raise ValueError('out-of-order paper execution')
        position=self.positions.get(symbol)
        if position is not None:
            if position.side=='long':
                triggered='stop' if price<=position.stop else 'target' if price>=position.target else ''
                raw=min(price,position.stop) if triggered=='stop' else position.target
            else:
                triggered='stop' if price>=position.stop else 'target' if price<=position.target else ''
                raw=max(price,position.stop) if triggered=='stop' else position.target
            if not triggered:
                self.last_trade_time[symbol]=trade.time;return None
            exit_price=owner.adverse_execution_price(raw,position.side,self.slippage_bps,False)
            gross,fees,net=owner.paper_fill_metrics(position.side,position.entry,exit_price,position.size,position.entry_fee,self.fee_rate)
            fill=PaperFill(symbol,position.side,position.entry,exit_price,triggered,gross,fees,net,trade.time)
            self.last_trade_time[symbol]=trade.time;self.fills.append(fill);del self.positions[symbol]
            return fill
        reference=self.reference.get(symbol)
        if not reference or timestamp!=reference[0]+timedelta(minutes=1):
            self.last_trade_time[symbol]=trade.time;return None
        poc=reference[1];side=owner.paper_entry_side(price,poc,self.threshold)
        if side is None:
            self.last_trade_time[symbol]=trade.time;return None
        entry=owner.adverse_execution_price(price,side,self.slippage_bps,True)
        stop=owner.paper_stop_price(entry,side,self.stop_pct)
        if stop<=0:raise ValueError('positive paper stop required')
        if entry==poc:
            self.last_trade_time[symbol]=trade.time;return None
        size=owner.paper_position_size(self.notional,entry);fee=owner.paper_entry_fee(self.notional,self.fee_rate)
        candidate=Position(symbol,side,entry,poc,stop,size,trade.time,fee)
        self.last_trade_time[symbol]=trade.time;self.positions[symbol]=candidate;self.reference.pop(symbol,None)
        return None


# One application registry instance, using the ONLY implementation owned by
# terminan.contracts. Registration is inert: no workers, collectors or orders.
STRATEGIES = StrategyRegistry()
STRATEGIES.register(StrategyDefinition(
    id="poc_next_minute",
    version="2",
    requirements=(
        DataRequirement("public_trades"),
        DataRequirement("candles", ("1m",), required=False),
    ),
    implementation=PaperEngine,
))


STRATEGIES.register(StrategyDefinition(id='ohlc_signal',version='1',requirements=(DataRequirement('candles'),),implementation=PaperEngine,feature_versions=('conservative_ohlc_v1','math_paper28_v1')))

REPLAY_SCHEMA = "terminan.paper.replay.v2"
REPLAY_RESULT = "terminan.paper.result.v2"
_MAX_EVENTS = 1024
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_SYMBOL = re.compile(r"[A-Z0-9]{2,30}")
_RUN_ID = re.compile(r"[A-Za-z0-9_.:-]{1,64}")


def _timestamp(value):
    if type(value) is not int or not 0 <= value <= 4102444800000:
        raise ValueError("invalid UTC millisecond timestamp")
    return _EPOCH + timedelta(milliseconds=value)


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
    The request's source SHA is caller-supplied, NOT authenticated MarketData data.
    Set TERMINAN_PAPER_LEDGER to a dedicated local SQLite file to retain
    completed receipts. Without it, replay stays stateless. A configured
    ledger must successfully record the receipt before replay returns it.
    An exact retry reads the committed receipt even if the strategy is now
    disabled. The registry still controls admission of all new runs.
    """
    expected = {"schema", "run_id", "source", "parameters", "events"}
    if (type(request) is not dict or
            set(request) not in (expected, expected | {"strategy"},
                                 expected | {"comparison"},
                                 expected | {"strategy", "comparison"}) or
            request["schema"] != REPLAY_SCHEMA or
            type(request["run_id"]) is not str or
            not _RUN_ID.fullmatch(request["run_id"])):
        raise ValueError("invalid paper replay contract")
    request_bytes = canonical_json(request)
    if len(request_bytes) > 262144:
        raise ValueError("paper replay body limit")
    request=json.loads(request_bytes)  # Detach caller-owned mutable DTOs before hashing/execution.
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

    # MarketData historical variant/fold metadata is a *caller assertion*, not a
    # qualified MarketData dataset or proof that a non-POC strategy was executed.
    # Only the actual registered POC BASE algorithm is currently supported.
    comparison = request.get("comparison")
    if "comparison" in request and comparison is None:
        raise ValueError("missing MarketData comparison context")
    if comparison is not None:
        if (type(comparison) is not dict or set(comparison) != {
                "schema", "dataset_id", "dataset_hash", "strategy_name",
                "setup", "variant", "fold", "comparison_group", "symbol"
        } or comparison["schema"] != "terminan.market_data.comparison.v1"
                or type(comparison["dataset_id"]) is not str
                or not _RUN_ID.fullmatch(comparison["dataset_id"])
                or type(comparison["dataset_hash"]) is not str
                or not re.fullmatch("[0-9a-f]{64}", comparison["dataset_hash"])
                or comparison["strategy_name"] != "poc_next_minute"
                or comparison["setup"] != "POC"
                or comparison["variant"] != "BASE"
                or type(comparison["fold"]) is not int
                or not 0 <= comparison["fold"] <= 1000
                or type(comparison["symbol"]) is not str
                or not _SYMBOL.fullmatch(comparison["symbol"])
                or comparison["comparison_group"] != (
                    request["run_id"] + ":" + comparison["symbol"] + ":POC")
                or any(type(item) is not dict or
                       item.get("symbol") != comparison["symbol"]
                       for item in events)):
            raise ValueError("unqualified MarketData comparison context")
    request_sha256 = sha256(request_bytes).hexdigest()
    ledger_path = os.environ.get("TERMINAN_PAPER_LEDGER")
    if ledger_path:
        existing=PaperReplayLedger.lookup_existing(ledger_path,request['run_id'],request_sha256)
        if existing is not None:
            if existing.get('schema')!=REPLAY_RESULT or existing.get('strategy',{}).get('id')!='poc_next_minute' or existing['strategy'].get('version')!='2':raise RuntimeError('cached paper identity mismatch')
            return existing
    definition=next(item for item in STRATEGIES.discover() if item.id=='poc_next_minute')
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
    engine = PaperEngine(**params)
    engine.enabled = True  # Only offline simulated fills; no live order route.
    previous_ms = -1
    for event in events:
        if type(event) is not dict or "kind" not in event:
            raise ValueError("invalid paper replay event")
        kind = event["kind"]
        stamp = event.get("event_ms")
        timestamp = _timestamp(stamp)
        if stamp>source["as_of_ms"]:raise ValueError("event follows source as_of")
        if stamp < previous_ms:
            raise ValueError("out-of-order replay events")
        previous_ms = stamp
        symbol = event.get("symbol")
        if type(symbol) is not str or not _SYMBOL.fullmatch(symbol):
            raise ValueError("invalid paper replay symbol")
        if kind == "closed_minute":
            if set(event) != {"kind", "event_ms", "symbol", "profile", "close"}:
                raise ValueError("invalid closed-minute event")
            if stamp<60000 or stamp % 60000:
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
        "request_sha256": request_sha256,
        "events_processed": len(events),
        "fills": [_serialize(asdict(fill)) for fill in engine.fills],
        "open_positions": {
            symbol: _serialize(asdict(position))
            for symbol, position in sorted(engine.positions.items())
        },
    }
    if comparison is not None:
        result["comparison"] = {
            **comparison,
            "status": "CALLER_SUPPLIED_UNATTESTED",
            "dataset_qualified": False,
            "strategy_executed": "poc_next_minute",
            "history_requirements": [
                {"dataset": requirement.dataset,
                 "timeframes": list(requirement.timeframes),
                 "required": requirement.required,
                 "coverage_verified": False}
                for requirement in definition.requirements
            ],
        }
        result["receipt_checkpoint"] = {
            "state": "COMPLETE_RESULT_ONLY",
            "resumable": False,
            "events_processed": len(events),
            "request_sha256": request_sha256,
        }
    result["result_sha256"] = sha256(canonical_json(result)).hexdigest()
    if ledger_path:
        return PaperReplayLedger(ledger_path).record(result)
    return result


# Execution/sizing state policy stays in Terminan; all arithmetic is Math-owned.
def apply_sizing(trades,mode='FIXED',base_size=1.0,multiplier=2.0,max_steps=3,max_size=4.0):
    if mode not in ('FIXED','MARTINGALE','ANTI_MARTINGALE'):raise ValueError('unknown sizing mode')
    if type(max_steps) is not int or not 0<=max_steps<=1_000_000:raise ValueError('invalid sizing step limit')
    owner=_paper_math();out=[];step=0
    for row in trades:
        candidate=dict(row)
        size=owner.paper_scale_value(base_size,1.0) if mode=='FIXED' else owner.paper_size_multiplier(base_size,multiplier,step,max_size)
        candidate['sizing_mode']=mode;candidate['size_multiplier']=size
        for field in ('pnl','fees','slippage','mfe','mae'):
            if field in candidate and candidate[field] is not None:candidate[field]=owner.paper_scale_value(candidate[field],size)
        net=owner.paper_net_pnl(candidate.get('pnl',0),candidate.get('fees',0),candidate.get('slippage',0))
        out.append(candidate)
        if mode=='MARTINGALE':step=min(max_steps,step+1) if net<0 else 0
        elif mode=='ANTI_MARTINGALE':step=min(max_steps,step+1) if net>0 else 0
    return out


def ruin_stats(trades,starting_equity=100.0,ruin_fraction=.5):
    owner=_paper_math();equity=peak=owner.paper_scale_value(starting_equity,1.0)
    minimum=equity;drawdown=0.0;ruined=False
    threshold=owner.paper_scale_value(equity,ruin_fraction)
    for row in trades:
        net=owner.paper_net_pnl(row.get('pnl',0),row.get('fees',0),row.get('slippage',0))
        equity,peak,minimum,drawdown=owner.paper_equity_update(equity,peak,minimum,drawdown,net)
        if equity<=threshold:ruined=True
    return dict(ending_equity=equity,min_equity=minimum,max_drawdown=drawdown,ruin_threshold=threshold,ruined=ruined)

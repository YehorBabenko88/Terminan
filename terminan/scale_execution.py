"""Bounded scaled-limit contracts; execution stays in the sole PaperEngine."""
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING
import re
from .research_signals import ResearchBar, ResearchSignal, validate_signal_batch

if TYPE_CHECKING:
    from .paper import PaperFill

SCALE_EXECUTION_MODEL = 'OHLC_SCALE_SL_FIRST_ONE_TARGET_PER_BAR_NO_TICK_ORDER_V1'

@dataclass(frozen=True)
class ScaleEntryLeg:
    price: Decimal
    fraction: Decimal

@dataclass(frozen=True)
class ScaleExitTarget:
    price: Decimal
    fraction: Decimal

@dataclass(frozen=True)
class ScaleExecutionPlan:
    symbol: str
    decision_ms: int
    side: str
    entries: tuple[ScaleEntryLeg, ...]
    stop: Decimal
    targets: tuple[ScaleExitTarget, ...]
    move_stop_to_entry_after_first_target: bool = False

@dataclass(frozen=True)
class ScaleEntryFill:
    leg_index: int
    time_ms: int
    price: Decimal
    quantity: Decimal
    fraction: Decimal

@dataclass(frozen=True)
class ScaleExitFill:
    time_ms: int
    price: Decimal
    quantity: Decimal
    reason: str

@dataclass(frozen=True)
class ScaleExecution:
    symbol: str
    entry_ms: int
    exit_ms: int
    quantity: Decimal
    entries: tuple[ScaleEntryFill, ...]
    exits: tuple[ScaleExitFill, ...]
    fill: 'PaperFill'
    unfilled_entry_indices: tuple[int, ...]
    model: str = field(default=SCALE_EXECUTION_MODEL, init=False)
    accounting_model: str = field(default='PAPER_SCALE_ACCOUNTING_V1', init=False)
    entry_basis_policy: str = field(default='WEIGHTED_EXECUTION_BASIS_PRESERVED_ON_PARTIAL_EXIT', init=False)
    tick_ordering: str = field(default='UNKNOWN', init=False)
    execution_authority: bool = field(default=False, init=False)
    trading_authorized: bool = field(default=False, init=False)

def _decimal_literal(value):
    # Resource/type codec only; financial admission and arithmetic belong to Math.
    if type(value) is not Decimal or not value.is_finite():
        raise ValueError('SCALE_PLAIN_FINITE_DECIMAL_REQUIRED')
    parts = value.as_tuple()
    if len(parts.digits) > 128 or abs(parts.exponent) > 4096:
        raise ValueError('SCALE_DECIMAL_RESOURCE_BUDGET')
    return value

def validate_scale_batch(plan, bars, *, bar_ms, as_of_ms, available_from_ms=0):
    """Detach the full literal plan/bars before any canonical Math callback."""
    if type(plan) is not ScaleExecutionPlan:
        raise ValueError('SCALE_TYPED_PLAN_REQUIRED')
    if (type(plan.symbol) is not str or re.fullmatch('[A-Z0-9]{2,30}', plan.symbol) is None
            or type(plan.side) is not str or plan.side not in ('long', 'short')
            or type(plan.move_stop_to_entry_after_first_target) is not bool):
        raise ValueError('SCALE_LITERAL_PLAN_POLICY_REQUIRED')
    if (type(bar_ms) is not int or not 1 <= bar_ms <= 2678400000
            or type(as_of_ms) is not int or not 0 <= as_of_ms <= 4102444800000
            or type(available_from_ms) is not int or not 0 <= available_from_ms <= as_of_ms
            or type(plan.decision_ms) is not int
            or not available_from_ms <= plan.decision_ms <= as_of_ms):
        raise ValueError('SCALE_LITERAL_CLOCK_REQUIRED')
    groups = []
    for source, cls in ((plan.entries, ScaleEntryLeg), (plan.targets, ScaleExitTarget)):
        if (type(source) is not tuple and type(source) is not list) or not 1 <= len(source) <= 16:
            raise ValueError('SCALE_BOUNDED_LEGS_REQUIRED')
        captured = tuple(source)
        if any(type(leg) is not cls for leg in captured):
            raise ValueError('SCALE_EXACT_LEG_TYPE_REQUIRED')
        groups.append(tuple(cls(_decimal_literal(leg.price), _decimal_literal(leg.fraction))
                            for leg in captured))
    entries, targets = groups
    detached = ScaleExecutionPlan(plan.symbol, plan.decision_ms, plan.side, entries,
                                  _decimal_literal(plan.stop), targets,
                                  plan.move_stop_to_entry_after_first_target)
    if (type(bars) is not tuple and type(bars) is not list) or not 1 <= len(bars) <= 4096:
        raise ValueError('SCALE_BOUNDED_BARS_REQUIRED')
    captured_bars = tuple(bars)
    if any(type(bar) is not ResearchBar for bar in captured_bars):
        raise ValueError('SCALE_EXACT_BAR_TYPE_REQUIRED')
    rows = []
    previous = None
    for bar in captured_bars:
        if (type(bar.start_ms) is not int or bar.start_ms < available_from_ms
                or bar.start_ms % bar_ms or bar.start_ms + bar_ms > as_of_ms
                or previous is not None and bar.start_ms != previous + bar_ms):
            raise ValueError('SCALE_CONTIGUOUS_CLOSED_BAR_CLOCKS_REQUIRED')
        rows.append(ResearchBar(bar.start_ms, *(_decimal_literal(value) for value in
                    (bar.open, bar.high, bar.low, bar.close, bar.volume))))
        previous = bar.start_ms
    rows = tuple(rows)
    import market_math as owner
    for name in ('paper_scale_fractions_valid', 'paper_scale_entry_metrics',
                 'paper_scale_target_quantity', 'paper_scale_accounting'):
        if not callable(getattr(owner, name, None)):
            raise RuntimeError('SCALE_CANONICAL_MATH_API_REQUIRED')
    if owner.paper_scale_fractions_valid(tuple(leg.fraction for leg in entries)) is not True:
        raise ValueError('SCALE_ENTRY_FRACTIONS_REFUSED')
    if owner.paper_scale_fractions_valid(tuple(target.fraction for target in targets)) is not True:
        raise ValueError('SCALE_TARGET_FRACTIONS_REFUSED')
    # Reuse the existing ordinary-signal OHLC/clock/financial admission path.
    probe = ResearchSignal(detached.symbol, detached.decision_ms, detached.side,
                           'limit', entries[0].price, detached.stop, targets[0].price)
    validate_signal_batch(probe, rows, bar_ms=bar_ms, as_of_ms=as_of_ms,
                          available_from_ms=available_from_ms, ambiguity_policy='SL_FIRST')
    for leg in entries:
        owner.adverse_execution_price(leg.price, detached.side, Decimal(0), True)
        if not (detached.stop < leg.price < targets[0].price if detached.side == 'long'
                else detached.stop > leg.price > targets[0].price):
            raise ValueError('SCALE_ORDERED_ENTRY_BOUNDS_REQUIRED')
    previous = None
    for target in targets:
        owner.adverse_execution_price(target.price, detached.side, Decimal(0), False)
        if previous is not None and not (target.price > previous if detached.side == 'long'
                                         else target.price < previous):
            raise ValueError('SCALE_ORDERED_TARGETS_REQUIRED')
        previous = target.price
    return detached, rows

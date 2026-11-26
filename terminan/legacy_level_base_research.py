"""Retrospective-only, causal-clocked historical level geometry.

The original Strattester level simulator triggers intrabar using *future*
high/low observations relative to a proposed bar-open decision. A closed bar
cannot authorize an earlier entry. This projector therefore returns an
immutable non-executable, explicitly post-close observation, NEVER a
ResearchSignal. Its only qualified geometric subset has entry at the exact
opening threshold and no stop/target hit in that first bar. All pricing math
belongs to the existing canonical market_math. A *test* may separately
construct a retrospective hypothetical signal to compare existing PaperEngine,
but production must never do so using this observation as authority.
"""
from dataclasses import dataclass, field
from decimal import Decimal
import re

from .research_signals import ResearchBar


@dataclass(frozen=True, slots=True)
class LegacyLevelBaseObservation:
    variant: str
    level_price: Decimal
    level_known_at_ms: int
    entry_bar_start_ms: int
    observed_at_ms: int
    side: str
    entry_price: Decimal
    stop: Decimal
    target: Decimal
    equivalence_scope: str = field(
        default='RETROSPECTIVE_EXACT_OPEN_NO_ENTRY_BAR_EXIT_V2',init=False)
    availability_basis: str = field(
        default='FULL_ENTRY_BAR_CLOSE_DECLARED_NOT_AUTHENTICATED',init=False)
    source_authentication: str = field(default='NOT_EVALUATED',init=False)
    execution_authority: bool = field(default=False,init=False)
    trading_authorized: bool = field(default=False,init=False)


def propose_legacy_level_base(symbol, variant, level_price, level_known_at_ms,
                              first_bar, *, bar_ms, as_of_ms):
    """Return only post-close original price geometry, never executable entry.

    The source interval's high/low and close are future information at bar
    open. An offline historical result becomes observable no earlier than the
    fully CLOSED source bar. This API does not return ResearchSignal or a
    pre-open entry decision, preventing its accidental use as an execution
    instruction by the existing single PaperEngine.
    """
    import market_math as owner
    if type(symbol) is not str or re.fullmatch('[A-Z0-9]{2,30}',symbol) is None:
        raise ValueError('LEGACY_LEVEL_LITERAL_SYMBOL_REQUIRED')
    if type(variant) is not str or variant not in ('LOW_BASE','HIGH_BASE'):
        raise ValueError('LEGACY_LEVEL_UNQUALIFIED_VARIANT')
    if (type(level_known_at_ms) is not int or type(bar_ms) is not int
            or type(as_of_ms) is not int
            or not 0<=level_known_at_ms<=2**53-1
            or not 1<=bar_ms<=2678400000
            or not 0<=as_of_ms<=2**53-1):
        raise ValueError('LEGACY_LEVEL_DECLARED_CLOCK_REQUIRED')
    if type(first_bar) is not ResearchBar:
        raise ValueError('LEGACY_LEVEL_EXACT_CLOSED_BAR_REQUIRED')
    if (type(first_bar.start_ms) is not int
            or first_bar.start_ms!=level_known_at_ms+bar_ms
            or first_bar.start_ms%bar_ms!=0
            or first_bar.start_ms+bar_ms>as_of_ms):
        raise ValueError('LEGACY_LEVEL_EXACT_NEXT_BAR_REQUIRED')
    observed=first_bar.start_ms+bar_ms
    prices=(level_price,first_bar.open,first_bar.high,first_bar.low,
            first_bar.close,first_bar.volume)
    if any(type(value) is not Decimal for value in prices):
        raise ValueError('LEGACY_LEVEL_EXACT_DECIMAL_REQUIRED')
    if (owner.candle_ohlcv_valid(first_bar.open,first_bar.high,
                                 first_bar.low,first_bar.close,
                                 first_bar.volume) is not True
            or owner.candle_ohlcv_valid(level_price,level_price,
                                        level_price,level_price,
                                        Decimal(0)) is not True):
        raise ValueError('LEGACY_LEVEL_CANONICAL_PRICE_DOMAIN')
    side='long' if variant=='HIGH_BASE' else 'short'
    trigger=owner.paper_stop_price(level_price,side,Decimal('0.005'))
    if type(trigger) is not Decimal or first_bar.open!=trigger:
        raise ValueError('LEGACY_LEVEL_TRIGGER_MUST_EQUAL_OPEN')
    stop=owner.paper_stop_price(trigger,side,Decimal('0.010'))
    other='short' if side=='long' else 'long'
    target=owner.paper_stop_price(trigger,other,Decimal('0.015'))
    if (type(stop) is not Decimal or type(target) is not Decimal
            or not (stop<trigger<target if side=='long'
                    else stop>trigger>target)):
        raise ValueError('LEGACY_LEVEL_CANONICAL_BRACKET_REQUIRED')
    if side=='long':
        if first_bar.open>level_price:
            raise ValueError('LEGACY_LEVEL_BROKEN_AT_OPEN')
        safe=first_bar.low>stop and first_bar.high<target
    else:
        if first_bar.open<level_price:
            raise ValueError('LEGACY_LEVEL_BROKEN_AT_OPEN')
        safe=first_bar.high<stop and first_bar.low>target
    if not safe:
        raise ValueError('LEGACY_LEVEL_ENTRY_BAR_EXIT_UNRESOLVED')
    return LegacyLevelBaseObservation(
        variant,level_price,level_known_at_ms,first_bar.start_ms,
        observed,side,trigger,stop,target)

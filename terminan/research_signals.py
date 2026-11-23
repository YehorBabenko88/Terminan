"""Typed offline signal/bar contracts; no simulator or numerical kernel."""
from dataclasses import dataclass
from decimal import Decimal
import re
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .paper import PaperFill

@dataclass(frozen=True)
class ResearchSignal:
    symbol:str
    decision_ms:int
    side:str
    entry_kind:str
    entry_price:Decimal|None
    stop:Decimal
    target:Decimal

@dataclass(frozen=True)
class ResearchBar:
    start_ms:int
    open:Decimal
    high:Decimal
    low:Decimal
    close:Decimal
    volume:Decimal=Decimal(0)

@dataclass(frozen=True)
class SignalExecution:
    entry_ms:int
    exit_ms:int
    quantity:Decimal
    fill:'PaperFill'
    model:str
    tick_ordering:str='UNKNOWN'

def validate_signal_batch(signal,bars,*,bar_ms,as_of_ms,ambiguity_policy,available_from_ms=0):
    import market_math as owner
    if type(signal) is not ResearchSignal or type(signal.symbol) is not str or re.fullmatch('[A-Z0-9]{2,30}',signal.symbol) is None:raise ValueError('typed signal instrument required')
    if (type(bar_ms) is not int or not 1<=bar_ms<=2678400000 or type(as_of_ms) is not int or not 0<=as_of_ms<=4102444800000
            or type(available_from_ms) is not int or not 0<=available_from_ms<=as_of_ms
            or type(signal.decision_ms) is not int or not available_from_ms<=signal.decision_ms<=as_of_ms):raise ValueError('bounded closed signal clock required')
    if type(signal.side) is not str or type(signal.entry_kind) is not str or type(ambiguity_policy) is not str or signal.side not in ('long','short') or signal.entry_kind not in ('market','limit') or ambiguity_policy not in ('SL_FIRST','TP_FIRST'):raise ValueError('explicit signal execution policy required')
    for price in (signal.stop,signal.target):owner.adverse_execution_price(price,'long',Decimal(0),True)
    if signal.entry_kind=='market':
        if signal.entry_price is not None:raise ValueError('market entry has no limit price')
        if not (signal.stop<signal.target if signal.side=='long' else signal.stop>signal.target):raise ValueError('ordered signal bounds required')
    else:
        owner.adverse_execution_price(signal.entry_price,'long',Decimal(0),True)
        if not (signal.stop<signal.entry_price<signal.target if signal.side=='long' else signal.stop>signal.entry_price>signal.target):raise ValueError('ordered limit signal bounds required')
    if (type(bars) is not tuple and type(bars) is not list) or not 1<=len(bars)<=20000:raise ValueError('bounded closed OHLC bars required')
    rows=tuple(bars);previous=None
    for bar in rows:
        if type(bar) is not ResearchBar or type(bar.start_ms) is not int or bar.start_ms<available_from_ms or bar.start_ms%bar_ms or bar.start_ms+bar_ms>as_of_ms:raise ValueError('unaligned or future OHLC bar')
        if previous is not None and bar.start_ms!=previous+bar_ms:raise ValueError('continuous strictly ordered OHLC bars required')
        if owner.candle_ohlcv_valid(bar.open,bar.high,bar.low,bar.close,bar.volume) is not True:raise ValueError('invalid OHLCV domain')
        previous=bar.start_ms
    return rows

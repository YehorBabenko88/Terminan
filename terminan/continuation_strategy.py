"""Explicit-availability offline continuation strategy; no data store or executor.

Numerical geometry belongs to Math. Returned rich ResearchEntry records feed the
existing PaperEngine only after its separate simulation admission checks.
"""
from dataclasses import dataclass,fields
import re
from .entry_context import build_entry_context
from .research_signals import ResearchSignal
from .volatility import VolatilityMetrics
_MAX_CLOCK=4102444800000
@dataclass(frozen=True,slots=True)
class CandleBodyObservation:
    event_start_ms:int
    event_end_ms:int
    available_at_ms:int
    open:int|float
    close:int|float

def _clock(value):
    if type(value) is not int or not 0<=value<=_MAX_CLOCK:
        raise ValueError('CONTINUATION_EXPLICIT_CLOCK_REQUIRED')
    return value

def generate_continuation_entries(symbol,bodies,volatility,*,as_of_ms,
                                  min_volume_ratio=1.35,min_percentile=.60,min_body_atr=.50):
    """Generate rich v2 research entries from detached caller-declared data.

    Availability and end clocks are mandatory; no duration or source clock is
    reconstructed. Only volatility for the same event start may contribute.
    Missing/future observations emit nothing; conflicting identities refuse.
    This function neither authenticates data nor authorizes trading.
    """
    import market_math as owner
    from .strategy_entries import ResearchEntry,ResearchEntryPattern,EntrySide,EntryEvidence,RiskBasis,_freeze
    from .market_structure import MarketStructureReference
    if type(symbol) is not str or re.fullmatch('[A-Z0-9]{2,30}',symbol) is None:
        raise ValueError('CONTINUATION_INSTRUMENT_REQUIRED')
    cutoff=_clock(as_of_ms)
    if ((type(bodies) is not tuple and type(bodies) is not list) or len(bodies)>512
            or (type(volatility) is not tuple and type(volatility) is not list) or len(volatility)>512):
        raise ValueError('CONTINUATION_BOUNDED_LITERAL_BATCH_REQUIRED')
    # Detach ALL records before the first numeric/projector call. Tuple copies
    # alone retain caller DTOs, allowing a callback to change a later read.
    def snapshot(values,kind):
        out=[]
        for value in tuple(values):
            if type(value) is not kind:
                raise ValueError('CONTINUATION_LITERAL_RECORD_REQUIRED')
            leaves=tuple((f.name,getattr(value,f.name)) for f in fields(kind))
            clone=object.__new__(kind)
            for name,item in leaves:object.__setattr__(clone,name,item)
            out.append(clone)
        return tuple(out)
    rows=snapshot(bodies,CandleBodyObservation);vols=snapshot(volatility,VolatilityMetrics)
    for value in (min_volume_ratio,min_percentile,min_body_atr):
        if not owner.lossless_nonnegative_binary64_valid(value):
            raise ValueError('CONTINUATION_NUMERIC_POLICY_REQUIRED')
    if min_percentile>1:raise ValueError('CONTINUATION_PERCENTILE_POLICY_REQUIRED')
    # Public projector preflights every row, including future values, and
    # refuses conflicting identities before the first output can be built.
    build_entry_context(decision_ms=cutoff,metadata={},volatility=vols)
    projected=tuple(build_entry_context(decision_ms=cutoff,metadata={},volatility=(v,))['volatility'] for v in vols)
    previous=None
    for row in rows:
        if type(row) is not CandleBodyObservation:
            raise ValueError('CONTINUATION_LITERAL_BODY_REQUIRED')
        start=_clock(row.event_start_ms);end=_clock(row.event_end_ms);available=_clock(row.available_at_ms)
        if not start<end<=available or (previous is not None and start<=previous):
            raise ValueError('CONTINUATION_ORDERED_DECLARED_BODY_REQUIRED')
        owner.research_expansion_side(row.open,row.close,0,min_body_atr=min_body_atr)
        previous=start
    out=[]
    for row in rows:
        if row.available_at_ms>cutoff:continue
        matching=tuple(v for v in projected if v is not None and v['event_start_ms']==row.event_start_ms)
        if not matching:continue
        # Replay declared versions chronologically. Only the latest version at
        # body availability is visible initially; later updates cannot erase a
        # signal already emitted at an earlier decision clock.
        decisions=sorted({max(row.available_at_ms,v['available_at_ms']) for v in matching})
        for decision in decisions:
            eligible=tuple(v for v in matching if v['available_at_ms']<=decision)
            v=max(eligible,key=lambda value:value['available_at_ms'])
            if v['atr_percentile']<min_percentile or v['volume_ratio']<min_volume_ratio:continue
            side=owner.research_expansion_side(row.open,row.close,v['atr_fraction'],min_body_atr=min_body_atr)
            if side is None:continue
            bracket=owner.research_bracket_prices(row.close,v['atr_fraction'],side)
            if type(bracket) is not owner.ResearchBracketPrices:raise ValueError('CONTINUATION_MATH_BRACKET_RECORD_REQUIRED')
            stop,target=bracket.as_decimal()
            selected=next(value for value in vols if value.event_start_ms==v['event_start_ms'] and value.available_at_ms==v['available_at_ms'])
            context=build_entry_context(decision_ms=decision,metadata={'pattern':ResearchEntryPattern.CONTINUATION.value},volatility=(selected,))
            evidence=EntryEvidence(row.close,(MarketStructureReference(row.event_start_ms,row.event_end_ms,row.available_at_ms),),None,None,
                selected.volume_ratio,selected.regime,None,None,None,selected.atr_fraction,RiskBasis.OBSERVED_ATR,
                body_reference=row,volatility=selected,atr_percentile=selected.atr_percentile)
            signal=ResearchSignal(symbol,decision,side,'market',None,stop,target)
            out.append(ResearchEntry(ResearchEntryPattern.CONTINUATION,decision,EntrySide(side),row.close,signal,evidence,_freeze(context)))
            break
    return tuple(sorted(out,key=lambda entry:entry.decision_ms))

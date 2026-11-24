"""Pure declared research-entry generators; no feed, registry or executor.

All inputs are detached before numeric owners run. Math owns price geometry;
Term owns causal selection. Missing flow stays absent and default risk is policy.
"""
from dataclasses import dataclass,field,fields
from enum import Enum
from types import MappingProxyType
import re
from .market_structure import (OHLCObservation,MarketStructureEvent,MarketStructureReference,
    MarketStructureKind,MarketStructureContext,MarketTimeframe,_clock,_timeframe,_snapshot,_finance_prices,_DURATIONS)
from .entry_context import ProfileSummary,ProfileKind,build_entry_context
from .volatility import VolatilityMetrics,VolatilityRegime
from .research_signals import ResearchSignal
from .continuation_strategy import CandleBodyObservation

class ResearchEntryPattern(str,Enum):
    SWEEP_RECLAIM='sweep_reclaim_v2'
    BREAKOUT_RETEST='breakout_retest_v2'
    PROFILE_RECLAIM='profile_reclaim_v2'
    CONTINUATION='volatility_continuation_v2'
class EntrySide(str,Enum):
    LONG='long';SHORT='short'
class RiskBasis(str,Enum):
    OBSERVED_ATR='CALLER_DECLARED_VOLATILITY_ATR'
    POLICY_DEFAULT='POLICY_DEFAULT_0_002_NOT_OBSERVED_VOLATILITY'
@dataclass(frozen=True,slots=True)
class SignedFlowObservation:
    event_start_ms:int
    available_at_ms:int
    delta:int|float
    availability_basis:str=field(default='CALLER_DECLARED',init=False)
    source_authentication:str=field(default='NOT_EVALUATED',init=False)
    execution_authority:bool=field(default=False,init=False)
    trading_authorized:bool=field(default=False,init=False)
@dataclass(frozen=True,slots=True)
class EntryEvidence:
    entry_price:int|float
    candle_references:tuple[MarketStructureReference,...]
    sweep_reference:MarketStructureReference|None
    break_reference:MarketStructureReference|None
    volume_ratio:int|float|None
    volatility_regime:VolatilityRegime|None
    profile_kind:ProfileKind|None
    profile_available_at_ms:int|None
    flow:SignedFlowObservation|None
    risk_atr_fraction:int|float
    risk_basis:RiskBasis
    body_reference:CandleBodyObservation|None=None
    volatility:VolatilityMetrics|None=None
    atr_percentile:int|float|None=None
    source_authentication:str=field(default='NOT_EVALUATED',init=False)
    execution_authority:bool=field(default=False,init=False)
    trading_authorized:bool=field(default=False,init=False)
@dataclass(frozen=True,slots=True)
class ResearchEntry:
    pattern:ResearchEntryPattern
    decision_ms:int
    side:EntrySide
    reference:int|float
    signal:ResearchSignal
    evidence:EntryEvidence
    context:MappingProxyType
    version:str=field(default='strategy_entries.v2',init=False)
    source_authentication:str=field(default='NOT_EVALUATED',init=False)
    execution_authority:bool=field(default=False,init=False)
    trading_authorized:bool=field(default=False,init=False)
    @property
    def metadata(self):
        evidence=self.evidence
        return MappingProxyType(dict(level=None if self.pattern is ResearchEntryPattern.PROFILE_RECLAIM else self.reference,
            sweep_event_start_ms=None if evidence.sweep_reference is None else evidence.sweep_reference.event_start_ms,
            break_available_at_ms=None if evidence.break_reference is None else evidence.break_reference.available_at_ms,
            volume_ratio=evidence.volume_ratio,
            poc=self.reference if self.pattern is ResearchEntryPattern.PROFILE_RECLAIM else None,
            profile_kind=None if evidence.profile_kind is None else evidence.profile_kind.value,
            delta=None if evidence.flow is None else evidence.flow.delta,
            volatility_regime=None if evidence.volatility_regime is None else evidence.volatility_regime.value,
            risk_atr_fraction=evidence.risk_atr_fraction,risk_basis=evidence.risk_basis.value,
            atr_percentile=evidence.atr_percentile,
            body_available_at_ms=None if evidence.body_reference is None else evidence.body_reference.available_at_ms,
            volatility_available_at_ms=None if evidence.volatility is None else evidence.volatility.available_at_ms))
@dataclass(frozen=True,slots=True)
class _Batch:
    symbol:str
    timeframe:MarketTimeframe
    cutoff:int
    rows:tuple
    events:tuple
    volatility:tuple
    profiles:tuple
    flow:tuple

def _clone_record(record,kind):
    if type(record) is not kind:raise ValueError('STRATEGY_ENTRY_EXACT_LITERAL_RECORD_REQUIRED')
    snapshot=tuple((f.name,getattr(record,f.name)) for f in fields(kind))
    if kind is MarketStructureEvent:
        snapshot=tuple((name,_clone_record(value,MarketStructureReference) if value is not None and name in ('swing_reference','trigger_reference') else value) for name,value in snapshot)
    # A detached DTO copy only, never admission. All cloned summary fields and
    # metadata are subsequently validated by their canonical owner/projector.
    clone=object.__new__(kind)
    for name,value in snapshot:object.__setattr__(clone,name,value)
    return clone

def _clones(values,kind,limit):
    if (type(values) is not tuple and type(values) is not list) or len(values)>limit:raise ValueError('STRATEGY_ENTRY_BOUNDED_LITERAL_BATCH_REQUIRED')
    return tuple(_clone_record(value,kind) for value in tuple(values))

def _validated_flow(values):
    import market_math as owner
    seen={};out=[]
    for value in values:
        start=value.event_start_ms;available=value.available_at_ms;delta=value.delta
        _clock(start);_clock(available)
        if available<start or owner.lossless_binary64_valid(delta) is not True:raise ValueError('STRATEGY_ENTRY_DECLARED_SIGNED_FLOW_REQUIRED')
        if type(value.availability_basis) is not str or value.availability_basis!='CALLER_DECLARED' or type(value.source_authentication) is not str or value.source_authentication!='NOT_EVALUATED' or value.execution_authority is not False or value.trading_authorized is not False:raise ValueError('STRATEGY_ENTRY_FLOW_NOT_AUTHORITY')
        identity=(available,start);signature=(type(delta),delta)
        if identity in seen:
            if seen[identity]!=signature:raise ValueError('STRATEGY_ENTRY_CONFLICTING_FLOW_IDENTITY')
            continue
        seen[identity]=signature;out.append(value)
    return tuple(out)

def _prepare(symbol,bars,events,volatility,profiles,flow,*,as_of_ms,timeframe):
    if type(symbol) is not str or re.fullmatch('[A-Z0-9]{2,30}',symbol) is None:raise ValueError('STRATEGY_ENTRY_LITERAL_SYMBOL_REQUIRED')
    cutoff=_clock(as_of_ms);timeframe=_timeframe(timeframe)
    # Every batch is copied before the FIRST Math/domain/projector call. A caller
    # mutating another original record during a numeric owner call cannot alter
    # these detached snapshots. Future records are never skipped in preflight.
    rows=_snapshot(bars,timeframe)
    event_copies=_clones(events,MarketStructureEvent,400000)
    vols=_clones(volatility,VolatilityMetrics,512)
    profs=_clones(profiles,ProfileSummary,512)
    flows=_clones(flow,SignedFlowObservation,512)
    checked=MarketStructureContext(event_copies).events
    if any(event.timeframe is not timeframe for event in checked):raise ValueError('STRATEGY_ENTRY_STRUCTURE_TIMEFRAME_MISMATCH')
    build_entry_context(decision_ms=cutoff,metadata={},volatility=vols,profiles=profs)
    _finance_prices(rows);flows=_validated_flow(flows)
    return _Batch(symbol,timeframe,cutoff,rows,checked,vols,profs,flows)

def _context(batch,decision,pattern):
    return build_entry_context(decision_ms=decision,metadata={'pattern':pattern.value},volatility=batch.volatility,profiles=batch.profiles)

def _freeze(value):
    if type(value) is dict:return MappingProxyType({key:_freeze(item) for key,item in value.items()})
    if type(value) in (tuple,list):return tuple(_freeze(item) for item in value)
    return value

def _ref(row):return MarketStructureReference(*row[:3])
def _event_ref(event):return MarketStructureReference(event.event_start_ms,event.event_end_ms,event.available_at_ms)
def _flow_at(batch,decision):
    visible=[row for row in batch.flow if row.available_at_ms<=decision]
    return max(visible,key=lambda row:(row.available_at_ms,row.event_start_ms)) if visible else None

def _entry(batch,row,decision,side,reference,pattern,context,*,event=None,prior=None,flow=None):
    import market_math as owner
    vol=context['volatility'];profile=context['profile']
    atr=.002 if vol is None else vol['atr_fraction']
    basis=RiskBasis.POLICY_DEFAULT if vol is None else RiskBasis.OBSERVED_ATR
    bracket=owner.research_bracket_prices(row[6],atr,side.value)
    if type(bracket) is not owner.ResearchBracketPrices:raise ValueError('STRATEGY_ENTRY_MATH_BRACKET_RECORD_REQUIRED')
    stop,target=bracket.as_decimal()
    signal=ResearchSignal(batch.symbol,decision,side.value,'market',None,stop,target)
    evidence=EntryEvidence(row[6],(_ref(row),) if prior is None else (_ref(prior),_ref(row)),
        _event_ref(event) if pattern is ResearchEntryPattern.SWEEP_RECLAIM else None,
        _event_ref(event) if pattern is ResearchEntryPattern.BREAKOUT_RETEST else None,
        None if vol is None else vol['volume_ratio'],None if vol is None else VolatilityRegime(vol['regime']),
        None if profile is None else ProfileKind(profile['kind']),None if profile is None else profile['available_at_ms'],
        flow,atr,basis,volatility=None if vol is None else next(value for value in batch.volatility
            if value.event_start_ms==vol['event_start_ms'] and value.available_at_ms==vol['available_at_ms']),
        atr_percentile=None if vol is None else vol['atr_percentile'])
    return ResearchEntry(pattern,decision,side,reference,signal,evidence,_freeze(context))

def _ordered(entries):
    return tuple(sorted(entries,key=lambda entry:(entry.decision_ms,entry.evidence.candle_references[-1].event_start_ms,entry.pattern.value,entry.side.value,entry.reference)))

def generate_sweep_reclaim_entries(symbol,bars,structure_events,volatility=(),*,as_of_ms,timeframe):
    """A sweep reclaim waits for both declared structure and its actual candle."""
    batch=_prepare(symbol,bars,structure_events,volatility,(),(),as_of_ms=as_of_ms,timeframe=timeframe)
    by_start={row[0]:row for row in batch.rows};out=[];pattern=ResearchEntryPattern.SWEEP_RECLAIM
    for event in batch.events:
        if event.kind not in (MarketStructureKind.BULLISH_LIQUIDITY_SWEEP,MarketStructureKind.BEARISH_LIQUIDITY_SWEEP):continue
        row=by_start.get(event.event_start_ms)
        if row is None:continue
        if row[1]!=event.event_end_ms:raise ValueError('STRATEGY_ENTRY_STRUCTURE_CANDLE_END_MISMATCH')
        decision=max(row[2],event.available_at_ms)
        if decision>batch.cutoff:continue
        side=EntrySide.LONG if event.kind is MarketStructureKind.BULLISH_LIQUIDITY_SWEEP else EntrySide.SHORT
        out.append(_entry(batch,row,decision,side,event.level,pattern,_context(batch,decision,pattern),event=event))
    return _ordered(out)

def generate_breakout_retest_entries(symbol,bars,structure_events,volatility=(),*,as_of_ms,timeframe,
                                      retest_tolerance=.0015,min_volume_ratio=1.20,max_wait_bars=20):
    """First actual decision matching post-break event time, Math touch and volume.

    Wait limits use the supplied/validated timeframe cadence as interval policy;
    no candle availability or end is synthesized from it. Delayed decision order
    need not follow event time, so an out-of-window row never ends the scan.
    """
    batch=_prepare(symbol,bars,structure_events,volatility,(),(),as_of_ms=as_of_ms,timeframe=timeframe)
    import market_math as owner
    if type(max_wait_bars) is not int or not 1<=max_wait_bars<=4096:raise ValueError('STRATEGY_ENTRY_BOUNDED_WAIT_POLICY_REQUIRED')
    for value in (retest_tolerance,min_volume_ratio):
        if owner.lossless_nonnegative_binary64_valid(value) is not True:raise ValueError('STRATEGY_ENTRY_LITERAL_NUMERIC_POLICY_REQUIRED')
    candidates=tuple(sorted(batch.rows,key=lambda row:(row[2],row[0])));out=[];pattern=ResearchEntryPattern.BREAKOUT_RETEST
    for event in batch.events:
        if event.kind not in (MarketStructureKind.BULLISH_BOS,MarketStructureKind.BEARISH_BOS):continue
        side=EntrySide.LONG if event.kind is MarketStructureKind.BULLISH_BOS else EntrySide.SHORT
        for row in candidates:
            decision=row[2]
            if decision>batch.cutoff or decision<=event.available_at_ms or row[0]<=event.event_start_ms or row[0]-event.event_start_ms>max_wait_bars*_DURATIONS[batch.timeframe]:continue
            matched=owner.research_retest_matches(row[4],row[5],row[6],event.level,side.value,tolerance=retest_tolerance)
            if type(matched) is not bool:raise ValueError('STRATEGY_ENTRY_MATH_RETEST_BOOL_REQUIRED')
            if not matched:continue
            context=_context(batch,decision,pattern);vol=context['volatility']
            if vol is None or vol['volume_ratio']<min_volume_ratio:continue
            out.append(_entry(batch,row,decision,side,event.level,pattern,context,event=event));break
    return _ordered(out)

def generate_profile_reclaim_entries(symbol,bars,profiles,flow=(),volatility=(),*,as_of_ms,timeframe):
    """Event-adjacent candle crossing; decision waits for BOTH actual availabilities.

    Profile, signed flow and volatility are selected by declared availability at
    that decision. Missing flow is None, never synthetic zero, L2 or OI evidence.
    """
    batch=_prepare(symbol,bars,(),volatility,profiles,flow,as_of_ms=as_of_ms,timeframe=timeframe)
    out=[];pattern=ResearchEntryPattern.PROFILE_RECLAIM
    for prior,row in zip(batch.rows,batch.rows[1:]):
        decision=max(prior[2],row[2])
        if decision>batch.cutoff:continue
        context=_context(batch,decision,pattern);profile=context['profile']
        if profile is None:continue
        reference=profile['poc'];side=None
        if prior[6]<reference<=row[6]:side=EntrySide.LONG
        elif prior[6]>reference>=row[6]:side=EntrySide.SHORT
        if side is None:continue
        observed=_flow_at(batch,decision)
        if observed is not None and ((side is EntrySide.LONG and observed.delta<=0) or (side is EntrySide.SHORT and observed.delta>=0)):continue
        out.append(_entry(batch,row,decision,side,reference,pattern,context,prior=prior,flow=observed))
    return _ordered(out)

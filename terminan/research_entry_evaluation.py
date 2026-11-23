"""Bounded rich-entry evaluation v2; selection evidence is never execution authority.

This adapter captures literal records, retains all evidence/context, and calls
one existing signal evaluator. It contains no fill, risk or numeric formula.
"""
from dataclasses import dataclass,field,fields
from decimal import Decimal
from types import MappingProxyType
import gc,hashlib,json,math
from .strategy_entries import (ResearchEntry,EntryEvidence,ResearchEntryPattern,EntrySide,RiskBasis,SignedFlowObservation)
from .continuation_strategy import CandleBodyObservation
from .market_structure import MarketStructureReference
from .entry_context import ProfileKind
from .volatility import VolatilityMetrics,VolatilityRegime
from .research_signals import ResearchSignal
from . import research_evaluation as evaluator

@dataclass(frozen=True,slots=True)
class EntryEvaluationOutcome:
    entry:ResearchEntry
    outcome:evaluator.EvaluationOutcome

@dataclass(frozen=True,slots=True)
class ResearchEntryEvaluation:
    input_sha256:str
    entries:tuple[ResearchEntry,...]
    evaluation:evaluator.ResearchEvaluation
    outcomes:tuple[EntryEvaluationOutcome,...]
    version:str=field(default='research_entry_evaluation.v2',init=False)
    source_authentication:str=field(default='NOT_EVALUATED',init=False)
    execution_authority:bool=field(default=False,init=False)
    trading_authorized:bool=field(default=False,init=False)

_RECORDS=(ResearchEntry,EntryEvidence,ResearchSignal,SignedFlowObservation,
          CandleBodyObservation,MarketStructureReference,VolatilityMetrics)
_ENUMS=(ResearchEntryPattern,EntrySide,RiskBasis,ProfileKind,VolatilityRegime)

def _capture_entries(entries):
    if (type(entries) is not tuple and type(entries) is not list) or len(entries)>512:
        raise ValueError('ENTRY_EVALUATION_BOUNDED_LITERAL_BATCH')
    nodes=0;budget=8388608
    def charge(size):
        nonlocal budget
        budget-=size
        if budget<0:raise ValueError('ENTRY_EVALUATION_BYTE_BUDGET')
    def copy(value,depth):
        nonlocal nodes
        nodes+=1
        if nodes>250000 or depth>16:raise ValueError('ENTRY_EVALUATION_GRAPH_BUDGET')
        kind=type(value)
        if value is None or kind is bool:charge(5);return value
        if kind is int:
            if not -(2**53)<=value<=2**53:raise ValueError('ENTRY_EVALUATION_INTEGER_BUDGET')
            charge(18);return value
        if kind is float:
            if not math.isfinite(value):raise ValueError('ENTRY_EVALUATION_FINITE_NUMBER')
            charge(24);return value
        if kind is str:
            if len(value)>65536:raise ValueError('ENTRY_EVALUATION_STRING_BUDGET')
            charge(len(json.dumps(value,ensure_ascii=True)));return value
        if kind is Decimal:
            evaluator._decimal(value);charge(196);return value
        if any(kind is enum for enum in _ENUMS):charge(128);return value
        if any(kind is record for record in _RECORDS):
            leaves=tuple((f.name,copy(getattr(value,f.name),depth+1)) for f in fields(kind))
            clone=object.__new__(kind)
            for name,item in leaves:object.__setattr__(clone,name,item)
            return clone
        if kind is MappingProxyType:
            # A proxy may wrap an arbitrary callback-bearing Mapping. Inspect
            # its referent type before iteration; only an exact dict is literal.
            referents=gc.get_referents(value)
            if len(referents)!=1 or type(referents[0]) is not dict:raise ValueError('ENTRY_EVALUATION_LITERAL_PROXY')
            value=referents[0];kind=dict
        if kind is dict:
            if len(value)>512 or any(type(key) is not str for key in value):raise ValueError('ENTRY_EVALUATION_LITERAL_KEYS')
            charge(2+len(value)*2)
            return MappingProxyType({copy(key,depth+1):copy(item,depth+1) for key,item in tuple(value.items())})
        if kind is tuple or kind is list:
            if len(value)>4096:raise ValueError('ENTRY_EVALUATION_ARRAY_BUDGET')
            charge(2+len(value));return tuple(copy(item,depth+1) for item in tuple(value))
        raise ValueError('ENTRY_EVALUATION_EXACT_LITERAL_GRAPH')
    captured=tuple(copy(value,0) for value in tuple(entries))
    if any(type(value) is not ResearchEntry for value in captured):raise ValueError('ENTRY_EVALUATION_TYPED_ENTRY')
    return captured

def _number(value):
    if (type(value) is not int and type(value) is not float) or not math.isfinite(value) or value<0:
        raise ValueError('ENTRY_EVALUATION_LITERAL_NONNEGATIVE_EVIDENCE')

def _declarations(value):
    if type(value.source_authentication) is not str or value.source_authentication!='NOT_EVALUATED' or value.execution_authority is not False or value.trading_authorized is not False:
        raise ValueError('ENTRY_EVALUATION_NOT_AUTHORITY')

def _reference(value,decision):
    if type(value) is not MarketStructureReference:raise ValueError('ENTRY_EVALUATION_TYPED_REFERENCE')
    start,end,available=(evaluator._clock(v) for v in (value.event_start_ms,value.event_end_ms,value.available_at_ms))
    if not start<end<=available<=decision:raise ValueError('ENTRY_EVALUATION_REFERENCE_CLOCK')

def _admit(entries,pattern):
    last=None
    for entry in entries:
        _declarations(entry)
        if type(entry.version) is not str or entry.version!='strategy_entries.v2' or type(entry.pattern) is not ResearchEntryPattern or type(entry.side) is not EntrySide or entry.pattern.value!=pattern:raise ValueError('ENTRY_EVALUATION_V2_PATTERN_REQUIRED')
        decision=evaluator._clock(entry.decision_ms)
        if last is not None and decision<=last:raise ValueError('ENTRY_EVALUATION_UNIQUE_ORDERED_CLOCKS')
        last=decision
        if type(entry.signal) is not ResearchSignal or entry.signal.decision_ms!=decision or type(entry.signal.decision_ms) is not int or type(entry.signal.side) is not str or entry.signal.side!=entry.side.value:raise ValueError('ENTRY_EVALUATION_SIGNAL_ASSOCIATION')
        _number(entry.reference)
        evidence=entry.evidence
        if type(evidence) is not EntryEvidence:raise ValueError('ENTRY_EVALUATION_TYPED_EVIDENCE')
        _declarations(evidence);_number(evidence.entry_price);_number(evidence.risk_atr_fraction)
        if type(evidence.risk_basis) is not RiskBasis:raise ValueError('ENTRY_EVALUATION_TYPED_RISK_BASIS')
        if type(evidence.candle_references) is not tuple or not 1<=len(evidence.candle_references)<=2:raise ValueError('ENTRY_EVALUATION_CANDLE_REFERENCES')
        for ref in (*evidence.candle_references,evidence.sweep_reference,evidence.break_reference):
            if ref is not None:_reference(ref,decision)
        for name in ('volume_ratio','atr_percentile'):
            value=getattr(evidence,name)
            if value is not None:_number(value)
        if evidence.atr_percentile is not None and evidence.atr_percentile>1:raise ValueError('ENTRY_EVALUATION_PERCENTILE')
        if evidence.volatility_regime is not None and type(evidence.volatility_regime) is not VolatilityRegime:raise ValueError('ENTRY_EVALUATION_VOLATILITY_REGIME')
        if evidence.profile_kind is not None and type(evidence.profile_kind) is not ProfileKind:raise ValueError('ENTRY_EVALUATION_PROFILE_KIND')
        if evidence.profile_available_at_ms is not None and evaluator._clock(evidence.profile_available_at_ms)>decision:raise ValueError('ENTRY_EVALUATION_PROFILE_CLOCK')
        context=entry.context
        keys={'schema','decision_ms','metadata','volatility','profile','source_authentication','execution_authority','trading_authorized'}
        if type(context) is not MappingProxyType or set(context)!=keys or type(context['schema']) is not str or context['schema']!='terminan.entry-context.v1' or type(context['decision_ms']) is not int or context['decision_ms']!=decision:raise ValueError('ENTRY_EVALUATION_CONTEXT_SCHEMA_CLOCK')
        if type(context['source_authentication']) is not str or context['source_authentication']!='NOT_EVALUATED' or context['execution_authority'] is not False or context['trading_authorized'] is not False:raise ValueError('ENTRY_EVALUATION_CONTEXT_NOT_AUTHORITY')
        if type(context['metadata']) is not MappingProxyType:raise ValueError('ENTRY_EVALUATION_LITERAL_CONTROL_METADATA')
        vol=evidence.volatility
        if vol is None:
            if context['volatility'] is not None or evidence.atr_percentile is not None or evidence.volume_ratio is not None or evidence.volatility_regime is not None or evidence.risk_basis is not RiskBasis.POLICY_DEFAULT or evidence.risk_atr_fraction!=.002:raise ValueError('ENTRY_EVALUATION_MISSING_VOLATILITY_NOT_ZERO')
        else:
            if type(vol) is not VolatilityMetrics:raise ValueError('ENTRY_EVALUATION_TYPED_VOLATILITY')
            _declarations(vol)
            if type(vol.availability_basis) is not str or vol.availability_basis!='CALLER_DECLARED_PREFIX_MAX' or type(vol.version) is not str or not 1<=len(vol.version)<=128 or not vol.version.isascii() or type(vol.regime) is not VolatilityRegime:raise ValueError('ENTRY_EVALUATION_VOLATILITY_DECLARATION')
            if not evaluator._clock(vol.event_start_ms)<=evaluator._clock(vol.available_at_ms)<=decision:raise ValueError('ENTRY_EVALUATION_VOLATILITY_CLOCK')
            names=('atr_fraction','realized_volatility','parkinson_volatility','range_fraction','volume_ratio','turnover_ratio','atr_percentile')
            for name in names:_number(getattr(vol,name))
            projected={f.name:getattr(vol,f.name) for f in fields(VolatilityMetrics)};projected['regime']=vol.regime.value
            context_vol=context['volatility']
            if type(context_vol) is not MappingProxyType or set(context_vol)!=set(projected) or any(type(context_vol[name]) is not type(value) or context_vol[name]!=value for name,value in projected.items()) or type(evidence.atr_percentile) is not type(vol.atr_percentile) or type(evidence.volume_ratio) is not type(vol.volume_ratio) or type(evidence.risk_atr_fraction) is not type(vol.atr_fraction) or evidence.atr_percentile!=vol.atr_percentile or evidence.volume_ratio!=vol.volume_ratio or evidence.volatility_regime is not vol.regime or evidence.risk_basis is not RiskBasis.OBSERVED_ATR or evidence.risk_atr_fraction!=vol.atr_fraction:raise ValueError('ENTRY_EVALUATION_SELECTED_VOLATILITY_ASSOCIATION')
        profile=context['profile']
        if profile is None:
            if evidence.profile_kind is not None or evidence.profile_available_at_ms is not None:raise ValueError('ENTRY_EVALUATION_PROFILE_ASSOCIATION')
        else:
            if type(profile) is not MappingProxyType or set(profile)!={'poc','value_area_high','value_area_low','value_area_width','available_at_ms','kind','availability_basis','source_authentication','execution_authority','trading_authorized'}:raise ValueError('ENTRY_EVALUATION_PROFILE_SCHEMA')
            for name in ('poc','value_area_high','value_area_low','value_area_width'):_number(profile[name])
            if type(profile['kind']) is not str or evidence.profile_kind is None or profile['kind']!=evidence.profile_kind.value or profile['available_at_ms']!=evidence.profile_available_at_ms or type(profile['available_at_ms']) is not int or type(profile['availability_basis']) is not str or profile['availability_basis']!='CALLER_DECLARED' or type(profile['source_authentication']) is not str or profile['source_authentication']!='NOT_EVALUATED' or profile['execution_authority'] is not False or profile['trading_authorized'] is not False:raise ValueError('ENTRY_EVALUATION_PROFILE_ASSOCIATION')
        flow=evidence.flow
        if flow is not None:
            if type(flow) is not SignedFlowObservation:raise ValueError('ENTRY_EVALUATION_TYPED_FLOW')
            _declarations(flow)
            if type(flow.availability_basis) is not str or flow.availability_basis!='CALLER_DECLARED' or not evaluator._clock(flow.event_start_ms)<=evaluator._clock(flow.available_at_ms)<=decision or (type(flow.delta) is not int and type(flow.delta) is not float) or not math.isfinite(flow.delta):raise ValueError('ENTRY_EVALUATION_FLOW_DECLARATION')
        body=evidence.body_reference
        if entry.pattern is ResearchEntryPattern.CONTINUATION:
            if type(body) is not CandleBodyObservation or vol is None:raise ValueError('ENTRY_EVALUATION_CONTINUATION_BODY_VOLATILITY')
            _number(body.open);_number(body.close)
            ref=evidence.candle_references[-1]
            if (body.event_start_ms,body.event_end_ms,body.available_at_ms)!=(ref.event_start_ms,ref.event_end_ms,ref.available_at_ms) or type(body.event_start_ms) is not int or type(body.event_end_ms) is not int or type(body.available_at_ms) is not int or body.event_start_ms!=vol.event_start_ms or body.close!=entry.reference or body.close!=evidence.entry_price or decision!=max(body.available_at_ms,vol.available_at_ms):raise ValueError('ENTRY_EVALUATION_CONTINUATION_ASSOCIATION')
        elif body is not None:raise ValueError('ENTRY_EVALUATION_UNEXPECTED_BODY')

def _encoded(value):
    kind=type(value)
    if kind is Decimal:return {'decimal':str(value)}
    if any(kind is enum for enum in _ENUMS):return {'enum':kind.__name__,'value':value.value}
    if any(kind is record for record in _RECORDS):return {'record':kind.__name__,'fields':{f.name:_encoded(getattr(value,f.name)) for f in fields(kind)}}
    if kind is MappingProxyType:return {key:_encoded(item) for key,item in value.items()}
    if kind is tuple:return [_encoded(item) for item in value]
    return value

def evaluate_research_entries(pattern,entries,candles,*,dataset,bar_ms,notional=Decimal(100),fee_rate=Decimal('0.0006'),slippage_bps=Decimal(2),folds=5,embargo_ms=0,ambiguity_policy='SL_FIRST',min_folds=3,min_samples=60,min_profitable_fraction=.60,min_expectancy=0.0,min_profit_factor=1.05,max_loss_fold_fraction=.50):
    pattern=evaluator._text(pattern,'[a-z0-9_]{1,64}')
    entries=_capture_entries(entries);_admit(entries,pattern)
    policy=(bar_ms,folds,embargo_ms,ambiguity_policy,notional,fee_rate,slippage_bps,min_folds,min_samples,min_profitable_fraction,min_expectancy,min_profit_factor,max_loss_fold_fraction)
    _,signals,rows,dataset,_=evaluator._capture(pattern,tuple(e.signal for e in entries),candles,dataset,policy)
    # The complete rich graph AND evaluator leaves/policies are detached before
    # the first evaluation/numeric callback. No caller mapping remains live.
    canonical=json.dumps({'schema':'terminan.rich-entry-evaluation.inputs.v2','entries':_encoded(entries)},sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
    if len(canonical)>8388608:raise ValueError('ENTRY_EVALUATION_CANONICAL_BYTE_BUDGET')
    result=evaluator.evaluate_research_signals(pattern,signals,rows,dataset=dataset,bar_ms=bar_ms,notional=notional,fee_rate=fee_rate,slippage_bps=slippage_bps,folds=folds,embargo_ms=embargo_ms,ambiguity_policy=ambiguity_policy,min_folds=min_folds,min_samples=min_samples,min_profitable_fraction=min_profitable_fraction,min_expectancy=min_expectancy,min_profit_factor=min_profit_factor,max_loss_fold_fraction=max_loss_fold_fraction)
    if type(result) is not evaluator.ResearchEvaluation or type(result.outcomes) is not tuple or len(result.outcomes)!=len(entries):raise ValueError('ENTRY_EVALUATION_OUTCOME_CONSERVATION')
    by_clock={entry.decision_ms:entry for entry in entries};out=[];seen=set()
    for outcome in result.outcomes:
        if type(outcome) is not evaluator.EvaluationOutcome or type(outcome.signal) is not ResearchSignal or type(outcome.signal.decision_ms) is not int:raise ValueError('ENTRY_EVALUATION_TYPED_OUTCOME')
        clock=outcome.signal.decision_ms
        if clock in seen or clock not in by_clock or outcome.signal!=by_clock[clock].signal:raise ValueError('ENTRY_EVALUATION_EXACT_OUTCOME_ASSOCIATION')
        seen.add(clock);out.append(EntryEvaluationOutcome(by_clock[clock],outcome))
    if seen!=set(by_clock):raise ValueError('ENTRY_EVALUATION_OUTCOME_CONSERVATION')
    fingerprint=hashlib.sha256(canonical+b'\0'+result.input_sha256.encode('ascii')).hexdigest()
    return ResearchEntryEvaluation(fingerprint,entries,result,tuple(out))

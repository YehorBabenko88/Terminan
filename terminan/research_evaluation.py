"""Bounded offline evaluation v1; no fitting, data IO or execution authority.

Folds use contiguous candle-index partitions and independent simulation accounts.
Market decisions use the first candle START >= decision. Limits use PaperEngine's
strict next boundary. Release equality permits a new offer. IID rounded-binary64
statistics describe exact paper fills, never replace their Decimal accounting.
"""
from dataclasses import dataclass, field, replace
from decimal import Decimal
from enum import Enum
import hashlib,json,re
from .research_signals import ResearchSignal,ResearchBar,SignalNotFilled,validate_signal_batch
from .paper import PaperEngine
from .strategy_screening import screen_research_pattern,ScreeningStatus

@dataclass(frozen=True,slots=True)
class EvaluationCandle:
    event_start_ms:int
    event_end_ms:int
    available_at_ms:int
    open:Decimal
    high:Decimal
    low:Decimal
    close:Decimal
    volume:Decimal

@dataclass(frozen=True,slots=True)
class EvaluationDataset:
    source_sha256:str
    symbol:str
    value_unit:str
    available_from_ms:int
    as_of_ms:int
    source_authentication:str=field(default='NOT_EVALUATED',init=False)
    execution_authority:bool=field(default=False,init=False)
    trading_authorized:bool=field(default=False,init=False)

class EvaluationDisposition(str,Enum):
    FILLED='FILLED'
    NOT_FILLED='NOT_FILLED'
    POSITION_OCCUPIED='POSITION_OCCUPIED'
    OUTSIDE_TEST_WINDOW='OUTSIDE_TEST_WINDOW'

@dataclass(frozen=True,slots=True)
class EvaluationOutcome:
    signal:ResearchSignal
    disposition:EvaluationDisposition
    fold_index:int|None
    known_at_ms:int|None
    execution:object=None

@dataclass(frozen=True,slots=True)
class EvaluationFold:
    index:int
    start_ms:int
    end_ms:int
    test_start_ms:int
    numeric:object

@dataclass(frozen=True,slots=True)
class ResearchEvaluation:
    input_sha256:str
    dataset:EvaluationDataset
    folds:tuple
    outcomes:tuple
    numeric:object
    bootstrap:object
    verdict:object
    policy:str=field(default='CANDLE_INDEX_INDEPENDENT_ACCOUNTS_V1',init=False)
    numeric_policy:str=field(default='DECIMAL_TO_BINARY64_V1_DESCRIPTIVE_ONLY',init=False)
    availability_basis:str=field(default='CALLER_DECLARED_ALL_EXAMINED_DEPENDENCIES_MAX',init=False)
    source_authentication:str=field(default='NOT_EVALUATED',init=False)
    out_of_sample_qualified:bool=field(default=False,init=False)
    point_in_time_qualified:bool=field(default=False,init=False)
    execution_authority:bool=field(default=False,init=False)
    trading_authorized:bool=field(default=False,init=False)

def _clock(value):
    if type(value) is not int or not 0<=value<=4102444800000:raise ValueError('EVALUATION_LITERAL_CLOCK')
    return value

def _decimal(value):
    # Resource codec only. Domain/financial arithmetic belongs to canonical Math.
    if type(value) is not Decimal or not value.is_finite():raise ValueError('EVALUATION_PLAIN_FINITE_DECIMAL')
    parts=value.as_tuple()
    if len(parts.digits)>64 or not -128<=parts.exponent<=128:raise ValueError('EVALUATION_DECIMAL_CODEC_BUDGET')
    return value

def _text(value,pattern):
    if type(value) is not str or re.fullmatch(pattern,value) is None:raise ValueError('EVALUATION_LITERAL_TEXT')
    return value

def _capture(pattern,signals,candles,dataset,policy):
    pattern=_text(pattern,'[a-z0-9_]{1,64}')
    if type(dataset) is not EvaluationDataset:raise ValueError('EVALUATION_TYPED_DATASET')
    source=_text(dataset.source_sha256,'[0-9a-f]{64}');symbol=_text(dataset.symbol,'[A-Z0-9]{2,30}')
    unit=_text(dataset.value_unit,'[A-Za-z0-9_.:/-]{1,32}')
    available,asof=_clock(dataset.available_from_ms),_clock(dataset.as_of_ms)
    if available>asof or type(dataset.source_authentication) is not str or dataset.source_authentication!='NOT_EVALUATED' or dataset.execution_authority is not False or dataset.trading_authorized is not False:raise ValueError('EVALUATION_UNATTESTED_DATASET_REQUIRED')
    detached=EvaluationDataset(source,symbol,unit,available,asof)
    if (type(signals) is not tuple and type(signals) is not list) or len(signals)>512:raise ValueError('EVALUATION_SIGNAL_BATCH')
    if (type(candles) is not tuple and type(candles) is not list) or not 1<=len(candles)<=4096:raise ValueError('EVALUATION_CANDLE_BATCH')
    bar_ms,folds,embargo,ambiguity,notional,fee,slip,min_folds,min_samples,profitable,expectancy,factor,loss=policy
    if type(bar_ms) is not int or not 1<=bar_ms<=2678400000 or type(folds) is not int or not 1<=folds<=min(128,len(candles)) or type(embargo) is not int or embargo<0:raise ValueError('EVALUATION_BOUNDED_FOLD_POLICY')
    if type(ambiguity) is not str or ambiguity not in ('SL_FIRST','TP_FIRST'):raise ValueError('EVALUATION_AMBIGUITY_POLICY')
    for value in (notional,fee,slip):_decimal(value)
    if type(min_folds) is not int or not 1<=min_folds<=128 or type(min_samples) is not int or not 0<=min_samples<=4096:raise ValueError('EVALUATION_SCREENING_COUNTS')
    for value in (profitable,expectancy,factor,loss):
        if type(value) is not float and type(value) is not int:raise ValueError('EVALUATION_SCREENING_LITERAL')
    if 4*len(signals)*len(candles)+len(candles)>1000000:raise ValueError('EVALUATION_ROW_VISIT_BUDGET')
    rows=[];previous=None
    for row in tuple(candles):
        if type(row) is not EvaluationCandle:raise ValueError('EVALUATION_TYPED_CANDLE')
        start,end,known=(_clock(v) for v in (row.event_start_ms,row.event_end_ms,row.available_at_ms))
        values=tuple(_decimal(v) for v in (row.open,row.high,row.low,row.close,row.volume))
        if start<available or start%bar_ms or end!=start+bar_ms or not end<=known<=asof or previous is not None and start!=previous:raise ValueError('EVALUATION_CONTIGUOUS_CLOSED_AVAILABLE_CANDLES')
        previous=end;rows.append(EvaluationCandle(start,end,known,*values))
    captured=[];last=None
    for signal in tuple(signals):
        if type(signal) is not ResearchSignal:raise ValueError('EVALUATION_TYPED_SIGNAL')
        name=_text(signal.symbol,'[A-Z0-9]{2,30}');decision=_clock(signal.decision_ms)
        if name!=symbol or not available<=decision<=asof or last is not None and decision<=last:raise ValueError('EVALUATION_UNIQUE_ORDERED_SIGNAL_CLOCK')
        last=decision
        side=_text(signal.side,'long|short');kind=_text(signal.entry_kind,'market|limit')
        entry=None if signal.entry_price is None else _decimal(signal.entry_price)
        stop,target=_decimal(signal.stop),_decimal(signal.target)
        if kind=='market' and entry is not None or kind=='limit' and entry is None:raise ValueError('EVALUATION_ENTRY_POLICY')
        captured.append(ResearchSignal(name,decision,side,kind,entry,stop,target))
    windows=[]
    for i in range(folds):
        subset=rows[i*len(rows)//folds:(i+1)*len(rows)//folds]
        start,end=subset[0].event_start_ms,subset[-1].event_end_ms
        if embargo>=end-start:raise ValueError('EVALUATION_EMBARGO_WINDOW')
        windows.append((start,end,start+embargo,tuple(r for r in subset if r.event_start_ms>=start+embargo)))
    return pattern,tuple(captured),tuple(rows),detached,tuple(windows)

def evaluate_research_signals(pattern,signals,candles,*,dataset,bar_ms,notional=Decimal(100),fee_rate=Decimal('0.0006'),slippage_bps=Decimal(2),folds=5,embargo_ms=0,ambiguity_policy='SL_FIRST',min_folds=3,min_samples=60,min_profitable_fraction=.60,min_expectancy=0.0,min_profit_factor=1.05,max_loss_fold_fraction=.50):
    policy=(bar_ms,folds,embargo_ms,ambiguity_policy,notional,fee_rate,slippage_bps,min_folds,min_samples,min_profitable_fraction,min_expectancy,min_profit_factor,max_loss_fold_fraction)
    pattern,signals,rows,dataset,windows=_capture(pattern,signals,candles,dataset,policy)
    # All leaves/flags and policies have been detached before the FIRST Math call.
    import market_math as owner
    from history_statistics import NumericFoldObservation,project_decimal_observations,numeric_profit_loss_summary,iid_observation_mean_bootstrap
    from .strategy_catalog import research_strategy,StrategyAvailability
    if research_strategy(pattern).availability is not StrategyAvailability.RESEARCH_GENERATOR:raise ValueError('EVALUATION_RESEARCH_GENERATOR_REQUIRED')
    # Hash signed zeros/trailing zeros exactly as supplied, never coerce objects.
    def encoded(value):
        if type(value) is Decimal:return str(value)
        if type(value) is tuple:return [encoded(v) for v in value]
        return value
    canonical={'schema':'terminan.research.evaluation.inputs.v1','pattern':pattern,'dataset':(dataset.source_sha256,dataset.symbol,dataset.value_unit,dataset.available_from_ms,dataset.as_of_ms),'candles':tuple((r.event_start_ms,r.event_end_ms,r.available_at_ms,r.open,r.high,r.low,r.close,r.volume) for r in rows),'signals':tuple((s.symbol,s.decision_ms,s.side,s.entry_kind,s.entry_price,s.stop,s.target) for s in signals),'policy':policy,'fold_policy':'CANDLE_INDEX_INDEPENDENT_ACCOUNTS_V1','market_policy':'FIRST_START_GE_DECISION','limit_policy':'STRICT_NEXT_BOUNDARY','occupied_policy':'DECISION_GE_RELEASE_ALLOWED','pending_policy':'UNTIL_FOLD_END_AND_ALL_PAGE_AVAILABILITY','availability_policy':'ALL_EXAMINED_DEPENDENCIES_MAX','numeric_policy':'DECIMAL_TO_BINARY64_V1_DESCRIPTIVE_ONLY','bootstrap':(500,17,.95),'math_abi':'PROFIT_LOSS_SUMMARY_V1'}
    raw=json.dumps({k:encoded(v) for k,v in canonical.items()},sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')
    if len(raw)>8388608:raise ValueError('EVALUATION_CANONICAL_BYTE_BUDGET')
    fingerprint=hashlib.sha256(raw).hexdigest()
    bars=tuple(ResearchBar(r.event_start_ms,r.open,r.high,r.low,r.close,r.volume) for r in rows)
    # Canonical Math owns financial domain checks and Paper owns signal admission.
    for row in rows:
        if owner.candle_ohlcv_valid(row.open,row.high,row.low,row.close,row.volume) is not True:raise ValueError('EVALUATION_OHLCV_DOMAIN')
    for signal in signals:
        validate_signal_batch(signal,bars,bar_ms=bar_ms,as_of_ms=dataset.as_of_ms,available_from_ms=dataset.available_from_ms,ambiguity_policy=ambiguity_policy)
    # Validate all screening numeric policy even for an empty evaluation.
    screen_research_pattern(pattern,(),min_folds=min_folds,min_samples=min_samples,min_profitable_fraction=min_profitable_fraction,min_expectancy=min_expectancy,min_profit_factor=min_profit_factor,max_loss_fold_fraction=max_loss_fold_fraction)
    engines=tuple(PaperEngine(notional=notional,fee_rate=fee_rate,slippage_bps=slippage_bps) for _ in windows)
    outcomes=[];fold_results=[];fold_metrics=[];pooled=[]
    for i,(start,end,test_start,subset) in enumerate(windows):
        engine=engines[i];engine.enabled=True;release=None;values=[]
        foldbars=tuple(ResearchBar(r.event_start_ms,r.open,r.high,r.low,r.close,r.volume) for r in subset)
        for signal in signals:
            if not start<=signal.decision_ms<end:continue
            if signal.decision_ms<test_start or not subset:
                outcomes.append(EvaluationOutcome(signal,EvaluationDisposition.OUTSIDE_TEST_WINDOW,i,None));continue
            if release is not None and signal.decision_ms<release:
                outcomes.append(EvaluationOutcome(signal,EvaluationDisposition.POSITION_OCCUPIED,i,release));continue
            try:
                execution=engine.execute_signal(signal,foldbars,bar_ms=bar_ms,as_of_ms=dataset.as_of_ms,available_from_ms=dataset.available_from_ms,ambiguity_policy=ambiguity_policy)
            except SignalNotFilled as exc:
                if type(exc) is not SignalNotFilled:raise
                release=max(end,max(r.available_at_ms for r in subset))
                outcomes.append(EvaluationOutcome(signal,EvaluationDisposition.NOT_FILLED,i,release));continue
            first=signal.decision_ms if signal.entry_kind=='market' else (signal.decision_ms//bar_ms+1)*bar_ms
            dependencies=tuple(r for r in subset if first<=r.event_start_ms<=execution.exit_ms)
            if not dependencies:raise ValueError('EVALUATION_EXECUTION_DEPENDENCY_REQUIRED')
            release=max(r.available_at_ms for r in dependencies)
            outcomes.append(EvaluationOutcome(signal,EvaluationDisposition.FILLED,i,release,execution));values.append(execution.fill.net)
        projected=project_decimal_observations(tuple(values));numeric=numeric_profit_loss_summary(projected)
        fold_results.append(EvaluationFold(i,start,end,test_start,numeric));pooled.extend(projected)
        fold_metrics.append(NumericFoldObservation(numeric.numeric.count,numeric.numeric.mean,numeric.profit_factor))
    for signal in signals:
        if not rows[0].event_start_ms<=signal.decision_ms<rows[-1].event_end_ms:
            outcomes.append(EvaluationOutcome(signal,EvaluationDisposition.OUTSIDE_TEST_WINDOW,None,None))
    outcomes.sort(key=lambda row:row.signal.decision_ms)
    if len(outcomes)!=len(signals):raise ValueError('EVALUATION_OUTCOME_CONSERVATION')
    numeric=numeric_profit_loss_summary(tuple(pooled))
    bootstrap=iid_observation_mean_bootstrap(tuple(pooled),runs=500,seed=17,confidence=.95) if pooled else None
    verdict=screen_research_pattern(pattern,tuple(fold_metrics),min_folds=min_folds,min_samples=min_samples,min_profitable_fraction=min_profitable_fraction,min_expectancy=min_expectancy,min_profit_factor=min_profit_factor,max_loss_fold_fraction=max_loss_fold_fraction)
    if verdict.status is ScreeningStatus.KEEP and bootstrap is not None and bootstrap.lower<=0:
        verdict=replace(verdict,status=ScreeningStatus.NEEDS_MORE_DATA,reasons=verdict.reasons+('BOOTSTRAP_CROSSES_ZERO',))
    return ResearchEvaluation(fingerprint,dataset,tuple(fold_results),tuple(outcomes),numeric,bootstrap,verdict)

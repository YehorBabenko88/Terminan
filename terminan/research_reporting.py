"""Pure declared research reporting; no persistence or execution paths.

All arithmetic summaries belong to Math. Amounts come from the existing paper
fill, while optional excursions/R and coverage remain posthoc caller declarations.
"""
from dataclasses import dataclass,field,fields
from decimal import Decimal
from datetime import datetime,timezone,timedelta
from enum import Enum
from types import MappingProxyType
import gc,hashlib,json,math,re
from . import research_entry_evaluation as rich
from . import research_evaluation as evaluation
from .research_signals import SignalExecution
from .paper import PaperFill
from .strategy_screening import ResearchPatternVerdict,ScreeningStatus
import history_statistics as numeric

class CoverageDeclaration(str,Enum):
    COMPLETE_HISTORY='COMPLETE_HISTORY'
    PARTIAL_HISTORY='PARTIAL_HISTORY'
    UNCLASSIFIED='UNCLASSIFIED'

@dataclass(frozen=True,slots=True)
class DeclaredTradeMetadata:
    symbol:str
    decision_ms:int
    available_at_ms:int
    coverage:CoverageDeclaration|None=None
    mae:Decimal|None=None
    mae_unit:str|None=None
    mfe:Decimal|None=None
    mfe_unit:str|None=None
    r_multiple:Decimal|None=None
    r_multiple_unit:str|None=None
    declared_volatility:str|None=field(default=None,kw_only=True)
    declared_poc_mode:str|None=field(default=None,kw_only=True)
    availability_basis:str=field(default='CALLER_DECLARED_POSTHOC',init=False)
    source_authentication:str=field(default='NOT_EVALUATED',init=False)
    execution_authority:bool=field(default=False,init=False)
    trading_authorized:bool=field(default=False,init=False)

@dataclass(frozen=True,slots=True)
class ReportUnits:
    amount:str
    mae:str|None
    mfe:str|None
    r_multiple:str|None
    basis:str=field(default='CALLER_DECLARED_NOT_INFERRED',init=False)

@dataclass(frozen=True,slots=True)
class ReportTrade:
    identity:tuple[str,int]
    outcome:rich.EntryEvaluationOutcome
    gross_pnl:Decimal
    net_pnl:Decimal
    fees:Decimal
    entry_ms:int
    exit_ms:int
    holding_ms:int
    declaration:DeclaredTradeMetadata|None

@dataclass(frozen=True,slots=True)
class VolatilityReportPartition:
    label:str|None
    trade_ids:tuple
    numeric:numeric.NumericTradeSummary

@dataclass(frozen=True,slots=True)
class CoverageReportPartition:
    declaration:CoverageDeclaration
    trade_ids:tuple
    numeric:numeric.NumericTradeSummary
    by_volatility:tuple[VolatilityReportPartition,...]

@dataclass(frozen=True,slots=True)
class ResearchPerformanceReport:
    input_sha256:str
    evaluation:rich.ResearchEntryEvaluation
    report_as_of_ms:int
    units:ReportUnits
    metadata:MappingProxyType
    trades:tuple[ReportTrade,...]
    all_filled:numeric.NumericTradeSummary
    by_coverage:tuple[CoverageReportPartition,...]
    by_volatility:tuple[VolatilityReportPartition,...]
    schema:str=field(default='terminan.research-performance-report.v1',kw_only=True)
    math_abi:str=field(default='math.numeric.screening.ordered-binary64.v1/declared-trade-summary.v1',init=False)
    numeric_policy:str=field(default='DECIMAL_TO_BINARY64_V1_ORDERED_DESCRIPTIVE_NOT_LEDGER_ACCOUNTING',init=False)
    holding_basis:str=field(default='MODELED_BAR_START_DURATION',init=False)
    coverage_basis:str=field(default='CALLER_DECLARATIONS_ONLY',init=False)
    metric_basis:str=field(default='POSTHOC_CALLER_DECLARATIONS_NOT_INFERRED_EXCURSIONS',init=False)
    execution_basis:str=field(default='CALLER_SUPPLIED_MODELED_EXECUTIONS_NOT_REEXECUTED',kw_only=True)
    execution_domain_policy:str=field(default='MATH_PAPER_EXECUTION_VALUES_V1_DECLARATIONS_ONLY',init=False)
    source_authentication:str=field(default='NOT_EVALUATED',init=False)
    completeness_qualified:bool=field(default=False,init=False)
    point_in_time_qualified:bool=field(default=False,init=False)
    execution_authority:bool=field(default=False,init=False)
    trading_authorized:bool=field(default=False,init=False)

_RECORDS=rich._RECORDS+(rich.ResearchEntryEvaluation,rich.EntryEvaluationOutcome,
 evaluation.EvaluationDataset,evaluation.ResearchEvaluation,evaluation.EvaluationOutcome,
 evaluation.EvaluationFold,SignalExecution,PaperFill,ResearchPatternVerdict,DeclaredTradeMetadata)
_ENUMS=rich._ENUMS+(CoverageDeclaration,evaluation.EvaluationDisposition,ScreeningStatus)
_NUMERIC=(numeric.NumericSampleSummary,numeric.ProfitFactorObservation,numeric.NumericFoldObservation,
 numeric.NumericFoldSummary,numeric.IIDMeanInterval,numeric.NumericProfitLossSummary,
 numeric.NumericTradeObservation,numeric.NumericOptionalSummary,numeric.NumericTradeSummary)

_NUMERIC_FIELDS={
 numeric.NumericSampleSummary:((int,),(int,),(int,),(float,),(float,),(float,)),
 numeric.ProfitFactorObservation:((str,),(int,float,type(None))),
 numeric.NumericFoldObservation:((int,),(int,float),(numeric.ProfitFactorObservation,)),
 numeric.NumericFoldSummary:((int,),(int,),(int,),(int,),(float,),(float,type(None)),(int,),(int,),(int,)),
 numeric.IIDMeanInterval:((float,),(float,),(float,)),
 numeric.NumericProfitLossSummary:((numeric.NumericSampleSummary,),(float,),(float,),(numeric.ProfitFactorObservation,),(float,),(int,)),
 numeric.NumericTradeObservation:((int,float),(int,float),(int,float),(int,float,type(None)),(int,float,type(None)),(int,float,type(None)),(int,type(None))),
 numeric.NumericOptionalSummary:((int,),(float,),(float,type(None))),
 numeric.NumericTradeSummary:((numeric.NumericProfitLossSummary,),(float,),(float,),(numeric.NumericOptionalSummary,),(numeric.NumericOptionalSummary,),(numeric.NumericOptionalSummary,),(numeric.NumericOptionalSummary,)),
}

def _graph(value):
    """One global resource budget for all exact records, including unused fields."""
    nodes=0;budget=8388608
    def charge(size):
        nonlocal budget
        budget-=size
        if budget<0:raise ValueError('REPORT_LITERAL_BYTE_BUDGET')
    def copy(item,depth):
        nonlocal nodes
        nodes+=1
        if nodes>250000 or depth>24:raise ValueError('REPORT_LITERAL_GRAPH_BUDGET')
        kind=type(item)
        if item is None or kind is bool:charge(5);return item
        if kind is int:
            if not -(2**53)<=item<=2**53:raise ValueError('REPORT_LITERAL_INTEGER_BUDGET')
            charge(18);return item
        if kind is float:
            if not math.isfinite(item):raise ValueError('REPORT_FINITE_NUMBER_REQUIRED')
            charge(24);return item
        if kind is str:
            if len(item)>65536:raise ValueError('REPORT_LITERAL_STRING_BUDGET')
            charge(len(json.dumps(item,ensure_ascii=True)));return item
        if kind is Decimal:evaluation._decimal(item);charge(196);return item
        if kind is datetime:
            if item.tzinfo is not timezone.utc:raise ValueError('REPORT_EXACT_UTC_MODELED_TIME')
            charge(64);return item
        if any(kind is enum for enum in _ENUMS):charge(128);return item
        if any(kind is record for record in _RECORDS):
            pairs=tuple((f.name,copy(getattr(item,f.name),depth+1)) for f in fields(kind))
            clone=object.__new__(kind)
            for name,leaf in pairs:
                if name in ('execution_authority','trading_authorized','point_in_time_qualified','out_of_sample_qualified') and leaf is not False:raise ValueError('REPORT_UNQUALIFIED_RECORD_REQUIRED')
                if name=='source_authentication' and (type(leaf) is not str or leaf!='NOT_EVALUATED'):raise ValueError('REPORT_UNAUTHENTICATED_RECORD_REQUIRED')
                object.__setattr__(clone,name,leaf)
            return clone
        if any(kind is record for record in _NUMERIC):
            if len(item)!=len(kind._fields):raise ValueError('REPORT_NUMERIC_RECORD_ARITY')
            captured=tuple(copy(leaf,depth+1) for leaf in tuple(item))
            if any(not any(type(leaf) is allowed for allowed in expected) for leaf,expected in zip(captured,_NUMERIC_FIELDS[kind])):raise ValueError('REPORT_EXACT_NUMERIC_FIELD_TYPES')
            return tuple.__new__(kind,captured)
        if kind is MappingProxyType:
            referents=gc.get_referents(item)
            if len(referents)!=1 or type(referents[0]) is not dict:raise ValueError('REPORT_LITERAL_PROXY_REQUIRED')
            item=referents[0];kind=dict
        if kind is dict:
            if len(item)>512 or any(type(key) is not str for key in item):raise ValueError('REPORT_LITERAL_MAP_KEYS_REQUIRED')
            charge(2+len(item)*2)
            return MappingProxyType({copy(key,depth+1):copy(leaf,depth+1) for key,leaf in tuple(item.items())})
        if kind is tuple or kind is list:
            if len(item)>4096:raise ValueError('REPORT_LITERAL_ARRAY_BUDGET')
            charge(2+len(item));return tuple(copy(leaf,depth+1) for leaf in tuple(item))
        raise ValueError('REPORT_EXACT_LITERAL_GRAPH_REQUIRED')
    return copy(value,0)

def _encoded(value):
    kind=type(value)
    if kind is Decimal:return {'decimal':str(value)}
    if kind is datetime:return {'modeled_utc':value.isoformat()}
    if any(kind is enum for enum in _ENUMS):return {'enum':kind.__name__,'value':value.value}
    if any(kind is record for record in _RECORDS):
        omitted=('declared_volatility','declared_poc_mode') if kind is DeclaredTradeMetadata and value.declared_volatility is None and value.declared_poc_mode is None else ()
        return {'record':kind.__name__,'fields':{f.name:_encoded(getattr(value,f.name)) for f in fields(kind) if f.name not in omitted}}
    if any(kind is record for record in _NUMERIC):return {'numeric_record':kind.__name__,'values':[_encoded(v) for v in value]}
    if kind is MappingProxyType:return {key:_encoded(leaf) for key,leaf in value.items()}
    if kind is tuple:return [_encoded(leaf) for leaf in value]
    return value

def _unit(value):
    return evaluation._text(value,'[A-Za-z0-9_.:/-]{1,32}')

def _instrument_preflight(source,symbol):
    """Literal consistency only: never proof that Paper produced the records."""
    def signal(record):
        if type(record) is not rich.ResearchSignal:raise ValueError('REPORT_TYPED_INSTRUMENT_SIGNAL_REQUIRED')
        observed=evaluation._text(record.symbol,'[A-Z0-9]{2,30}')
        if observed!=symbol:raise ValueError('REPORT_INSTRUMENT_ASSOCIATION')
    def entry(record):
        if type(record) is not rich.ResearchEntry:raise ValueError('REPORT_TYPED_INSTRUMENT_ENTRY_REQUIRED')
        signal(record.signal)
    def outcome(record):
        if type(record) is not evaluation.EvaluationOutcome:raise ValueError('REPORT_TYPED_INSTRUMENT_OUTCOME_REQUIRED')
        signal(record.signal)
        # Check every present execution in both underlying and rich associations,
        # including malformed nonfilled records, before any downstream owner.
        execution=record.execution
        if execution is not None:
            if type(execution) is not SignalExecution or type(execution.fill) is not PaperFill:raise ValueError('REPORT_TYPED_INSTRUMENT_FILL_REQUIRED')
            observed=evaluation._text(execution.fill.symbol,'[A-Z0-9]{2,30}')
            if observed!=symbol:raise ValueError('REPORT_FILL_INSTRUMENT_ASSOCIATION')
    for record in source.entries:entry(record)
    for record in source.evaluation.outcomes:outcome(record)
    for pair in source.outcomes:
        if type(pair) is not rich.EntryEvaluationOutcome:raise ValueError('REPORT_TYPED_INSTRUMENT_PAIR_REQUIRED')
        entry(pair.entry);outcome(pair.outcome)


def _account_pair(source):
    # Structural caller declarations only: an opaque digest cannot attest execution.
    if type(source) is not rich.ResearchEntryEvaluation or type(source.evaluation) is not evaluation.ResearchEvaluation:raise ValueError('REPORT_TYPED_RICH_EVALUATION_REQUIRED')
    version,policy=source.version,source.evaluation.policy
    if type(version) is not str or type(policy) is not str:raise ValueError('REPORT_CLOSED_ACCOUNT_PAIR')
    if version=='research_entry_evaluation.v2' and policy=='CANDLE_INDEX_INDEPENDENT_ACCOUNTS_V1':return False
    if version=='research_entry_evaluation.v3' and policy=='CANDLE_INDEX_INDEPENDENT_SIGNAL_ACCOUNTS_V2':return True
    raise ValueError('REPORT_CLOSED_ACCOUNT_PAIR')

def _admit(source,declarations,amount_unit,cutoff):
    independent=_account_pair(source)
    evaluation._text(source.input_sha256,'[a-f0-9]{64}')
    owner=source.evaluation
    if type(owner) is not evaluation.ResearchEvaluation or type(owner.dataset) is not evaluation.EvaluationDataset:raise ValueError('REPORT_TYPED_EVALUATION_DATASET')
    dataset=owner.dataset;evaluation._text(dataset.source_sha256,'[a-f0-9]{64}');evaluation._text(dataset.symbol,'[A-Z0-9]{2,30}');_unit(dataset.value_unit)
    available,asof=evaluation._clock(dataset.available_from_ms),evaluation._clock(dataset.as_of_ms)
    if available>asof or amount_unit!=dataset.value_unit or not available<=cutoff<=asof:raise ValueError('REPORT_DECLARED_UNIT_CUTOFF_MISMATCH')
    if type(source.entries) is not tuple or len(source.entries)>512 or type(owner.outcomes) is not tuple or type(source.outcomes) is not tuple or len(owner.outcomes)!=len(source.entries) or len(source.outcomes)!=len(source.entries):raise ValueError('REPORT_OUTCOME_CONSERVATION')
    if type(owner.verdict) is not ResearchPatternVerdict or any(type(entry) is not rich.ResearchEntry for entry in source.entries):raise ValueError('REPORT_TYPED_ENTRIES_AND_VERDICT')
    _instrument_preflight(source,dataset.symbol)
    evaluation._text(owner.input_sha256,'[a-f0-9]{64}')
    if type(owner.folds) is not tuple or not 1<=len(owner.folds)<=128 or type(owner.numeric) is not numeric.NumericProfitLossSummary or owner.bootstrap is not None and type(owner.bootstrap) is not numeric.IIDMeanInterval or type(owner.verdict.numeric) is not numeric.NumericFoldSummary or type(owner.verdict.status) is not ScreeningStatus or type(owner.verdict.reasons) is not tuple or any(type(reason) is not str for reason in owner.verdict.reasons):raise ValueError('REPORT_TYPED_NUMERIC_FOLDS_VERDICT')
    previous=None
    for index,fold in enumerate(owner.folds):
        if type(fold) is not evaluation.EvaluationFold or type(fold.index) is not int or fold.index!=index or type(fold.numeric) is not numeric.NumericProfitLossSummary:raise ValueError('REPORT_TYPED_ORDERED_FOLD')
        start,end,test=(evaluation._clock(v) for v in (fold.start_ms,fold.end_ms,fold.test_start_ms))
        if not available<=start<=test<end<=asof or previous is not None and start!=previous:raise ValueError('REPORT_FOLD_CLOCKS')
        previous=end
    pattern=evaluation._text(owner.verdict.pattern,'[a-z0-9_]{1,64}')
    rich._admit(source.entries,pattern)
    by_clock={e.decision_ms:e for e in source.entries};underlying={};pairs={};filled=[]
    for outcome in owner.outcomes:
        if type(outcome) is not evaluation.EvaluationOutcome or type(outcome.signal) is not rich.ResearchSignal or type(outcome.disposition) is not evaluation.EvaluationDisposition:raise ValueError('REPORT_TYPED_OUTCOME')
        if independent and outcome.disposition is evaluation.EvaluationDisposition.POSITION_OCCUPIED:raise ValueError('REPORT_INDEPENDENT_OCCUPANCY_REFUSED')
        clock=evaluation._clock(outcome.signal.decision_ms)
        if clock>cutoff or outcome.known_at_ms is not None and evaluation._clock(outcome.known_at_ms)>cutoff:raise ValueError('REPORT_ALL_OUTCOME_CLOCKS_WITHIN_CUTOFF')
        if outcome.fold_index is not None and (type(outcome.fold_index) is not int or not 0<=outcome.fold_index<len(owner.folds)):raise ValueError('REPORT_LITERAL_OUTCOME_FOLD_INDEX')
        if outcome.disposition is not evaluation.EvaluationDisposition.OUTSIDE_TEST_WINDOW and outcome.fold_index is None:raise ValueError('REPORT_OUTCOME_FOLD_REQUIRED')
        if clock in underlying or clock not in by_clock or outcome.signal!=by_clock[clock].signal:raise ValueError('REPORT_EXACT_SIGNAL_ASSOCIATION')
        underlying[clock]=outcome
    for pair in source.outcomes:
        if type(pair) is not rich.EntryEvaluationOutcome or type(pair.entry) is not rich.ResearchEntry or type(pair.outcome) is not evaluation.EvaluationOutcome:raise ValueError('REPORT_TYPED_ENTRY_OUTCOME')
        clock=evaluation._clock(pair.entry.decision_ms)
        if clock in pairs or clock not in by_clock or _encoded(pair.entry)!=_encoded(by_clock[clock]) or _encoded(pair.outcome)!=_encoded(underlying[clock]):raise ValueError('REPORT_ENTRY_OUTCOME_ASSOCIATION')
        pairs[clock]=pair
    if set(pairs)!=set(by_clock) or set(underlying)!=set(by_clock):raise ValueError('REPORT_OUTCOME_CONSERVATION')
    for clock in sorted(pairs):
        pair=pairs[clock];outcome=pair.outcome
        if outcome.disposition is not evaluation.EvaluationDisposition.FILLED:
            if outcome.execution is not None:raise ValueError('REPORT_NONFILLED_EXECUTION_REFUSED')
            continue
        execution=outcome.execution
        if type(execution) is not SignalExecution or type(execution.fill) is not PaperFill:raise ValueError('REPORT_SOLE_PAPER_EXECUTION_RECORD_REQUIRED')
        fill=execution.fill
        if type(fill.symbol) is not str or fill.symbol!=dataset.symbol or type(fill.side) is not str or fill.side!=pair.entry.signal.side or type(execution.model) is not str or execution.model not in ('OHLC_CONSERVATIVE_NO_TICK_ORDER','OHLC_OPTIMISTIC_NO_TICK_ORDER') or type(execution.tick_ordering) is not str or execution.tick_ordering!='UNKNOWN':raise ValueError('REPORT_MODELED_EXECUTION_ASSOCIATION')
        entry,exit,known=(evaluation._clock(v) for v in (execution.entry_ms,execution.exit_ms,outcome.known_at_ms))
        if not pair.entry.decision_ms<=entry<=exit<=known<=cutoff:raise ValueError('REPORT_FILLED_DEPENDENCY_CLOCK')
        canonical_exit=datetime(1970,1,1,tzinfo=timezone.utc)+timedelta(milliseconds=exit)
        if fill.exit_time!=canonical_exit:raise ValueError('REPORT_FILL_UTC_EXIT_CLOCK_ASSOCIATION')
        for value in (fill.gross,fill.net,fill.fees,fill.entry,fill.exit,execution.quantity):evaluation._decimal(value)
        filled.append(pair)
    if (type(declarations) is not tuple) or len(declarations)>512:raise ValueError('REPORT_DECLARATION_BATCH')
    fills={(p.entry.signal.symbol,p.entry.decision_ms):p for p in filled};metadata={};units={'mae':None,'mfe':None,'r_multiple':None}
    for row in declarations:
        if type(row) is not DeclaredTradeMetadata:raise ValueError('REPORT_TYPED_POSTHOC_DECLARATION')
        symbol=evaluation._text(row.symbol,'[A-Z0-9]{2,30}');clock=evaluation._clock(row.decision_ms);known=evaluation._clock(row.available_at_ms);key=(symbol,clock)
        if key in metadata or key not in fills:raise ValueError('REPORT_DUPLICATE_OR_UNUSED_DECLARATION_KEY')
        if not fills[key].outcome.known_at_ms<=known<=cutoff:raise ValueError('REPORT_POSTHOC_DECLARATION_AVAILABILITY')
        if type(row.availability_basis) is not str or row.availability_basis!='CALLER_DECLARED_POSTHOC' or row.coverage is not None and type(row.coverage) is not CoverageDeclaration:raise ValueError('REPORT_DECLARATION_NOT_COVERAGE_AUTHORITY')
        for label in (row.declared_volatility,row.declared_poc_mode):
            if label is not None and (type(label) is not str or re.fullmatch('[A-Z][A-Z0-9_]{0,63}',label) is None):raise ValueError('REPORT_LITERAL_DECLARED_LABEL_REQUIRED')
        for name in units:
            value=getattr(row,name);unit=getattr(row,name+'_unit')
            if value is None:
                if unit is not None:raise ValueError('REPORT_MISSING_METRIC_UNIT_MUST_BE_NONE')
                continue
            evaluation._decimal(value);unit=_unit(unit)
            if name=='r_multiple' and unit!='DIMENSIONLESS_R_MULTIPLE':raise ValueError('REPORT_DIMENSIONLESS_R_UNIT_REQUIRED')
            if units[name] is not None and units[name]!=unit:raise ValueError('REPORT_MIXED_DECLARED_METRIC_UNITS')
            units[name]=unit
        metadata[key]=row
    return tuple(filled),metadata,ReportUnits(amount_unit,units['mae'],units['mfe'],units['r_multiple'])


def _finite_trade_summary(value):
    if type(value) is not numeric.NumericTradeSummary or type(value.net) is not numeric.NumericProfitLossSummary or type(value.net.numeric) is not numeric.NumericSampleSummary or type(value.net.profit_factor) is not numeric.ProfitFactorObservation:raise ValueError('REPORT_EXACT_NESTED_NUMERIC_SUMMARY')
    sample=value.net.numeric
    for count in (sample.count,sample.positive,sample.negative,value.net.max_consecutive_losses):
        if type(count) is not int or not 0<=count<=4096:raise ValueError('REPORT_LITERAL_NUMERIC_COUNTS')
    for amount in (sample.total,sample.mean,sample.positive_fraction,value.net.gross_profit,value.net.gross_loss,value.net.max_drawdown,value.gross_pnl_total,value.fees_total):
        if type(amount) is not float or not math.isfinite(amount):raise ValueError('REPORT_FINITE_FLOAT_SUMMARY')
    factor=value.net.profit_factor
    if type(factor.kind) is not str or factor.kind not in ('FINITE','NO_LOSSES') or (factor.value is not None if factor.kind=='NO_LOSSES' else type(factor.value) is not float or not math.isfinite(factor.value)):raise ValueError('REPORT_CLOSED_PROFIT_FACTOR')
    for optional in (value.mae,value.mfe,value.r_multiple,value.holding_ms):
        if type(optional) is not numeric.NumericOptionalSummary or type(optional.count) is not int or not 0<=optional.count<=4096 or type(optional.total) is not float or not math.isfinite(optional.total):raise ValueError('REPORT_TYPED_OPTIONAL_SUMMARY')
        if optional.count==0:
            if optional.mean is not None:raise ValueError('REPORT_MISSING_MEAN_NOT_ZERO')
        elif type(optional.mean) is not float or not math.isfinite(optional.mean):raise ValueError('REPORT_FINITE_OPTIONAL_MEAN')
    return value

def build_research_report(source,trade_metadata=(),*,value_unit,report_as_of_ms=None,metadata=None):
    # Capture ALL records/declarations/unused context/policies before admission
    # or the first Math projection/summary callback. No caller graph remains live.
    source,declarations,value_unit,cutoff,control=_graph((source,trade_metadata,value_unit,report_as_of_ms,{} if metadata is None else metadata))
    _unit(value_unit)
    if type(control) is not MappingProxyType:raise ValueError('REPORT_LITERAL_CONTROL_METADATA')
    if type(source) is not rich.ResearchEntryEvaluation or type(source.evaluation) is not evaluation.ResearchEvaluation or type(source.evaluation.dataset) is not evaluation.EvaluationDataset:raise ValueError('REPORT_TYPED_RICH_EVALUATION_REQUIRED')
    independent=_account_pair(source)
    cutoff=source.evaluation.dataset.as_of_ms if cutoff is None else cutoff;evaluation._clock(cutoff)
    filled,declared,units=_admit(source,declarations,value_unit,cutoff)
    labeled=any(row.declared_volatility is not None or row.declared_poc_mode is not None for row in declarations)
    input_schema=('terminan.research-report.inputs.independent-signals.declared-labels.v1' if independent else 'terminan.research-report.inputs.declared-labels.v1') if labeled else ('terminan.research-report.inputs.v2' if independent else 'terminan.research-report.inputs.v1')
    report_schema=('terminan.research-performance-report.independent-signals.declared-labels.v1' if independent else 'terminan.research-performance-report.declared-labels.v1') if labeled else ('terminan.research-performance-report.independent-signals.v2' if independent else 'terminan.research-performance-report.v1')
    if type(numeric.SCREENING_NUMERIC_ABI) is not str or numeric.SCREENING_NUMERIC_ABI!='math.numeric.screening.ordered-binary64.v1' or numeric.NumericTradeObservation._fields!=('gross_pnl','net_pnl','fees','mae','mfe','r_multiple','holding_ms'):raise RuntimeError('REPORT_UNSUPPORTED_MATH_ABI')
    import market_math as execution_owner
    predicate=getattr(execution_owner,'paper_execution_values_valid',None)
    if not callable(predicate):raise RuntimeError('REPORT_EXECUTION_DOMAIN_MATH_API_REQUIRED')
    # All literal records, symbols, clocks, declarations and units are admitted
    # before the first financial-domain callback; no projection happens until
    # every filled declaration has passed the sole canonical Math predicate.
    for pair in filled:
        execution=pair.outcome.execution;fill=execution.fill
        if predicate(fill.entry,fill.exit,execution.quantity,fill.fees) is not True:raise ValueError('REPORT_MATH_EXECUTION_DOMAIN_REFUSED')
    canonical=json.dumps({'schema':input_schema,'evaluation':_encoded(source),'declarations':_encoded(tuple(sorted(declarations,key=lambda row:(row.symbol,row.decision_ms)))),'value_unit':value_unit,'report_as_of_ms':cutoff,'metadata':_encoded(control),'math_abi':'math.numeric.screening.ordered-binary64.v1/declared-trade-summary.v1','numeric_policy':'DECIMAL_TO_BINARY64_V1_ORDERED_DESCRIPTIVE_NOT_LEDGER_ACCOUNTING','holding_basis':'MODELED_BAR_START_DURATION','coverage_basis':'CALLER_DECLARATIONS_ONLY','execution_basis':'CALLER_DECLARED_INDEPENDENT_HYPOTHESES_SIGNAL_ORDER_NOT_PORTFOLIO_NOT_REEXECUTED' if independent else 'CALLER_SUPPLIED_MODELED_EXECUTIONS_NOT_REEXECUTED','execution_domain_policy':'MATH_PAPER_EXECUTION_VALUES_V1_DECLARATIONS_ONLY'},sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
    if len(canonical)>8388608:raise ValueError('REPORT_CANONICAL_BYTE_BUDGET')
    trades=[];observations=[]
    # One explicit owner conversion per complete scalar batch. No PnL summation
    # or excursion estimate exists in Term; exact ledger amounts are retained.
    amounts=tuple(value for pair in filled for value in (pair.outcome.execution.fill.gross,pair.outcome.execution.fill.net,pair.outcome.execution.fill.fees))
    def project(values):
        result=numeric.project_decimal_observations(values)
        if type(result) is not tuple or len(result)!=len(values) or any(type(value) is not float or not math.isfinite(value) for value in result):raise ValueError('REPORT_EXACT_FINITE_PROJECTION')
        return result
    projected=project(amounts)
    optional_values=tuple(getattr(declared[key],name) for key in declared for name in ('mae','mfe','r_multiple') if getattr(declared[key],name) is not None)
    optional_projected=iter(project(optional_values));optional={}
    for key,row in declared.items():optional[key]=tuple(None if getattr(row,name) is None else next(optional_projected) for name in ('mae','mfe','r_multiple'))
    for index,pair in enumerate(filled):
        execution=pair.outcome.execution;fill=execution.fill;key=(pair.entry.signal.symbol,pair.entry.decision_ms);duration=execution.exit_ms-execution.entry_ms;row=declared.get(key)
        trades.append(ReportTrade(key,pair,fill.gross,fill.net,fill.fees,execution.entry_ms,execution.exit_ms,duration,row))
        observations.append(numeric.NumericTradeObservation(*projected[index*3:index*3+3],*optional.get(key,(None,None,None)),duration))
    trades=tuple(trades);observations=tuple(observations)
    def summary(indices):
        result=numeric.numeric_trade_summary(tuple(observations[i] for i in indices))
        if type(result) is not numeric.NumericTradeSummary:raise ValueError('REPORT_EXACT_MATH_TRADE_SUMMARY')
        return _finite_trade_summary(_graph(result)) # Closed exact finite numeric output.
    def volatility(indices):
        groups={}
        for index in indices:
            regime=trades[index].outcome.entry.evidence.volatility_regime;label=None if regime is None else regime.value
            groups.setdefault(label,[]).append(index)
        return tuple(VolatilityReportPartition(label,tuple(trades[i].identity for i in groups[label]),summary(groups[label])) for label in sorted(groups,key=lambda v:(v is None,v or '')))
    all_indices=tuple(range(len(trades)));partitions=[]
    for label in CoverageDeclaration:
        indices=tuple(i for i,t in enumerate(trades) if (CoverageDeclaration.UNCLASSIFIED if t.declaration is None or t.declaration.coverage is None else t.declaration.coverage) is label)
        partitions.append(CoverageReportPartition(label,tuple(trades[i].identity for i in indices),summary(indices),volatility(indices)))
    partition_ids=tuple(identity for part in partitions for identity in part.trade_ids)
    if len(partition_ids)!=len(trades) or set(partition_ids)!={t.identity for t in trades}:raise ValueError('REPORT_COVERAGE_TRADE_CONSERVATION')
    return ResearchPerformanceReport(hashlib.sha256(canonical).hexdigest(),source,cutoff,units,control,trades,summary(all_indices),tuple(partitions),volatility(all_indices),schema=report_schema,**({'execution_basis':'CALLER_DECLARED_INDEPENDENT_HYPOTHESES_SIGNAL_ORDER_NOT_PORTFOLIO_NOT_REEXECUTED'} if independent else {}))

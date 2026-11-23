"""Declared research screening policy; all numerical summaries belong to Math.

These are caller-supplied fold metrics, not proof of out-of-sample fitting,
source authenticity, execution admission or a profitable trading strategy.
"""
from dataclasses import dataclass,field
from enum import Enum
from history_statistics import NumericFoldSummary,NumericSampleSummary
from .strategy_catalog import research_strategy,StrategyAvailability

class ScreeningStatus(str,Enum):
    KEEP='KEEP'
    REJECT='REJECT'
    NEEDS_MORE_DATA='NEEDS_MORE_DATA'
@dataclass(frozen=True,slots=True)
class ResearchPatternVerdict:
    pattern:str
    status:ScreeningStatus
    numeric:NumericFoldSummary
    reasons:tuple[str,...]
    numeric_policy:str=field(default='ORDERED_BINARY64_V1',init=False)
    factor_policy:str=field(default='LEGACY_LT_1E100_V1',init=False)
    source_authentication:str=field(default='NOT_EVALUATED',init=False)
    execution_authority:bool=field(default=False,init=False)
    trading_authorized:bool=field(default=False,init=False)

def screen_research_pattern(pattern,fold_metrics,*,min_folds=3,min_samples=60,
                            min_profitable_fraction=.60,min_expectancy=0.0,
                            min_profit_factor=1.05,max_loss_fold_fraction=.50):
    import market_math as domain
    from history_statistics import numeric_fold_summary
    definition=research_strategy(pattern)
    if definition.availability is not StrategyAvailability.RESEARCH_GENERATOR:
        raise ValueError('SCREENING_RESEARCH_GENERATOR_REQUIRED')
    if (type(fold_metrics) is not tuple and type(fold_metrics) is not list) or len(fold_metrics)>128:
        raise ValueError('SCREENING_LITERAL_FOLD_BATCH_REQUIRED')
    rows=tuple(fold_metrics)
    if type(min_folds) is not int or not 1<=min_folds<=128 or type(min_samples) is not int or not 0<=min_samples<=4096:
        raise ValueError('SCREENING_BOUNDED_COUNT_POLICY_REQUIRED')
    for value in (min_profitable_fraction,max_loss_fold_fraction):
        if domain.lossless_nonnegative_binary64_valid(value) is not True or value>1:
            raise ValueError('SCREENING_FRACTION_POLICY_REQUIRED')
    if domain.lossless_binary64_valid(min_expectancy) is not True or domain.lossless_nonnegative_binary64_valid(min_profit_factor) is not True:
        raise ValueError('SCREENING_NUMERIC_THRESHOLD_REQUIRED')
    summary=numeric_fold_summary(rows,min_expectancy=min_expectancy,min_profit_factor=min_profit_factor,factor_policy='LEGACY_LT_1E100_V1')
    if type(summary) is not NumericFoldSummary:raise ValueError('SCREENING_MATH_FOLD_RECORD_REQUIRED')
    reasons=[]
    if summary.folds<min_folds:reasons.append('INSUFFICIENT_FOLDS')
    if summary.samples<min_samples:reasons.append('INSUFFICIENT_SAMPLES')
    if summary.folds and summary.profitable_fraction<min_profitable_fraction:reasons.append('UNSTABLE_OOS_EDGE')
    if summary.folds and summary.losing_fraction>max_loss_fold_fraction:reasons.append('MAJORITY_LOSS_MAKING')
    if summary.mean_expectancy<=min_expectancy:reasons.append('NON_POSITIVE_EXPECTANCY')
    # Legacy policy compares an absent eligible PF mean against its zero
    # baseline. Preserve that threshold behavior while reporting None honestly.
    if (summary.mean_profit_factor is None and min_profit_factor>0) or (summary.mean_profit_factor is not None and summary.mean_profit_factor<min_profit_factor):reasons.append('LOW_PROFIT_FACTOR')
    status=ScreeningStatus.REJECT if any(reason in reasons for reason in ('MAJORITY_LOSS_MAKING','NON_POSITIVE_EXPECTANCY','LOW_PROFIT_FACTOR')) else (ScreeningStatus.NEEDS_MORE_DATA if reasons else ScreeningStatus.KEEP)
    return ResearchPatternVerdict(definition.id,status,summary,tuple(reasons))

@dataclass(frozen=True,slots=True)
class SegmentObservation:
    net_value:int|float
    labels:tuple[tuple[str,str],...]
@dataclass(frozen=True,slots=True)
class ResearchSegmentSummary:
    dimension:str
    label:str
    value_unit:str
    numeric:NumericSampleSummary
    availability_basis:str=field(default='CALLER_SUPPLIED_AGGREGATE',init=False)
    source_authentication:str=field(default='NOT_EVALUATED',init=False)
    execution_authority:bool=field(default=False,init=False)
    trading_authorized:bool=field(default=False,init=False)
_DIMENSIONS=('volatility_regime','symbol','level_kind')

def summarize_research_segments(observations,*,value_unit,dimensions=_DIMENSIONS):
    import market_math as domain
    from history_statistics import numeric_sample_summary
    if (type(observations) is not tuple and type(observations) is not list) or len(observations)>4096:
        raise ValueError('SCREENING_LITERAL_OBSERVATION_BATCH_REQUIRED')
    if type(dimensions) is not tuple or not 1<=len(dimensions)<=3 or any(type(key) is not str or key not in _DIMENSIONS for key in dimensions) or len(set(dimensions))!=len(dimensions):
        raise ValueError('SCREENING_CLOSED_DIMENSIONS_REQUIRED')
    if type(value_unit) is not str or not 1<=len(value_unit)<=32 or not value_unit.isascii() or not value_unit.isprintable():
        raise ValueError('SCREENING_DECLARED_VALUE_UNIT_REQUIRED')
    # Snapshot every numeric and metadata leaf before the FIRST Math call.
    captured=[]
    for row in tuple(observations):
        if type(row) is not SegmentObservation:raise ValueError('SCREENING_EXACT_SEGMENT_OBSERVATION_REQUIRED')
        number=row.net_value;labels=row.labels
        if type(labels) is not tuple or len(labels)>3:raise ValueError('SCREENING_LITERAL_LABELS_REQUIRED')
        detached={}
        for pair in labels:
            if type(pair) is not tuple or len(pair)!=2:raise ValueError('SCREENING_LITERAL_LABEL_PAIR_REQUIRED')
            key,label=pair
            if type(key) is not str or key not in _DIMENSIONS or key in detached or type(label) is not str or not 1<=len(label)<=128 or not label.isascii() or not label.isprintable():
                raise ValueError('SCREENING_CLOSED_LITERAL_LABEL_REQUIRED')
            detached[key]=label
        captured.append((number,detached))
    for number,_ in captured:
        if domain.lossless_binary64_valid(number) is not True:raise ValueError('SCREENING_LITERAL_FINITE_NET_VALUE_REQUIRED')
    out=[]
    for dimension in dimensions:
        groups={}
        for number,labels in captured:groups.setdefault(labels.get(dimension,'UNKNOWN'),[]).append(number)
        for label in sorted(groups):
            summary=numeric_sample_summary(groups[label])
            if type(summary) is not NumericSampleSummary:raise ValueError('SCREENING_MATH_SAMPLE_RECORD_REQUIRED')
            out.append(ResearchSegmentSummary(dimension,label,value_unit,summary))
    return tuple(out)

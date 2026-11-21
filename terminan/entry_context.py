
"""Pure declared entry-context projection, never source or execution authority.

ProfileSummary carries a caller's finite binary64 presentation summary. It does
not calculate a profile, validate a distribution, infer availability, or attest
that a supplied value was historically observable. Control metadata uses the
existing bounded literal JSON codec (no float-valued research metrics).
"""
from dataclasses import dataclass,field
from enum import Enum
import json
from .volatility import VolatilityMetrics,VolatilityRegime
from .bounded_json import load_bounded_json

_MAX_CLOCK=2**53-1
_METRICS=('atr_fraction','realized_volatility','parkinson_volatility','range_fraction',
          'volume_ratio','turnover_ratio','atr_percentile')
_PROFILE_VALUES=('poc','value_area_high','value_area_low','value_area_width')

def _clock(value):
    if type(value) is not int or not 0<=value<=_MAX_CLOCK:
        raise ValueError('ENTRY_CONTEXT_LITERAL_CLOCK_REQUIRED')
    return value

def _number(value):
    from market_compute_api import finite_nonnegative_number_valid
    if ((type(value) is not int and type(value) is not float)
        or (type(value) is int and value.bit_length()>53)
        or not finite_nonnegative_number_valid(value)):
        raise ValueError('ENTRY_CONTEXT_DECLARED_FINITE_NUMBER_REQUIRED')
    return value

class ProfileKind(str,Enum):
    TRADE_DISTRIBUTION='TRADE_DISTRIBUTION'
    CANDLE_PROXY='CANDLE_PROXY'

@dataclass(frozen=True,slots=True)
class ProfileSummary:
    poc:int|float
    value_area_high:int|float
    value_area_low:int|float
    available_at_ms:int
    kind:ProfileKind
    value_area_width:int|float
    availability_basis:str=field(default='CALLER_DECLARED',init=False)
    source_authentication:str=field(default='NOT_EVALUATED',init=False)
    execution_authority:bool=field(default=False,init=False)
    trading_authorized:bool=field(default=False,init=False)

    def __post_init__(self):
        _profile(self)

def _profile(value):
    if type(value) is not ProfileSummary:
        raise ValueError('ENTRY_CONTEXT_PROFILE_TYPE_REQUIRED')
    # Snapshot literal immutable leaves once; subsequent use reads this copy.
    out={name:getattr(value,name) for name in
         (*_PROFILE_VALUES,'available_at_ms','kind','availability_basis',
          'source_authentication','execution_authority','trading_authorized')}
    _clock(out['available_at_ms'])
    for name in _PROFILE_VALUES:_number(out[name])
    if (type(out['kind']) is not ProfileKind
        or type(out['availability_basis']) is not str or out['availability_basis']!='CALLER_DECLARED'
        or type(out['source_authentication']) is not str or out['source_authentication']!='NOT_EVALUATED'
        or out['execution_authority'] is not False or out['trading_authorized'] is not False):
        raise ValueError('ENTRY_CONTEXT_PROFILE_DECLARATION_REQUIRED')
    out['kind']=out['kind'].value
    return out

def _volatility(value):
    if type(value) is not VolatilityMetrics:
        raise ValueError('ENTRY_CONTEXT_VOLATILITY_TYPE_REQUIRED')
    out={name:getattr(value,name) for name in
         (*_METRICS,'event_start_ms','available_at_ms','regime','version',
          'availability_basis','source_authentication','execution_authority','trading_authorized')}
    _clock(out['event_start_ms']);_clock(out['available_at_ms'])
    if out['available_at_ms']<out['event_start_ms']:
        raise ValueError('ENTRY_CONTEXT_DECLARED_CLOCK_ORDER_REQUIRED')
    for name in _METRICS:_number(out[name])
    if (type(out['regime']) is not VolatilityRegime
        or type(out['version']) is not str or not 1<=len(out['version'])<=128 or not out['version'].isascii()
        or type(out['availability_basis']) is not str or out['availability_basis']!='CALLER_DECLARED_PREFIX_MAX'
        or type(out['source_authentication']) is not str or out['source_authentication']!='NOT_EVALUATED'
        or out['execution_authority'] is not False or out['trading_authorized'] is not False):
        raise ValueError('ENTRY_CONTEXT_VOLATILITY_DECLARATION_REQUIRED')
    out['regime']=out['regime'].value
    return out

def _rows(values,project):
    if (type(values) is not tuple and type(values) is not list) or len(values)>512:
        raise ValueError('ENTRY_CONTEXT_BOUNDED_LITERAL_ROWS_REQUIRED')
    snapshot=tuple(values)
    return tuple(project(value) for value in snapshot)

def _latest(rows,decision,*,volatility):
    seen={};eligible=[]
    for row in rows:
        key=(row['available_at_ms'],row['event_start_ms'] if volatility else row['available_at_ms'])
        signature=tuple((name,type(value),value) for name,value in row.items())
        if key in seen and seen[key]!=signature:
            raise ValueError('ENTRY_CONTEXT_AMBIGUOUS_IDENTITY')
        seen[key]=signature
        if row['available_at_ms']<=decision:eligible.append((key,row))
    return max(eligible,key=lambda item:item[0])[1] if eligible else None

def _metadata(value):
    if type(value) is not dict or len(value)>32:
        raise ValueError('ENTRY_CONTEXT_BOUNDED_LITERAL_METADATA_REQUIRED')
    count=0
    def copy(item,depth):
        nonlocal count
        count+=1
        if count>512 or depth>8:raise ValueError('ENTRY_CONTEXT_METADATA_BUDGET')
        if item is None or type(item) is bool:return item
        if type(item) is int:
            if item.bit_length()>53:raise ValueError('ENTRY_CONTEXT_METADATA_INTEGER_BUDGET')
            return item
        if type(item) is str:
            if len(item)>1536:raise ValueError('ENTRY_CONTEXT_METADATA_STRING_BUDGET')
            return item
        if type(item) is list:
            if len(item)>200:raise ValueError('ENTRY_CONTEXT_METADATA_ARRAY_BUDGET')
            return [copy(child,depth+1) for child in item]
        if type(item) is dict:
            if len(item)>32:raise ValueError('ENTRY_CONTEXT_METADATA_MAP_BUDGET')
            if any(type(key) is not str or not 1<=len(key)<=64 for key in item):
                raise ValueError('ENTRY_CONTEXT_METADATA_KEY_REQUIRED')
            return {key:copy(child,depth+1) for key,child in item.items()}
        raise ValueError('ENTRY_CONTEXT_LITERAL_METADATA_REQUIRED')
    detached=copy(value,0)
    try:raw=json.dumps(detached,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
    except (ValueError,UnicodeError,RecursionError):
        raise ValueError('ENTRY_CONTEXT_METADATA_ENCODING') from None
    return load_bounded_json(raw,max_bytes=65536)

def build_entry_context(*,decision_ms,metadata,volatility=(),profiles=()):
    """Select latest explicitly available summaries; retain no caller containers.

    Input summaries, including future ones, are preflighted before selection.
    Missing observations remain None. Unrelated control metadata stays nested;
    even an embedded authority-looking tag cannot grant top-level authority.
    """
    decision=_clock(decision_ms)
    control=_metadata(metadata)
    vols=_rows(volatility,_volatility)
    profs=_rows(profiles,_profile)
    return {'schema':'terminan.entry-context.v1','decision_ms':decision,
            'metadata':control,'volatility':_latest(vols,decision,volatility=True),
            'profile':_latest(profs,decision,volatility=False),
            'source_authentication':'NOT_EVALUATED',
            'execution_authority':False,'trading_authorized':False}

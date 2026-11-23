"""Declared-time price-pattern analysis; numerical detection belongs to Math."""
from dataclasses import dataclass,field
from enum import Enum
_MAX_CLOCK=2**53-1
@dataclass(frozen=True,slots=True)
class PriceRangeObservation:
    event_start_ms:int
    event_end_ms:int
    available_at_ms:int
    high:int|float
    low:int|float
class PricePatternKind(str,Enum):
    HIGH_SWING='HIGH_SWING'
    LOW_SWING='LOW_SWING'
    UPWARD_GAP='UPWARD_GAP'
    DOWNWARD_GAP='DOWNWARD_GAP'
@dataclass(frozen=True,slots=True)
class PricePatternEvent:
    event_start_ms:int
    available_at_ms:int
    kind:PricePatternKind
    low:int|float
    high:int|float
    dependency_start_ms:int
    dependency_end_ms:int
    version:str=field(default='price_structure.v1',init=False)
    availability_basis:str=field(default='CALLER_DECLARED_DEPENDENCY_MAX',init=False)
    source_authentication:str=field(default='NOT_EVALUATED',init=False)
    execution_authority:bool=field(default=False,init=False)
    trading_authorized:bool=field(default=False,init=False)
def _clock(value):
    if type(value) is not int or not 0<=value<=_MAX_CLOCK:
        raise ValueError('PRICE_STRUCTURE_LITERAL_CLOCK_REQUIRED')
    return value

def analyze_price_structure(observations,*,as_of_ms,left=2,right=2):
    """Project Math price patterns using every actual dependency availability.

    Consecutive, uniform explicit start/end clocks are required. No bar end,
    duration or availability is reconstructed. Even future observations are
    preflighted before selection. Results are sorted by availability; numeric
    geometry and confirmation windows are computed only by Math. These caller
    declarations neither authenticate a source nor authorize execution.
    """
    import market_math as owner
    cutoff=_clock(as_of_ms)
    if (type(observations) is not tuple and type(observations) is not list) or len(observations)>4096:
        raise ValueError('PRICE_STRUCTURE_BOUNDED_LITERAL_OBSERVATIONS_REQUIRED')
    snapshots=[];previous_end=None;cadence=None
    for row in tuple(observations):
        if type(row) is not PriceRangeObservation:
            raise ValueError('PRICE_STRUCTURE_LITERAL_OBSERVATION_REQUIRED')
        start,end,available,high,low=(row.event_start_ms,row.event_end_ms,row.available_at_ms,row.high,row.low)
        _clock(start);_clock(end);_clock(available)
        if not start<end<=available:
            raise ValueError('PRICE_STRUCTURE_DECLARED_CLOCK_ORDER_REQUIRED')
        duration=end-start
        if (previous_end is not None and start!=previous_end) or (cadence is not None and duration!=cadence):
            raise ValueError('PRICE_STRUCTURE_CONTIGUOUS_DECLARED_CADENCE_REQUIRED')
        previous_end=end;cadence=duration
        snapshots.append((start,end,available,high,low))
    rows=tuple(snapshots)
    patterns=owner.price_structure_patterns(tuple((row[3],row[4]) for row in rows),left=left,right=right)
    if type(patterns) is not tuple:raise ValueError('PRICE_STRUCTURE_MATH_RECORD_REQUIRED')
    kinds=tuple(PricePatternKind);out=[]
    for pattern in patterns:
        if type(pattern) is not owner.PriceStructurePattern:
            raise ValueError('PRICE_STRUCTURE_MATH_RECORD_REQUIRED')
        if type(pattern.kind) is not int or not 0<=pattern.kind<len(kinds):
            raise ValueError('PRICE_STRUCTURE_MATH_KIND_REQUIRED')
        indices=(pattern.index,pattern.dependency_start,pattern.dependency_stop)
        if any(type(value) is not int for value in indices):
            raise ValueError('PRICE_STRUCTURE_MATH_DEPENDENCY_REQUIRED')
        index,start,stop=indices
        if not 0<=start<=index<stop<=len(rows):
            raise ValueError('PRICE_STRUCTURE_MATH_DEPENDENCY_REQUIRED')
        if (not owner.lossless_nonnegative_binary64_valid(pattern.low)
                or not owner.lossless_nonnegative_binary64_valid(pattern.high) or pattern.low>pattern.high):
            raise ValueError('PRICE_STRUCTURE_MATH_BOUNDS_REQUIRED')
        available=max(row[2] for row in rows[start:stop])
        if available<=cutoff:
            out.append(PricePatternEvent(rows[index][0],available,kinds[pattern.kind],
                       pattern.low,pattern.high,rows[start][0],rows[stop-1][1]))
    return tuple(sorted(out,key=lambda item:(item.available_at_ms,item.event_start_ms,item.kind.value)))

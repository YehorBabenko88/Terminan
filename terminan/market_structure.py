"""Declared-time market structure state; numeric pattern geometry belongs to Math.

OHLC finance policy is stricter than calibration range geometry: positive,
ordered prices only. Declarations do not authenticate feeds or authorize trades.
"""
from bisect import bisect_left,bisect_right,insort
from dataclasses import dataclass,field
from decimal import Decimal
from enum import Enum
from types import MappingProxyType
from .price_structure import PriceRangeObservation,PricePatternKind,analyze_price_structure

_MAX_CLOCK=2**53-1
class MarketTimeframe(str,Enum):
    M1='1m';M3='3m';M5='5m';M15='15m';M30='30m'
    H1='1h';H2='2h';H4='4h';H6='6h';H12='12h';D1='1d'
_DURATIONS=MappingProxyType(dict(zip(tuple(MarketTimeframe),(60000,180000,300000,900000,1800000,3600000,7200000,14400000,21600000,43200000,86400000))))
class MarketDirection(str,Enum):
    BULLISH='bullish';BEARISH='bearish'
class MarketStructureKind(str,Enum):
    HIGH_SWING='high_swing';LOW_SWING='low_swing'
    BULLISH_BOS='bullish_bos';BEARISH_BOS='bearish_bos'
    BULLISH_CHOCH='bullish_choch';BEARISH_CHOCH='bearish_choch'
    BULLISH_LIQUIDITY_SWEEP='bullish_liquidity_sweep';BEARISH_LIQUIDITY_SWEEP='bearish_liquidity_sweep'
    BULLISH_ORDER_BLOCK='bullish_order_block';BEARISH_ORDER_BLOCK='bearish_order_block'
_STRUCTURAL=(MarketStructureKind.BULLISH_BOS,MarketStructureKind.BEARISH_BOS,MarketStructureKind.BULLISH_CHOCH,MarketStructureKind.BEARISH_CHOCH)
_BULLISH=(MarketStructureKind.BULLISH_BOS,MarketStructureKind.BULLISH_CHOCH)
_SWINGS=(MarketStructureKind.HIGH_SWING,MarketStructureKind.LOW_SWING)
_BLOCKS=(MarketStructureKind.BULLISH_ORDER_BLOCK,MarketStructureKind.BEARISH_ORDER_BLOCK)
@dataclass(frozen=True,slots=True)
class OHLCObservation:
    event_start_ms:int
    event_end_ms:int
    available_at_ms:int
    open:int|float
    high:int|float
    low:int|float
    close:int|float
@dataclass(frozen=True,slots=True)
class MarketStructureReference:
    event_start_ms:int
    event_end_ms:int
    available_at_ms:int
@dataclass(frozen=True,slots=True)
class MarketStructureEvent:
    event_start_ms:int
    event_end_ms:int
    available_at_ms:int
    source_available_at_ms:int
    kind:MarketStructureKind
    timeframe:MarketTimeframe
    level:int|float
    low:int|float
    high:int|float
    swing_reference:MarketStructureReference
    trigger_reference:MarketStructureReference|None
    version:str=field(default='market_structure.v1',init=False)
    availability_basis:str=field(default='CALLER_DECLARED_CAUSAL_DEPENDENCIES',init=False)
    source_authentication:str=field(default='NOT_EVALUATED',init=False)
    execution_authority:bool=field(default=False,init=False)
    trading_authorized:bool=field(default=False,init=False)
@dataclass(frozen=True,slots=True)
class MarketBiasObservation:
    direction:MarketDirection
    timeframe:MarketTimeframe
    as_of_ms:int
    evidence:MarketStructureEvent
    source_authentication:str=field(default='NOT_EVALUATED',init=False)
    execution_authority:bool=field(default=False,init=False)
    trading_authorized:bool=field(default=False,init=False)
@dataclass(frozen=True,slots=True)
class HigherTimeframeAlignment:
    entry_timeframe:MarketTimeframe
    bias_timeframe:MarketTimeframe
    direction:MarketDirection
    as_of_ms:int
    aligned:bool
    bias:MarketBiasObservation|None
    source_authentication:str=field(default='NOT_EVALUATED',init=False)
    execution_authority:bool=field(default=False,init=False)
    trading_authorized:bool=field(default=False,init=False)

def _clock(value):
    if type(value) is not int or not 0<=value<=_MAX_CLOCK:raise ValueError('MARKET_STRUCTURE_LITERAL_CLOCK_REQUIRED')
    return value

def _timeframe(value):
    if type(value) is not MarketTimeframe:raise ValueError('MARKET_STRUCTURE_EXPLICIT_TIMEFRAME_REQUIRED')
    return value

def _window(left,right):
    if type(left) is not int or type(right) is not int or not 1<=left<=64 or not 1<=right<=64:raise ValueError('MARKET_STRUCTURE_LITERAL_WINDOW_REQUIRED')

def _snapshot(observations,timeframe):
    if (type(observations) is not tuple and type(observations) is not list) or len(observations)>4096:raise ValueError('MARKET_STRUCTURE_BOUNDED_LITERAL_OBSERVATIONS_REQUIRED')
    rows=[];previous_end=None
    for item in tuple(observations):
        if type(item) is not OHLCObservation:raise ValueError('MARKET_STRUCTURE_LITERAL_OHLC_REQUIRED')
        row=(item.event_start_ms,item.event_end_ms,item.available_at_ms,item.open,item.high,item.low,item.close)
        start,end,available=row[:3]
        _clock(start);_clock(end);_clock(available)
        if not start<end<=available:raise ValueError('MARKET_STRUCTURE_DECLARED_CLOCK_ORDER_REQUIRED')
        if end-start!=_DURATIONS[timeframe] or (previous_end is not None and start!=previous_end):raise ValueError('MARKET_STRUCTURE_DECLARED_TIMEFRAME_CADENCE_REQUIRED')
        previous_end=end;rows.append(row)
    return tuple(rows)

def _finance_prices(rows):
    import market_math as owner
    for row in rows:
        prices=(row[3],row[4],row[5],row[6])
        if any(owner.lossless_nonnegative_binary64_valid(value) is not True for value in prices):raise ValueError('MARKET_STRUCTURE_LOSSLESS_LITERAL_PRICES_REQUIRED')
        # Decimal spelling is DTO presentation for the existing policy predicate;
        # no arithmetic, inferred precision or conversion of output payloads.
        if owner.candle_ohlcv_valid(*(Decimal(str(value)) for value in prices),Decimal(0)) is not True:raise ValueError('MARKET_STRUCTURE_POSITIVE_ORDERED_OHLC_REQUIRED')

def _reference(row):return MarketStructureReference(*row[:3])
def _event(row,available,kind,timeframe,level,low,high,swing,trigger):
    return MarketStructureEvent(row[0],row[1],available,row[2],kind,timeframe,level,low,high,swing,trigger)

def _analyze(rows,*,cutoff,timeframe,left,right):
    _finance_prices(rows)
    patterns=analyze_price_structure(tuple(PriceRangeObservation(r[0],r[1],r[2],r[4],r[5]) for r in rows),as_of_ms=cutoff,left=left,right=right)
    by_start={row[0]:row for row in rows};swings=[]
    for pattern in patterns:
        if pattern.kind not in (PricePatternKind.HIGH_SWING,PricePatternKind.LOW_SWING):continue
        row=by_start[pattern.event_start_ms]
        kind=MarketStructureKind.HIGH_SWING if pattern.kind is PricePatternKind.HIGH_SWING else MarketStructureKind.LOW_SWING
        ref=MarketStructureReference(row[0],row[1],pattern.available_at_ms)
        swings.append(_event(row,pattern.available_at_ms,kind,timeframe,pattern.low,pattern.low,pattern.high,ref,None))
    # Prefix maxima answer conservative temporal visibility independently of
    # decision order; delayed decisions can move backwards in event time.
    visible_indices={}
    for kind in _SWINGS:
        ordered=sorted((s for s in swings if s.kind is kind),key=lambda s:(s.available_at_ms,s.event_start_ms))
        clocks=[];latest=[];current=None
        for swing in ordered:
            if current is None or swing.event_start_ms>current.event_start_ms:current=swing
            clocks.append(swing.available_at_ms);latest.append(current)
        visible_indices[kind]=(tuple(clocks),tuple(latest))
    out=list(swings);broken=set();trend=None;opposing_starts={True:[],False:[]}
    for row in sorted((r for r in rows if r[2]<=cutoff),key=lambda r:(r[2],r[0])):
        for high_side in (True,False):
            swing_kind=MarketStructureKind.HIGH_SWING if high_side else MarketStructureKind.LOW_SWING
            clocks,latest=visible_indices[swing_kind];index=bisect_right(clocks,row[0])-1
            if index<0:continue
            swing=latest[index];key=(swing_kind,swing.event_start_ms)
            if key in broken:continue
            level=swing.level;close=row[6]
            breached=close>level if high_side else close<level
            swept=(row[4]>level and close<=level) if high_side else (row[5]<level and close>=level)
            if swept:
                kind=MarketStructureKind.BEARISH_LIQUIDITY_SWEEP if high_side else MarketStructureKind.BULLISH_LIQUIDITY_SWEEP
                out.append(_event(row,row[2],kind,timeframe,level,level,level,swing.swing_reference,_reference(row)))
            elif breached:
                if high_side:
                    kind=MarketStructureKind.BULLISH_CHOCH if trend is MarketDirection.BEARISH else MarketStructureKind.BULLISH_BOS
                    trend=MarketDirection.BULLISH
                else:
                    kind=MarketStructureKind.BEARISH_CHOCH if trend is MarketDirection.BULLISH else MarketStructureKind.BEARISH_BOS
                    trend=MarketDirection.BEARISH
                out.append(_event(row,row[2],kind,timeframe,level,level,level,swing.swing_reference,_reference(row)));broken.add(key)
                candidates=opposing_starts[high_side];index=bisect_left(candidates,row[0])-1
                if index>=0 and candidates[index]>=swing.event_start_ms:
                    prior=by_start[candidates[index]];kind=MarketStructureKind.BULLISH_ORDER_BLOCK if high_side else MarketStructureKind.BEARISH_ORDER_BLOCK
                    out.append(_event(prior,row[2],kind,timeframe,level,prior[5],prior[4],swing.swing_reference,_reference(row)))
        # All preceding decision rows are actually available now. Equal-clock
        # rows with smaller event starts are visited first. Event-time bisection
        # excludes a later-event candle even if that decision arrived earlier.
        if row[6]<row[3]:insort(opposing_starts[True],row[0])
        elif row[6]>row[3]:insort(opposing_starts[False],row[0])
    return tuple(sorted(out,key=lambda e:(e.available_at_ms,e.event_start_ms,e.timeframe.value,e.kind.value)))

def analyze_market_structure(observations,*,as_of_ms,timeframe,left=2,right=2):
    """Analyze detached OHLC declarations; visibility uses known<=trigger start.

    Decisions follow (declared availability,event start), and each latest
    event-time swing breaks once. Opposing order-block candles must precede the
    trigger in event time and already be available at its decision. Sweeps do
    not consume a level. No clock is derived from a start or timeframe label.
    """
    cutoff=_clock(as_of_ms);timeframe=_timeframe(timeframe);_window(left,right)
    rows=_snapshot(observations,timeframe)
    return _analyze(rows,cutoff=cutoff,timeframe=timeframe,left=left,right=right)

def build_multi_timeframe_structure(series,*,as_of_ms,left=2,right=2):
    """Detach every timeframe before any numeric owner call; no partial batch."""
    cutoff=_clock(as_of_ms);_window(left,right)
    if type(series) is not dict or len(series)>len(_DURATIONS):raise ValueError('MARKET_STRUCTURE_LITERAL_TIMEFRAME_MAP_REQUIRED')
    entries=tuple(series.items())
    if any(type(timeframe) is not MarketTimeframe for timeframe,_ in entries):raise ValueError('MARKET_STRUCTURE_EXPLICIT_TIMEFRAME_REQUIRED')
    snapshots=tuple((timeframe,_snapshot(rows,timeframe)) for timeframe,rows in entries)
    out=[]
    for timeframe,rows in snapshots:out.extend(_analyze(rows,cutoff=cutoff,timeframe=timeframe,left=left,right=right))
    return tuple(sorted(out,key=lambda e:(e.available_at_ms,e.event_start_ms,e.timeframe.value,e.kind.value)))

def _reference_snapshot(ref):
    if ref is None:return None
    if type(ref) is not MarketStructureReference:raise ValueError('MARKET_STRUCTURE_LITERAL_REFERENCE_REQUIRED')
    return (ref.event_start_ms,ref.event_end_ms,ref.available_at_ms)

def _check_reference(ref,timeframe):
    if ref is None:raise ValueError('MARKET_STRUCTURE_SWING_REFERENCE_REQUIRED')
    for value in ref:_clock(value)
    if not ref[0]<ref[1]<=ref[2] or ref[1]-ref[0]!=_DURATIONS[timeframe]:raise ValueError('MARKET_STRUCTURE_DECLARED_REFERENCE_REQUIRED')

def _record_event(row):
    return MarketStructureEvent(*row[:9],MarketStructureReference(*row[9]),None if row[10] is None else MarketStructureReference(*row[10]))

def _context_records(events):
    if (type(events) is not tuple and type(events) is not list) or len(events)>400000:raise ValueError('MARKET_STRUCTURE_BOUNDED_LITERAL_EVENTS_REQUIRED')
    snapshots=[]
    for event in tuple(events):
        if type(event) is not MarketStructureEvent:raise ValueError('MARKET_STRUCTURE_LITERAL_EVENT_REQUIRED')
        snapshots.append((event.event_start_ms,event.event_end_ms,event.available_at_ms,event.source_available_at_ms,event.kind,event.timeframe,event.level,event.low,event.high,
            _reference_snapshot(event.swing_reference),_reference_snapshot(event.trigger_reference),event.version,event.availability_basis,event.source_authentication,event.execution_authority,event.trading_authorized))
    import market_math as owner
    records=[]
    for row in snapshots:
        start,end,known,source,kind,timeframe,level,low,high,swing,trigger=row[:11]
        for value in (start,end,known,source):_clock(value)
        _timeframe(timeframe)
        if type(kind) is not MarketStructureKind or not start<end<=source<=known or end-start!=_DURATIONS[timeframe]:raise ValueError('MARKET_STRUCTURE_EVENT_FIELDS_REQUIRED')
        if any(type(value) is not str or value!=expected for value,expected in zip(row[11:14],('market_structure.v1','CALLER_DECLARED_CAUSAL_DEPENDENCIES','NOT_EVALUATED'))) or row[14] is not False or row[15] is not False:raise ValueError('MARKET_STRUCTURE_NO_AUTHORITY_METADATA_REQUIRED')
        if any(owner.lossless_nonnegative_binary64_valid(value) is not True for value in (level,low,high)):raise ValueError('MARKET_STRUCTURE_EVENT_PRICES_REQUIRED')
        if owner.candle_ohlcv_valid(Decimal(str(low)),Decimal(str(high)),Decimal(str(low)),Decimal(str(high)),Decimal(0)) is not True or owner.candle_ohlcv_valid(*(Decimal(str(level)) for _ in range(4)),Decimal(0)) is not True:raise ValueError('MARKET_STRUCTURE_EVENT_PRICES_REQUIRED')
        _check_reference(swing,timeframe)
        if kind in _SWINGS:
            if trigger is not None or swing!=(start,end,known) or not low==high==level:raise ValueError('MARKET_STRUCTURE_SWING_EVIDENCE_REQUIRED')
        else:
            _check_reference(trigger,timeframe)
            if swing[2]>trigger[0] or known!=trigger[2]:raise ValueError('MARKET_STRUCTURE_CONSERVATIVE_TRIGGER_EVIDENCE_REQUIRED')
            if kind in _BLOCKS:
                if not swing[0]<=start<trigger[0]:raise ValueError('MARKET_STRUCTURE_PRIOR_BLOCK_EVIDENCE_REQUIRED')
            elif (start,end,source)!=(trigger[0],trigger[1],trigger[2]) or not low==high==level:raise ValueError('MARKET_STRUCTURE_TRIGGER_EVIDENCE_REQUIRED')
        records.append(row[:11])
    return tuple(records)

class MarketStructureContext:
    """Detached declared event context; alignment is analysis, not admission."""
    __slots__=('_records',)
    def __init__(self,events):self._records=_context_records(events)
    @property
    def events(self):return tuple(_record_event(row) for row in self._records)
    def bias_at(self,as_of_ms,timeframe):
        cutoff=_clock(as_of_ms);timeframe=_timeframe(timeframe)
        visible=[row for row in self._records if row[5] is timeframe and row[2]<=cutoff and row[4] in _STRUCTURAL]
        if not visible:return None
        latest=max(visible,key=lambda row:(row[2],row[0],row[4].value))
        direction=MarketDirection.BULLISH if latest[4] in _BULLISH else MarketDirection.BEARISH
        return MarketBiasObservation(direction,timeframe,cutoff,_record_event(latest))
    def alignment_at(self,as_of_ms,*,entry_timeframe,bias_timeframe,direction):
        cutoff=_clock(as_of_ms);entry_timeframe=_timeframe(entry_timeframe);bias_timeframe=_timeframe(bias_timeframe)
        if type(direction) is not MarketDirection:raise ValueError('MARKET_STRUCTURE_LITERAL_DIRECTION_REQUIRED')
        if _DURATIONS[bias_timeframe]<=_DURATIONS[entry_timeframe]:raise ValueError('MARKET_STRUCTURE_HIGHER_TIMEFRAME_REQUIRED')
        bias=self.bias_at(cutoff,bias_timeframe)
        return HigherTimeframeAlignment(entry_timeframe,bias_timeframe,direction,cutoff,bias is not None and bias.direction is direction,bias)

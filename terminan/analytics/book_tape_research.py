"""Completed-tape research state; every feature/vote is owned by Math.
Packets and source declarations are validated only by the canonical Data SDK.
No SQL/provider, simulator, source authentication or live order authority.
"""
from dataclasses import dataclass
from threading import Lock
from ..causal_inputs import CausalInputCursor
from ..causal_quotes import _decimal_value
from ..causal_replay import SYMBOLS
VERSION='book_tape_research.v2'
@dataclass(frozen=True)
class ResearchBatch:
 packet:dict
 observations:tuple
 changed_channels:tuple
class BookTapeResearch:
 def __init__(self,symbol,*,window=32,min_history=8):
  if type(symbol) is not str or symbol not in SYMBOLS:raise ValueError('explicit canonical research symbol required')
  if type(window) is not int or not 8<=window<=4096 or type(min_history) is not int or not 4<=min_history<=window:raise ValueError('bounded research history required')
  self._symbol=symbol;self._window=window;self._minimum=min_history;self._history=();self._last=None;self._epoch=None;self._cursor=CausalInputCursor(symbol);self._lock=Lock()
 def snapshot(self):
  with self._lock:return dict(symbol=self._symbol,window=self._window,min_history=self._minimum,history=tuple((t,str(p),str(v)) for t,p,v in self._history),last_event_us=self._last,epoch=self._epoch,cursor=self._cursor.snapshot())
 def observe_packet(self,packet,*,expected_request):
  from market_data.paper_inputs import validate_paper_inputs
  from market_math import exact_sum,wall_notional,book_tape_research_metrics
  checked=validate_paper_inputs(packet);q=checked['request']
  if q['symbol']!=self._symbol:raise ValueError('research packet symbol mismatch')
  with self._lock:
   history=list(self._history);last=self._last;epoch=self._epoch;observations=[]
   for row in checked['rows']:
    if row['event_type']!='trade_tape_250ms':continue
    clock=int(row['event_us']);payload=row['payload'];context=payload.get('_producer_connection');current=None if context is None else context['connection_id']
    if last is not None and clock<=last:raise ValueError('replayed or out-of-order completed tape')
    if current!=epoch:history=[]
    epoch=current;last=clock
    common=dict(schema='terminan.analytics.book-tape-observation.v2',version=VERSION,strategy='book_tape_research',symbol=self._symbol,event_us=row['event_us'],row_id=row['id'],row_sha256=row['row_sha256'],available_from_ms=q['as_of_ms'],availability_basis=checked['availability_basis'],point_in_time_availability=checked['point_in_time_availability'],source_authenticity=checked['source_authenticity'],execution_authority=False,trading_authorized=False)
    if current is None:
     history=[];observations.append(dict(common,eligible=False,reason='SOURCE_CONTEXT_UNAVAILABLE'));continue
    def decode(value):
     if type(value) not in (str,int,float):raise ValueError('exact packet numeric scalar required')
     return _decimal_value(str(value))
    close,buy,sell=(decode(payload[key]) for key in ('close','buy_volume','sell_volume'))
    volume=exact_sum((buy,sell));notional=wall_notional(close,volume)
    # This is the actual completed bucket notional, also exposed below. No
    # invented history or fabricated trade is used to validate warmup input.
    if len(history)<self._minimum:
     history.append((clock,close,volume));history=history[-self._window:]
     observations.append(dict(common,eligible=False,reason='warmup',samples=len(history),bucket_notional=str(notional)));continue
    metrics=book_tape_research_metrics(close,buy,sell,tuple((p,v) for _,p,v in history))
    observations.append(dict(common,eligible=True,direction=metrics.signal,decision='PAPER_CANDIDATE' if metrics.signal else 'ABSTAIN',bucket_notional=str(notional),patterns=dict(jbe_proxy=metrics.breakout_long,dbi_proxy=metrics.breakout_short,trend_continuation_long=metrics.trend_long,trend_continuation_short=metrics.trend_short,volume_confirmation=metrics.volume_confirmation,effort_result_anomaly=metrics.effort_anomaly),features=dict(relative_volume=str(metrics.relative_volume),delta_ratio=str(metrics.delta_ratio),base_width_fraction=str(metrics.base_width_fraction),proxy_poc=str(metrics.proxy_poc),proxy_poc_distance=str(metrics.proxy_poc_distance)),data_limitations=['250ms bucket-close profile is not true executed-price VAP','trade bucket lacks intrabar high/low and order-level absorption']))
    history.append((clock,close,volume));history=history[-self._window:]
   # Stage ALL strategy work before the cursor may commit. The private cursor
   # revalidates the detached packet/query; it is never exposed for mutation.
   batch=self._cursor.accept(checked,expected_request=expected_request)
   self._history=tuple(history);self._last=last;self._epoch=epoch
   return ResearchBatch(batch.packet,tuple(observations),batch.changed_channels)

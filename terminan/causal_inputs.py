"""Atomic temporal cursor over the canonical Data-owned paper packet SDK.

No copied wire validator, numeric kernel, SQL reader, provider or authority.
Wire microsecond strings and all Data qualifiers/hashes stay untouched.
"""
from dataclasses import dataclass
from threading import Lock
import re

@dataclass(frozen=True)
class PersistedRowClock:
 id: int
 kind: str
 event_us: int
 ingest_us: int
 row_sha256: str

@dataclass(frozen=True)
class CausalInputBatch:
 packet: dict
 row_clocks: tuple
 changed_channels: tuple

class CausalInputCursor:
 def __init__(self,symbol,*,after_id=0):
  if type(symbol) is not str or len(symbol)>30 or re.fullmatch('[A-Z0-9]{2,30}',symbol) is None or type(after_id) is not int or not 0<=after_id<=2**53-1:raise ValueError('bounded causal cursor required')
  self._symbol=symbol;self._cursor=after_id;self._events={};self._epochs={'book':None,'tape':None};self._book=None;self._lock=Lock()
 def snapshot(self):
  with self._lock:return dict(symbol=self._symbol,cursor=self._cursor,events=dict(self._events),epochs=dict(self._epochs),book=self._book)
 def accept(self,packet,*,expected_request):
  from market_data.paper_inputs import validate_paper_inputs
  checked=validate_paper_inputs(packet);q=checked['request']
  # Derive the closed query shape from the SDK-owned checked request, not a
  # duplicate schema. Refuse bool/int equality and opaque caller operators.
  if type(expected_request) is not dict or len(expected_request)!=len(q) or any(type(key) is not str or key not in q for key in expected_request):raise ValueError('expected source query required')
  if any(type(expected_request[key]) is not type(q[key]) or expected_request[key]!=q[key] for key in q):raise ValueError('source query mismatch')
  with self._lock:
   if q['symbol']!=self._symbol or q['after_id']!=self._cursor:raise ValueError('source cursor mismatch')
   events=dict(self._events);epochs=dict(self._epochs);book=self._book;changed=set();clocks=[]
   for row in checked['rows']:
    kind=row['event_type'];event=int(row['event_us']);ingest=int(row['ingest_us'])
    if kind in events and event<=events[kind]:raise ValueError('source event regression')
    events[kind]=event
    # Funding has independent field provenance; it is not a book connection
    # event and must never erase or replace orderbook sequence watermarks.
    if kind in ('trade_tape_250ms','orderbook_snapshot'):
     channel='tape' if kind=='trade_tape_250ms' else 'book';context=row['payload'].get('_producer_connection');current=None if context is None else context['connection_id']
     if epochs[channel]!=current:
      if epochs[channel] is not None:changed.add(channel)
      if channel=='book':book=None
     epochs[channel]=current
    if kind=='orderbook_snapshot':
     sequence=(row['payload']['sequence'],row['payload']['update_id'])
     if book is not None and any(a<=b for a,b in zip(sequence,book)):raise ValueError('source book sequence regression')
     book=sequence if current is not None else None
    clocks.append(PersistedRowClock(row['id'],kind,event,ingest,row['row_sha256']))
   result=CausalInputBatch(checked,tuple(clocks),tuple(sorted(changed)))
   self._cursor=checked['cursor'];self._events=events;self._epochs=epochs;self._book=book
   return result

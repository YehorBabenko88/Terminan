"""Finite SYNTHETIC_OFFLINE packet-to-paper session; no I/O or publication.
The caller freshness callback is NOT permission or source authentication.
Root retains all provider polling, durable audit/publication, custody and actual
capsule/service admission. No operational constructor is exposed here.
"""
import copy,json,re,time
from dataclasses import dataclass
from hashlib import sha256
from threading import RLock
from .paper_ledger import canonical_json
from .causal_replay import SYMBOLS,digest,label
from .causal_quotes import _clock,_decimal_value
from .causal_account import CausalAccountJournal

@dataclass(frozen=True)
class SessionDescriptor:
 payload_json:bytes
 sha256:str
 def decode(self):
  if sha256(self.payload_json).hexdigest()!=self.sha256:raise ValueError('descriptor integrity mismatch')
  return json.loads(self.payload_json)
def _seal(value):return dict(value,sha256=digest(value))
def _ceil_ms(text):return (int(text)+999)//1000

@dataclass(frozen=True)
class SessionPublication:
 artifact_json:bytes
 sha256:str
 descriptor:SessionDescriptor

class CausalPaperSession:
 def __init__(self,account,*,run_id,strategy_revision,planned_duration_ms,source_max_age_ms,clock_ms=None,min_history=8):
  if type(account) is not CausalAccountJournal:raise ValueError('existing offline account required')
  self.account=account;self._blocked=None;self._ended=False;self._end_reason=None;self._lock=RLock();self._last_clock=0;self._sequence=0;self._pending={}
  self._current();label(run_id)
  if len(run_id)>32 or type(strategy_revision) is not str or re.fullmatch('[a-f0-9]{40}',strategy_revision) is None:raise ValueError('bounded session identity required')
  if type(planned_duration_ms) is not int or not 1<=planned_duration_ms<=3600000 or type(source_max_age_ms) is not int or not account.policy['max_quote_age_ms']<=source_max_age_ms<=3600000:raise ValueError('bounded session window required')
  if type(min_history) is not int or not 4<=min_history<=32:raise ValueError('bounded session warmup required')
  view=account.snapshot()
  if any(r['status'] not in ('DENIED','SETTLED') for r in view['reservations']):raise ValueError('SESSION_RECOVERY_REQUIRED')
  cooldown=account.policy['hold_ms']+account.policy['entry_wait_ms']+account.policy['exit_wait_ms'];forecast=(planned_duration_ms//cooldown+1)*len(SYMBOLS)
  closed=sum(r['status']=='SETTLED' for r in view['reservations'])
  if closed+forecast>200 or len(view['reservations'])+forecast>512 or forecast*7+1>4096:raise ValueError('SESSION_CAPACITY')
  self.run_id=run_id;self.strategy_revision=strategy_revision;self.duration=planned_duration_ms;self.source_max_age=source_max_age_ms;self.cooldown=cooldown;self.forecast=forecast
  self._clock_ms=(lambda:time.time_ns()//1000000) if clock_ms is None else clock_ms
  if not callable(self._clock_ms):raise ValueError('explicit session clock required')
  self.started_ms=self._now();self._current()
  from .analytics.book_tape_research import BookTapeResearch
  self._state={symbol:dict(strategy=BookTapeResearch(symbol,min_history=min_history),cursor=0,book=None,book_row=None,book_context=None,tape_context=None,funding_context=None,funding=None,prefix=(),last_candidate=None,candidates=0,denied=0,closed=0,issue=None,retry=None) for symbol in sorted(SYMBOLS)}
 def _current(self):
  if self._blocked is not None:raise ValueError(self._blocked)
  try:valid=self.account.require_current() is True
  except Exception:valid=False
  if not valid:self._blocked='SOURCE_FRESHNESS_UNAVAILABLE'
  if not valid:raise ValueError(self._blocked)
 def _now(self):
  now=_clock(self._clock_ms())
  if now<self._last_clock:raise ValueError('SESSION_CLOCK_REGRESSION')
  self._last_clock=now;return now
 def _emit(self,kind,symbol,reservation_id,at_ms,detail,*,source_packet_sha256=None):
  self._current()
  if self._sequence>=4096:raise ValueError('SESSION_DESCRIPTOR_CAPACITY')
  value=dict(schema='terminan.paper.session-event.v2',sequence=self._sequence+1,kind=kind,run_id=self.run_id,symbol=symbol,reservation_id=reservation_id,at_ms=at_ms,detail=detail,source_packet_sha256=source_packet_sha256,evidence_class='SYNTHETIC',source_authenticity='NOT_EVALUATED',point_in_time_availability='UNKNOWN',execution_authority=False,trading_authorized=False)
  raw=canonical_json(value)
  if len(raw)>65536:raise ValueError('SESSION_DESCRIPTOR_BYTES')
  self._sequence+=1;return SessionDescriptor(raw,sha256(raw).hexdigest())
 def status(self):
  with self._lock:return dict(schema='terminan.paper.session-status.v2',run_id=self.run_id,state='BLOCKED' if self._blocked else ('WINDOW_ENDED' if self._end_reason=='WINDOW_ENDED' else 'FINISHED') if self._ended else 'OBSERVING',error_code=self._blocked,elapsed_ms=self._last_clock-self.started_ms,planned_duration_ms=self.duration,capacity_forecast_decisions=self.forecast,unresolved_reservations=len(self._pending),descriptor_sequence=self._sequence,routing_state='NON_AUTHORITATIVE_SESSION_CACHE',financial_truth='OWNED_VERIFIED_ARTIFACT_ONLY',source_authenticity='NOT_EVALUATED',point_in_time_availability='UNKNOWN',execution_authority=False,trading_authorized=False,instruments={s:{k:v for k,v in state.items() if k in ('cursor','candidates','denied','closed','issue')} for s,state in self._state.items()})
 def _id(self,record):return record['candidate']['id']
 def _uncertain(self,symbol,reason,now,events):
  old=self._pending.get(symbol)
  if old is None or old['status']=='UNCERTAIN':return
  self._current();ident=self._id(old);self.account.mark_uncertain(ident,reason,now_ms=now);old=copy.deepcopy(old);old.update(status='UNCERTAIN',uncertainty=reason);self._pending[symbol]=old
  events.append(self._emit('UNCERTAIN',symbol,ident,now,dict(reason=reason)))
 def _advance(self,now,events):
  self._current();p=self.account.policy
  for symbol,record in tuple(self._pending.items()):
   if record['status']=='UNCERTAIN':continue
   book=self._state[symbol]['book']
   if book is None or now-book['observed_ms']>p['max_quote_age_ms']:
    self._uncertain(symbol,'SOURCE_GAP',now,events);continue
   if record['status'] in ('RESERVED','DECIDED'):
    decision=record.get('decision') or record['candidate']['signal']
    if now>decision['expires_ms']:self._uncertain(symbol,'QUOTE_TIMEOUT',now,events)
   elif record['status']=='ENTRY_SELECTED':
    entry=record['entry_quote']
    if now>entry['event_ms']+p['hold_ms']+p['exit_wait_ms'] or now+p['exit_wait_ms']>=record['candidate']['funding']['next_ms']:
     self._uncertain(symbol,'QUOTE_TIMEOUT',now,events);continue
    if now>=entry['observed_ms']+p['hold_ms']:
     basis=dict(schema='terminan.paper.close-decision-input.v2',opening_decision_sha256=record['decision']['sha256'],entry_quote_sha256=entry['sha256'],risk_sha256=digest(record['risk_receipt']),hold_ms=p['hold_ms'])
     decision=_seal(dict(receipt_id=self._id(record)+'_close',symbol=symbol,source_id='terminan_paper_close_decision',raw_sha256=digest(basis),decision_ms=now,observed_ms=now,expires_ms=now+p['exit_wait_ms']))
     updated=self.account.record_exit_decision(self._id(record),decision,now_ms=now);self._pending[symbol]=updated;events.append(self._emit('EXIT_DECISION',symbol,self._id(record),now,dict(decision=decision)))
   elif record['status']=='EXIT_DECIDED' and now>record['close_decision']['expires_ms']:self._uncertain(symbol,'QUOTE_TIMEOUT',now,events)
 def advance(self):
  with self._lock:
   self._current()
   if self._ended:return ()
   try:
    now=self._now();events=[];self._advance(now,events)
    if now>=self.started_ms+self.duration:
     self._ended=True;self._end_reason='WINDOW_ENDED';events.append(self._emit('WINDOW_ENDED',None,None,now,dict(qualification='NOT_EVALUATED',unresolved_reservations=len(self._pending))))
    return tuple(events)
   except Exception:
    if self._blocked is None:self._blocked='SESSION_ACCOUNT_REJECTED'
    raise
 def _context(self,symbol,row,now,events):
  state=self._state[symbol];context=row['payload'].get('_producer_connection');kind=row['event_type']
  if kind=='derivatives_ticker':
   # Funding provenance is independent: never clear/replace the actual book
   # connection or its quote/sequence baseline because of a ticker row.
   current=None if context is None else context['connection_id'];previous=state['funding_context']
   if current is None or previous is not None and current!=previous:
    state['funding']=None;state['issue']='FUNDING_CONTEXT_UNAVAILABLE' if current is None else 'FUNDING_CONNECTION_CHANGED';self._uncertain(symbol,'SOURCE_GAP',now,events)
   state['funding_context']=current;return current
  channel='tape_context' if kind=='trade_tape_250ms' else 'book_context'
  if context is None:
   state['issue']='PRODUCER_CONTEXT_UNAVAILABLE';self._uncertain(symbol,'SOURCE_GAP',now,events);state['book']=None;state['funding']=None;state[channel]=None;return None
  current=context['connection_id'];previous=state[channel]
  if previous is not None and current!=previous:
   self._uncertain(symbol,'SOURCE_GAP',now,events);state['book']=None;state['funding']=None;state['prefix']=();state['issue']='LOCAL_CONNECTION_CHANGED'
  state[channel]=current;return current
 def _funding_values(self,payload):
  import market_math
  convert=getattr(market_math,'exact_scaled_integer',None)
  if not callable(convert):return None
  try:
   interval=convert(_decimal_value(str(payload['funding_interval_hour'])),3600000);next_ms=convert(_decimal_value(str(payload['next_funding_time'])),1)
   if not 0<interval<=86400000 or next_ms<interval:return None
   return interval,next_ms
  except (KeyError,ValueError,TypeError):return None
 def _funding(self,symbol,now):
  from market_data.paper_inputs import paper_funding_at
  import market_math
  saved=self._state[symbol]['funding']
  if saved is None:return None
  packet,row=saved
  try:
   assessment=paper_funding_at(packet,row_id=row['id'],now_ms=now)
   expected=dict(funding_status='KNOWN_SOURCE_FIELDS',evaluated_at_ms=now,source_request_sha256=digest(packet['request']),row_sha256=row['row_sha256'])
   if assessment!=expected or row['payload']['_producer_connection']['connection_id']!=self._state[symbol]['book_context']:return None
   payload=row['payload'];values=self._funding_values(payload)
   if values is None:return None
   interval,next_ms=values
   observed=max(_ceil_ms(row['ingest_us']),*(proof['observed_ms'] for proof in payload['_field_observations']['fields'].values()))
   return _seal(dict(receipt_id='f_'+self.run_id+'_'+symbol+'_'+str(row['id']),symbol=symbol,source_id='market_data_persisted_funding',raw_sha256=row['row_sha256'],kind='COMPLETE_INTERVAL',observed_ms=observed,previous_ms=next_ms-interval,next_ms=next_ms,interval_ms=interval,events=[]))
  except (KeyError,ValueError,TypeError):return None
 def _proposal(self,symbol,row,answer,now,packet_sha,events):
  state=self._state[symbol];p=self.account.policy
  if answer.get('eligible') is not True or answer.get('direction') not in (-1,1) or symbol in self._pending:return
  if state['last_candidate'] is not None and now-state['last_candidate']<self.cooldown:return
  if self.started_ms+self.duration-now<=self.cooldown:state['issue']='RUN_WINDOW_CLOSING';return
  if now-max(_ceil_ms(row['ingest_us']),int(row['event_us'])//1000+250)>p['max_quote_age_ms']:state['issue']='STALE_STRATEGY_INPUT';return
  ident='p_'+self.run_id+'_'+symbol+'_'+str(row['id']);observed=answer['available_from_ms']
  if observed>now:raise ValueError('future caller-declared packet cut')
  bundle=dict(schema='terminan.paper.strategy-input.v2',strategy='book_tape_research',strategy_revision=self.strategy_revision,source_packet_sha256=packet_sha,source_row_sha256=(*state['prefix'],row['row_sha256']),result=answer)
  signal=_seal(dict(receipt_id=ident+'_proposal',symbol=symbol,source_id='terminan_completed_tape_strategy',raw_sha256=digest(bundle),decision_ms=now,observed_ms=observed,expires_ms=now+p['entry_wait_ms'],side='long' if answer['direction']==1 else 'short'))
  funding=self._funding(symbol,now);self._current();risk=self.account.reserve(ident,signal=signal,strategy='book_tape_research',strategy_revision=self.strategy_revision,evidence_class='SYNTHETIC',reference_quote=state['book'],funding=funding,now_ms=now);state['last_candidate']=now;state['candidates']+=1
  if risk['accepted'] is True:
   self._pending[symbol]=dict(candidate=dict(id=ident,signal=signal,strategy='book_tape_research',strategy_revision=self.strategy_revision,evidence_class='SYNTHETIC',reference_quote=state['book'],funding=funding),status='RESERVED',risk_receipt=risk)
  events.append(self._emit('RISK_DECISION',symbol,ident,now,dict(strategy_bundle=bundle,proposal=signal,risk=risk),source_packet_sha256=packet_sha))
  if risk['accepted'] is not True:state['denied']+=1;state['issue']='RISK_DENIED_'+risk['reason'];return
  at=self._now();self._current()
  if at+p['latency_ms']>signal['expires_ms']:
   self._uncertain(symbol,'QUOTE_TIMEOUT',at,events);state['issue']='PROPOSAL_TTL_CONSUMED';return
  basis=dict(schema='terminan.paper.risk-decision-input.v2',proposal_sha256=signal['sha256'],risk_sha256=digest(risk))
  decision=_seal(dict(receipt_id=ident+'_decision',symbol=symbol,source_id='terminan_paper_risk_decision',raw_sha256=digest(basis),decision_ms=at,observed_ms=at,expires_ms=signal['expires_ms'],side=signal['side']))
  self._pending[symbol]=self.account.record_decision(ident,decision,now_ms=at);events.append(self._emit('ENTRY_DECISION',symbol,ident,at,dict(decision=decision),source_packet_sha256=packet_sha))
 def _book(self,symbol,row,connection,now,financial,events,packet_sha):
  state=self._state[symbol];p=self.account.policy;payload=row['payload']
  quote=_seal(dict(receipt_id='q_'+self.run_id+'_'+symbol+'_'+str(row['id']),symbol=symbol,source_id='market_data_persisted_book',raw_sha256=row['row_sha256'],epoch='book_'+connection,sequence=row['id'],event_ms=int(row['event_us'])//1000,observed_ms=_ceil_ms(row['ingest_us']),bid=str(payload['best_bid']),ask=str(payload['best_ask'])))
  state['book']=quote;state['book_row']=row
  record=self._pending.get(symbol)
  if not financial or record is None or record['status']=='UNCERTAIN':return
  if record['status']=='DECIDED':
   if quote['event_ms']<record['decision']['decision_ms']+p['latency_ms']:return
   self._pending[symbol]=self.account.record_entry(self._id(record),quote,now_ms=now);events.append(self._emit('ENTRY_SELECTED',symbol,self._id(record),now,dict(quote=quote,row_sha256=row['row_sha256']),source_packet_sha256=packet_sha))
  elif record['status']=='EXIT_DECIDED':
   if quote['event_ms']<record['close_decision']['decision_ms']+p['latency_ms']:return
   c=record['candidate'];request=dict(schema='terminan.paper.causal-quote.request.v2',request_id=c['id'],strategy=c['strategy'],strategy_revision=c['strategy_revision'],evidence_class=c['evidence_class'],symbol=symbol,units=dict(price='USDT/'+symbol[:-4],qty=symbol[:-4]),policy=dict(notional=p['notional_usdt'],fee_bps=p['fee_bps'],slippage_bps=p['slippage_bps'],latency_ms=p['latency_ms'],max_quote_age_ms=p['max_quote_age_ms'],max_hold_ms=p['hold_ms']+p['exit_wait_ms']),signal=record['decision'],close_signal=record['close_decision'],quotes=[record['entry_quote'],quote],funding=c['funding'])
   result=self.account.close_trade(request,now_ms=now);state['closed']+=1;del self._pending[symbol];events.append(self._emit('LEDGER_COMMITTED',symbol,c['id'],now,dict(request_sha256=digest(request),result_sha256=result['result_sha256'],admitted_ms=result['admitted_ms']),source_packet_sha256=packet_sha))
 def accept_packet(self,packet,*,expected_request):
  with self._lock:
   self._current()
   if self._ended:return ()
   try:
    from market_data.paper_inputs import validate_paper_inputs
    checked=validate_paper_inputs(packet);q=checked['request']
    if type(expected_request) is not dict or len(expected_request)!=len(q) or any(type(k) is not str or k not in q for k in expected_request) or any(type(expected_request[k]) is not type(q[k]) or expected_request[k]!=q[k] for k in q):raise ValueError('source request mismatch')
    if q['max_age_ms']!=self.source_max_age:raise ValueError('source age contract mismatch')
    symbol=q['symbol'];state=self._state[symbol];pin=digest(checked)
    if state['retry'] is not None and state['retry'][0]==pin:return state['retry'][1]
    now=self._now()
    if q['as_of_ms']>now:raise ValueError('future source packet cut')
    if now>=self.started_ms+self.duration:return self.advance()
    batch=state['strategy'].observe_packet(checked,expected_request=expected_request);answers={r['row_id']:r for r in batch.observations};events=[]
    tickers=[r for r in checked['rows'] if r['event_type']=='derivatives_ticker']
    if tickers:
     payload=tickers[-1]['payload'];pending=self._pending.get(symbol);funding_fields=('funding_rate','funding_interval_hour','next_funding_time')
     # A newly observed explicit unknown is not a numeric schedule change.
     # Invalidate BEFORE hold/close advancement; omitted fields/no arrival
     # remain distinct and cannot fabricate facts about the prior interval.
     explicit_unknown=any(key in payload and payload[key] is None for key in funding_fields)
     complete_unavailable=all(key in payload for key in funding_fields) and checked['funding_status']!='KNOWN_SOURCE_FIELDS'
     if pending is not None and (explicit_unknown or complete_unavailable):self._uncertain(symbol,'SOURCE_GAP',now,events)
     values=self._funding_values(payload)
     if values is not None and pending is not None and pending['candidate'].get('funding') is not None:
      prior=pending['candidate']['funding']
      if values!=(prior['interval_ms'],prior['next_ms']):self._uncertain(symbol,'FUNDING_CHANGED',now,events)
     state['funding']=(checked,tickers[-1]) if checked['funding_status']=='KNOWN_SOURCE_FIELDS' and checked['producer_context_status']=='CONSISTENT' else None
    self._advance(now,events)
    financial=checked['producer_context_status']=='CONSISTENT'
    for row in checked['rows']:
     self._current();at=self._now();connection=self._context(symbol,row,at,events)
     if connection is None:continue
     if row['event_type']=='orderbook_snapshot':self._book(symbol,row,connection,at,financial,events,pin)
     elif row['event_type']=='trade_tape_250ms':
      answer=answers[row['id']]
      if financial:self._proposal(symbol,row,answer,at,pin,events)
      state['prefix']=(*state['prefix'],row['row_sha256'])[-32:]
    state['cursor']=checked['cursor'];self._advance(self._now(),events)
    if not events:events.append(self._emit('SOURCE_PACKET_OBSERVED',symbol,None,now,dict(cursor=state['cursor'],source_request_sha256=digest(q)),source_packet_sha256=pin))
    result=tuple(events);state['retry']=(pin,result);return result
   except Exception:
    if self._blocked is None:self._blocked='SESSION_SOURCE_OR_ACCOUNT_REJECTED'
    raise
 def finish(self):
  with self._lock:
   self._current()
   if self._ended:return ()
   try:
    now=self._now();events=[]
    for symbol in tuple(self._pending):self._uncertain(symbol,'RESTART',now,events)
    self._ended=True;self._end_reason='CALLER_STOP';events.append(self._emit('SESSION_FINISHED',None,None,now,dict(qualification='NOT_EVALUATED',unresolved_reservations=len(self._pending))))
    return tuple(events)
   except Exception:
    if self._blocked is None:self._blocked='SESSION_ACCOUNT_REJECTED'
    raise
 def publication_artifact(self):
  with self._lock:
   self._current()
   try:
    view=self.account.verified_results();now=self._now();raw=canonical_json(view);pin=sha256(raw).hexdigest()
    descriptor=self._emit('VERIFIED_PAPER_SNAPSHOT',None,None,now,dict(paper_sha256=pin,account_id=view['account_id'],sequence=view['sequence'],row_count=view['row_count'],result_sha256s=[row['result_sha256'] for row in view['rows']],consistency=view['consistency']))
    return SessionPublication(raw,pin,descriptor)
   except Exception:
    if self._blocked is None:self._blocked='SESSION_ACCOUNT_REJECTED'
    raise
 def publication_descriptor(self):return self.publication_artifact().descriptor

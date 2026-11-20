"""Temporal and declaration-integrity checks for offline causal quote execution.

This validates schedules, not market numerics, source authenticity or authority.
PaperEngine must obtain Math financial validation before committing any result.
No storage, account, execution simulator or transport is implemented here.
"""
from dataclasses import dataclass
from hashlib import sha256
import re
from decimal import Decimal,DecimalException,localcontext
from .paper_ledger import canonical_json
_BASE={'receipt_id','source_id','raw_sha256','sha256','symbol'}
def _need(value):
 if not value:raise ValueError('invalid causal quote schedule')
def _clock(value):
 _need(type(value) is int and 0<=value<=2**53-1);return value
def _label(value):return type(value) is str and len(value)<=128 and re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}',value) is not None
def _decimal_text(value):return type(value) is str and len(value)<=256 and re.fullmatch(r'-?(?:0|[1-9][0-9]*)(?:[.][0-9]+)?(?:[eE][+-]?[0-9]+)?',value) is not None
def _decimal_value(value):
 # Representation decoding only. Market/rate domains remain Math-owned.
 _need(_decimal_text(value))
 try:
  with localcontext() as context:
   context.clear_flags();number=Decimal(value)
 except DecimalException as exc:raise ValueError('unrepresentable causal decimal text') from exc
 _need(number.is_finite() and -4096<=number.as_tuple().exponent<=4096)
 return number
def _receipt_shape(value,fields):
 expected=_BASE|set(fields)
 _need(type(value) is dict and len(value)==len(expected))
 _need(all(type(k) is str for k in value) and set(value)==expected)
 _need(all(_label(value[k]) for k in ('receipt_id','source_id')))
 _need(type(value['symbol']) is str and len(value['symbol'])<=30 and re.fullmatch('[A-Z0-9]{2,30}',value['symbol']) is not None)
 for key in ('raw_sha256','sha256'):_need(type(value[key]) is str and len(value[key])==64 and re.fullmatch('[a-f0-9]{64}',value[key]) is not None)
def _receipt(value,fields):
 _receipt_shape(value,fields)
 _need(value['sha256']==sha256(canonical_json({k:v for k,v in value.items() if k!='sha256'})).hexdigest())
 return value

def _preflight(a,b,quotes,f):
 # Exact container type/count checks precede iteration, serialization or hashes.
 _need(type(quotes) is list and len(quotes)==2)
 _receipt_shape(a,{'decision_ms','observed_ms','expires_ms','side'})
 _receipt_shape(b,{'decision_ms','observed_ms','expires_ms'})
 _need(type(a['side']) is str and a['side'] in ('long','short'))
 for d in (a,b):
  for key in ('decision_ms','observed_ms','expires_ms'):_clock(d[key])
 _receipt_shape(f,{'kind','observed_ms','previous_ms','next_ms','interval_ms','events'})
 _need(type(f['kind']) is str and f['kind'] in ('COMPLETE_INTERVAL','COMPLETE_EVENTS'))
 _need(type(f['events']) is list and len(f['events'])<=128)
 for key in ('observed_ms','previous_ms','next_ms','interval_ms'):_clock(f[key])
 for q in quotes:
  _receipt_shape(q,{'epoch','sequence','event_ms','observed_ms','bid','ask'})
  _need(_label(q['epoch']) and _decimal_text(q['bid']) and _decimal_text(q['ask']))
  for key in ('sequence','event_ms','observed_ms'):_clock(q[key])
 for event in f['events']:
  _receipt_shape(event,{'event_ms','observed_ms','rate','mark_price'})
  _need(_decimal_text(event['rate']) and _decimal_text(event['mark_price']))
  _clock(event['event_ms']);_clock(event['observed_ms'])

def validate_causal_schedule(*,open_decision,close_decision,quotes,funding,latency_ms,max_quote_age_ms,max_hold_ms,now_ms):
 """Return selected (mark-price text, rate text) only after full temporal proof.

 Return values remain untrusted numeric text for the sole Math owner. Canonical
 hashes bind declarations only; passing this function cannot grant admission.
 """
 _clock(now_ms)
 for value in (latency_ms,max_quote_age_ms,max_hold_ms):_need(1<=_clock(value)<=3600000)
 _preflight(open_decision,close_decision,quotes,funding)
 _need(len(canonical_json([open_decision,close_decision,quotes,funding]))<=262144)
 a=_receipt(open_decision,{'decision_ms','observed_ms','expires_ms','side'})
 b=_receipt(close_decision,{'decision_ms','observed_ms','expires_ms'})
 _need(a['side'] in ('long','short'))
 for d in (a,b):_need(_clock(d['observed_ms'])<=_clock(d['decision_ms'])<_clock(d['expires_ms'])<=now_ms+3600000)
 _need(type(quotes) is list and len(quotes)==2)
 for q,d in zip(quotes,(a,b)):
  _receipt(q,{'epoch','sequence','event_ms','observed_ms','bid','ask'})
  _need(_label(q['epoch']));_clock(q['sequence'])
  _need(_clock(q['event_ms'])<=_clock(q['observed_ms'])<=now_ms and q['observed_ms']-q['event_ms']<=max_quote_age_ms)
  _need(d['decision_ms']+latency_ms<=q['event_ms'] and q['observed_ms']<=d['expires_ms'])
  _need(_decimal_text(q['bid']) and _decimal_text(q['ask']))
 x,y=quotes
 _need(x['epoch']==y['epoch'] and x['source_id']==y['source_id'] and x['sequence']<y['sequence'])
 _need(x['event_ms']<y['event_ms'] and x['observed_ms']<y['observed_ms'] and x['observed_ms']<=b['decision_ms'])
 _need(max(y['event_ms']-x['event_ms'],y['observed_ms']-x['observed_ms'])<=max_hold_ms and now_ms-y['event_ms']<=max_quote_age_ms)
 f=_receipt(funding,{'kind','observed_ms','previous_ms','next_ms','interval_ms','events'})
 prev,nxt,interval=(_clock(f[k]) for k in ('previous_ms','next_ms','interval_ms'))
 _need(1<=interval<=86400000 and prev<=x['event_ms']<y['event_ms']<nxt and (nxt-prev)%interval==0)
 _need((x['event_ms']-prev)%interval!=0 and (y['event_ms']-prev)%interval!=0)
 _need(_clock(f['observed_ms'])<=now_ms and type(f['events']) is list and len(f['events'])<=128)
 _need((nxt-prev)//interval-1<=128 and f['kind'] in ('COMPLETE_INTERVAL','COMPLETE_EVENTS'))
 if f['kind']=='COMPLETE_INTERVAL':_need(nxt-prev==interval and not f['events'] and prev<=f['observed_ms']<nxt and f['observed_ms']<=x['observed_ms'])
 else:_need(bool(f['events']))
 expected=range(prev+interval,nxt,interval);_need(len(f['events'])==len(expected));selected=[]
 for event,t in zip(f['events'],expected):
  _receipt(event,{'event_ms','observed_ms','rate','mark_price'})
  _need(_clock(event['event_ms'])==t<=_clock(event['observed_ms'])<=f['observed_ms'])
  _need(_decimal_text(event['rate']) and _decimal_text(event['mark_price']))
  if x['event_ms']<=t<y['event_ms']:selected.append((event['mark_price'],event['rate']))
 receipts=[a,b,x,y,f,*f['events']]
 _need(all(r['symbol']==a['symbol'] for r in receipts))
 identities=[r['receipt_id'] for r in receipts];_need(len(identities)==len(set(identities)))
 return tuple(selected)


@dataclass(frozen=True)
class QuoteExecution:
 symbol: str
 side: str
 entry_ms: int
 exit_ms: int
 metrics: object
 fill: object
 model: str = "CALLER_DECLARED_CAUSAL_QUOTES_NOT_COMPLETE_MARKET_STREAM"

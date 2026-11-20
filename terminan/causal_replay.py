"""Canonical causal quote request/result codec using the ONLY PaperEngine.
No provider, scheduler, source authentication or secondary financial evaluator.
"""
from hashlib import sha256
from decimal import Decimal
import json,re
from .paper import PaperEngine,_serialize
from .paper_ledger import canonical_json
from .causal_quotes import validate_causal_schedule,_decimal_text,_clock
REQUEST_SCHEMA='terminan.paper.causal-quote.request.v2'
RESULT_SCHEMA='terminan.paper.causal-quote.result.v2'
SYMBOLS=frozenset(name+'USDT' for name in ('BTC','ETH','SOL','XRP','BNB','DOGE','ADA','AVAX','LINK','DOT'))
def digest(value):return sha256(canonical_json(value)).hexdigest()
def label(value):
 if type(value) is not str or not 1<=len(value)<=128 or re.fullmatch('[A-Za-z0-9_.:-]+',value) is None:raise ValueError('invalid causal identity')
def fields(value,keys):
 expected=set(keys)
 if type(value) is not dict or len(value)!=len(expected) or any(type(key) is not str for key in value) or set(value)!=expected:raise ValueError('closed causal descriptor required')
def prepare_causal_request(request,*,now_ms):
 _clock(now_ms);fields(request,('schema','request_id','strategy','strategy_revision','evidence_class','symbol','units','policy','signal','close_signal','quotes','funding'))
 if type(request['schema']) is not str or request['schema']!=REQUEST_SCHEMA or type(request['symbol']) is not str or request['symbol'] not in SYMBOLS:raise ValueError('canonical causal request required')
 for key in ('request_id','strategy'):label(request[key])
 if request['strategy'] not in ('causal_quote','book_tape_research'):raise ValueError('canonical causal strategy identity required')
 if type(request['strategy_revision']) is not str or re.fullmatch('[a-f0-9]{40}',request['strategy_revision']) is None or type(request['evidence_class']) is not str or request['evidence_class'] not in ('SYNTHETIC','HISTORICAL','LIVE'):raise ValueError('causal revision/evidence label required')
 fields(request['units'],('price','qty'))
 if any(type(value) is not str for value in request['units'].values()) or request['units']!={'price':'USDT/'+request['symbol'][:-4],'qty':request['symbol'][:-4]}:raise ValueError('causal units required')
 p=request['policy'];fields(p,('notional','fee_bps','slippage_bps','latency_ms','max_quote_age_ms','max_hold_ms'))
 for key in ('notional','fee_bps','slippage_bps'):
  if not _decimal_text(p[key]):raise ValueError('bounded decimal policy text required')
 args=dict(open_decision=request['signal'],close_decision=request['close_signal'],quotes=request['quotes'],funding=request['funding'],latency_ms=p['latency_ms'],max_quote_age_ms=p['max_quote_age_ms'],max_hold_ms=p['max_hold_ms'],now_ms=now_ms)
 validate_causal_schedule(**args)
 if request['signal']['symbol']!=request['symbol']:raise ValueError('causal symbol mismatch')
 raw=canonical_json(request)
 if len(raw)>262144:raise ValueError('causal request byte limit')
 return json.loads(raw)
def calculate_causal_receipt(request,*,now_ms):
 """Pure replay through the shared engine; no storage or external actions."""
 q=prepare_causal_request(request,now_ms=now_ms);p=q['policy'];engine=PaperEngine(notional=p['notional'],slippage_bps=p['slippage_bps']);engine.enabled=True
 value=engine.execute_quote(open_decision=q['signal'],close_decision=q['close_signal'],quotes=q['quotes'],funding=q['funding'],latency_ms=p['latency_ms'],max_quote_age_ms=p['max_quote_age_ms'],max_hold_ms=p['max_hold_ms'],now_ms=now_ms,fee_bps=Decimal(p['fee_bps']))
 result=dict(schema=RESULT_SCHEMA,run_id=q['request_id'],request_sha256=digest(q),request=q,admitted_ms=now_ms,symbol=q['symbol'],strategy=q['strategy'],strategy_revision=q['strategy_revision'],evidence_class=q['evidence_class'],units=q['units'],entry_ts_ms=value.entry_ms,exit_ts_ms=value.exit_ms,metrics=_serialize(value.metrics._asdict()),status='OFFLINE_UNATTESTED',provenance='CALLER_SUPPLIED_UNATTESTED',source_authenticity='NOT_EVALUATED',point_in_time_availability='UNKNOWN',model=value.model,execution_authority=False,trading_authorized=False,training_authorized=False,paper_eligible='NOT_QUALIFIED')
 result['result_sha256']=digest(result);return result

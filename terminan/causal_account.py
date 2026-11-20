"""Fresh-owned offline causal account namespace, backed by existing receipt ledgers.
Ownership is an external local custody receipt, never source authentication.
This foundation intentionally exposes no reserve/settle operation yet.
"""
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import json,os,re,stat,uuid,copy
from contextlib import contextmanager
from .paper_ledger import PaperReplayLedger,canonical_json
from .causal_replay import fields

@dataclass(frozen=True)
class CausalAccountOwnership:
 account_id:str
 policy_sha256:str
 root_identity:tuple
 state_identity:tuple
 results_identity:tuple

def _identity(path,directory=False):
 location=Path(path).absolute()
 if str(location).startswith(('\\\\','//')) or ':' in str(location)[2:]:raise ValueError('ordinary local account path required')
 for part in (*reversed(location.parents),location):
  info=part.lstat()
  if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&1024:raise ValueError('linked account path refused')
 info=location.stat()
 if (not stat.S_ISDIR(info.st_mode) if directory else not stat.S_ISREG(info.st_mode) or info.st_nlink!=1):raise ValueError('ordinary account object required')
 return info.st_dev,info.st_ino

def _current(callback):
 if not callable(callback) or callback() is not True:raise ValueError('causal source admission unavailable')

def _policy(value):
 keys=('schema','mode','long_only','initial_cash_usdt','notional_usdt','max_reserved_usdt','max_positions','max_drawdown_fraction','max_quote_age_ms','max_spread_bps','fee_bps','slippage_bps','latency_ms','entry_wait_ms','exit_wait_ms','hold_ms')
 fields(value,keys)
 if value['schema']!='terminan.paper.causal-account-policy.v2' or type(value['schema']) is not str or value['mode']!='SYNTHETIC_OFFLINE' or type(value['mode']) is not str or value['long_only'] is not True:raise ValueError('explicit conservative offline account policy required')
 # Policy admission limits are DTO/control boundaries; all account calculations
 # and actual reservation predicates belong to the public Math SDK.
 bounds={'initial_cash_usdt':('0.000000001','1000000000000'),'notional_usdt':('0.000000001','1000000000000'),'max_reserved_usdt':('0','1000000000000000'),'max_drawdown_fraction':('0','1'),'max_spread_bps':('0','10000'),'fee_bps':('0','1000'),'slippage_bps':('0','1000')}
 for key,(lo,hi) in bounds.items():
  text=value[key]
  if type(text) is not str or not 1<=len(text)<=128 or re.fullmatch(r'[+]?(?:[0-9]+(?:[.][0-9]*)?|[.][0-9]+)(?:[eE][+-]?[0-9]+)?',text) is None:raise ValueError('bounded account policy decimal text required')
  number=Decimal(text)
  if not number.is_finite() or not Decimal(lo)<=number<=Decimal(hi) or len(number.as_tuple().digits)>128 or not -1000<=number.as_tuple().exponent<=1000:raise ValueError('account policy domain refused')
 for key in ('max_positions','max_quote_age_ms','latency_ms','entry_wait_ms','exit_wait_ms','hold_ms'):
  limit=10 if key=='max_positions' else 3600000
  if type(value[key]) is not int or not 1<=value[key]<=limit:raise ValueError('bounded literal account control required')
 if not Decimal(value['notional_usdt'])<=Decimal(value['max_reserved_usdt'])<=Decimal(value['initial_cash_usdt']):raise ValueError('account collateral policy ordering refused')
 if not Decimal('0')<Decimal(value['max_drawdown_fraction'])<Decimal('1') or not Decimal('0')<Decimal(value['max_spread_bps'])<=Decimal('1000'):raise ValueError('account risk policy limits refused')
 if not value['latency_ms']<value['entry_wait_ms'] or not value['latency_ms']<value['exit_wait_ms'] or value['hold_ms']+value['exit_wait_ms']>3600000:raise ValueError('account temporal policy ordering refused')
 from market_math import paper_account_balances
 paper_account_balances(Decimal(value['initial_cash_usdt']),(),(),())
 return json.loads(canonical_json(value))

def _hash(value):return sha256(canonical_json(value)).hexdigest()

class CausalAccountJournal:
 @classmethod
 def create(cls,root,policy,*,require_current):
  policy=_policy(policy);_current(require_current)
  root=Path(root).absolute()
  # Validate ancestors before the only exclusive namespace creation.
  _identity(root.parent,directory=True)
  try:root.mkdir()
  except FileExistsError as exc:raise ValueError('causal account requires a fresh owned namespace') from exc
  identity=_identity(root,directory=True);_current(require_current)
  for name in ('state.sqlite','results.sqlite'):
   _current(require_current)
   with (root/name).open('xb'):pass
  _current(require_current);state=PaperReplayLedger(root/'state.sqlite')
  _current(require_current);results=PaperReplayLedger(root/'results.sqlite')
  ownership=CausalAccountOwnership(uuid.uuid4().hex,_hash(policy),identity,_identity(root/'state.sqlite'),_identity(root/'results.sqlite'))
  receipt=dict(schema='terminan.paper.causal-account.initial.v2',run_id='causal-account-initial',request_sha256=ownership.policy_sha256,account_id=ownership.account_id,policy=policy,status='OFFLINE_UNATTESTED',provenance='CALLER_SUPPLIED_UNATTESTED',execution_authority=False,trading_authorized=False)
  receipt['result_sha256']=_hash(receipt);_current(require_current);state.record(receipt)
  return cls.open(root,policy,ownership=ownership,require_current=require_current)
 @classmethod
 def open(cls,root,policy,*,ownership,require_current):
  policy=_policy(policy);_current(require_current)
  if type(ownership) is not CausalAccountOwnership or re.fullmatch('[a-f0-9]{32}',ownership.account_id or '') is None or ownership.policy_sha256!=_hash(policy):raise ValueError('external account ownership receipt required')
  self=object.__new__(cls);self.root=Path(root).absolute();self.policy=policy;self.ownership=ownership;self.require_current=require_current
  self._verify()
  # Read-only preflight above proves these are existing dedicated ledgers;
  # their constructor cannot adopt a missing/truncated/foreign file.
  self._state=object.__new__(PaperReplayLedger);self._state.path=self.root/'state.sqlite'
  self._results=object.__new__(PaperReplayLedger);self._results.path=self.root/'results.sqlite'
  self._verify();return self
 def _guard(self):
  _current(self.require_current)
  if _hash(_policy(self.policy))!=self.ownership.policy_sha256:raise ValueError('account policy identity changed')
  if _identity(self.root,directory=True)!=self.ownership.root_identity:raise ValueError('account directory identity changed')
  names=[]
  for child in self.root.iterdir():
   names.append(child.name)
   if len(names)>2:raise ValueError('foreign account namespace content')
  if set(names)!={'state.sqlite','results.sqlite'}:raise ValueError('incomplete or hot account namespace')
  for name,expected in (('state.sqlite',self.ownership.state_identity),('results.sqlite',self.ownership.results_identity)):
   p=self.root/name
   if _identity(p)!=expected or not 100<=p.stat().st_size<=2*1024*1024:raise ValueError('account file identity or budget changed')
 def _verify(self):
  self._guard()
  with PaperReplayLedger._existing_database(self.root/'state.sqlite') as db:
   if db is None:raise ValueError('missing state ledger')
   value=self._read_log(db)
  with PaperReplayLedger._existing_database(self.root/'results.sqlite') as db:
   if db is None or db.execute('SELECT count(*) FROM paper_replay_receipts').fetchone()[0]!=0:raise ValueError('foreign completed receipt before close-intent support')
  _current(self.require_current);return value
 def _read_log(self,db):
  count=db.execute('SELECT count(*) FROM paper_replay_receipts').fetchone()[0]
  if not 1<=count<=4097:raise ValueError('causal event capacity refused')
  if db.execute('SELECT 1 FROM paper_replay_receipts WHERE length(CAST(receipt AS BLOB))>32768 LIMIT 1').fetchone():raise ValueError('causal event byte budget refused')
  receipt=PaperReplayLedger._read(db,'causal-account-initial',self.ownership.policy_sha256)
  if receipt is not None:fields(receipt,('schema','run_id','request_sha256','account_id','policy','status','provenance','execution_authority','trading_authorized','result_sha256'))
  if receipt is None or receipt.get('schema')!='terminan.paper.causal-account.initial.v2' or receipt.get('account_id')!=self.ownership.account_id or receipt.get('policy')!=self.policy:raise ValueError('account ownership binding mismatch')
  previous=receipt['result_sha256'];records={};last=0;sequence=0
  for ident,pin in db.execute("SELECT run_id,request_sha256 FROM paper_replay_receipts WHERE run_id!='causal-account-initial' ORDER BY run_id"):
   sequence+=1
   if ident!='causal-event-'+str(sequence).zfill(8):raise ValueError('causal event ordering refused')
   stored=PaperReplayLedger._read(db,ident,pin);fields(stored,('schema','run_id','request_sha256','event','status','provenance','execution_authority','trading_authorized','result_sha256'))
   if stored['schema']!='terminan.paper.causal-account-event.v2':raise ValueError('causal event schema refused')
   event=stored.get('event');fields(event,('sequence','at_ms','previous_sha256','record'))
   from .causal_quotes import _clock
   _clock(event['at_ms'])
   if event['sequence']!=sequence or type(event['sequence']) is not int or event['at_ms']<last or event['previous_sha256']!=previous or _hash(event)!=pin:raise ValueError('causal event chain refused')
   record=event['record'];fields(record,('candidate','at_ms','status','collateral','risk_receipt','uncertainty'))
   candidate=self._candidate(**record['candidate']);old=records.get(candidate['id'])
   if old is None:
    if record!=self._risk(candidate,records,event['at_ms']):raise ValueError('causal risk replay mismatch')
   else:
    expected=copy.deepcopy(old);expected.update(status='UNCERTAIN',uncertainty=record['uncertainty'])
    if old['status']!='RESERVED' or record!=expected or record['uncertainty'] not in ('SOURCE_GAP','FUNDING_CHANGED','RESTART','REVOKED','QUOTE_TIMEOUT'):raise ValueError('causal uncertainty transition refused')
   records[candidate['id']]=record;previous=stored['result_sha256'];last=event['at_ms']
  return records,last,sequence,previous
 @contextmanager
 def _transaction(self):
  self._verify()
  with self._state._paper_event_transaction(write=True) as db:
   value=self._read_log(db);_current(self.require_current)
   yield db,value
   # This callback must remain current through the final commit boundary.
   # On refusal the existing ledger transaction rolls back; no cleanup/adoption.
   if db.execute('PRAGMA page_count').fetchone()[0]*db.execute('PRAGMA page_size').fetchone()[0]>2*1024*1024:raise ValueError('causal database capacity refused')
   _current(self.require_current)
 def _candidate(self,*,id,signal,strategy,strategy_revision,evidence_class,reference_quote,funding):
  from .causal_replay import label,SYMBOLS
  from .causal_quotes import _receipt_shape,_receipt,_clock,_decimal_text,_label
  label(id);label(strategy)
  if strategy not in ('causal_quote','book_tape_research') or type(strategy_revision) is not str or re.fullmatch('[a-f0-9]{40}',strategy_revision) is None or type(evidence_class) is not str or evidence_class not in ('SYNTHETIC','HISTORICAL','LIVE'):raise ValueError('canonical strategy metadata required')
  _receipt_shape(signal,('decision_ms','observed_ms','expires_ms','side'))
  for k in ('decision_ms','observed_ms','expires_ms'):_clock(signal[k])
  if type(signal['side']) is not str or signal['side'] not in ('long','short') or signal['symbol'] not in SYMBOLS or not signal['observed_ms']<=signal['decision_ms']<signal['expires_ms'] or signal['expires_ms']-signal['decision_ms']!=self.policy['entry_wait_ms']:raise ValueError('bounded causal signal required')
  _receipt(signal,('decision_ms','observed_ms','expires_ms','side'))
  if reference_quote is not None:
   _receipt_shape(reference_quote,('epoch','sequence','event_ms','observed_ms','bid','ask'))
   if not _label(reference_quote['epoch']) or not _decimal_text(reference_quote['bid']) or not _decimal_text(reference_quote['ask']):raise ValueError('bounded causal book required')
   for k in ('sequence','event_ms','observed_ms'):_clock(reference_quote[k])
   if reference_quote['event_ms']>reference_quote['observed_ms']:raise ValueError('causal quote clocks refused')
   _receipt(reference_quote,('epoch','sequence','event_ms','observed_ms','bid','ask'))
   from market_math import paper_quote_book_valid
   if paper_quote_book_valid(Decimal(reference_quote['bid']),Decimal(reference_quote['ask'])) is not True:raise ValueError('Math book domain refused')
  if funding is not None:
   _receipt_shape(funding,('kind','observed_ms','previous_ms','next_ms','interval_ms','events'))
   if type(funding['events']) is not list or len(funding['events'])!=0 or type(funding['kind']) is not str or funding['kind']!='COMPLETE_INTERVAL':raise ValueError('reservation requires a complete declared no-funding interval')
   for k in ('observed_ms','previous_ms','next_ms','interval_ms'):_clock(funding[k])
   _receipt(funding,('kind','observed_ms','previous_ms','next_ms','interval_ms','events'))
  return json.loads(canonical_json(dict(id=id,signal=signal,strategy=strategy,strategy_revision=strategy_revision,evidence_class=evidence_class,reference_quote=reference_quote,funding=funding)))
 def _balances(self,records):
  from market_math import paper_account_balances
  return paper_account_balances(Decimal(self.policy['initial_cash_usdt']),(),(),tuple(Decimal(r['collateral']) for r in records.values() if r['status'] not in ('DENIED','SETTLED')))
 def _risk(self,candidate,records,now_ms):
  from .causal_quotes import _clock
  _clock(now_ms);p=self.policy;s=candidate['signal'];q=candidate['reference_quote'];f=candidate['funding']
  if not s['decision_ms']<=now_ms<s['expires_ms']:raise ValueError('reservation clock refused')
  balance=self._balances(records);live=[r for r in records.values() if r['status'] not in ('DENIED','SETTLED')];reason='APPROVED';metrics=None
  if s['side']!='long':reason='LONG_ONLY'
  elif q is None:reason='QUOTE_UNAVAILABLE'
  elif q['symbol']!=s['symbol'] or q['observed_ms']>s['decision_ms'] or now_ms-q['event_ms']>p['max_quote_age_ms']:reason='STALE_QUOTE'
  else:
   from market_math import paper_reservation_metrics
   metrics=paper_reservation_metrics(balance.cash,balance.peak,balance.reserved,Decimal(q['bid']),Decimal(q['ask']),Decimal(p['notional_usdt']),Decimal(p['fee_bps']),Decimal(p['max_reserved_usdt']),Decimal(p['max_drawdown_fraction']),Decimal(p['max_spread_bps']))
   if metrics.spread_exceeded:reason='SPREAD_LIMIT'
   elif f is None or f['symbol']!=s['symbol'] or not (0<f['interval_ms']<=86400000 and f['next_ms']-f['previous_ms']==f['interval_ms'] and f['observed_ms']<=s['decision_ms'] and f['previous_ms']<=s['decision_ms'] and s['expires_ms']+p['hold_ms']+p['exit_wait_ms']<f['next_ms']):reason='FUNDING_UNPROVEN'
   elif any(r['candidate']['signal']['symbol']==s['symbol'] for r in live):reason='SYMBOL_RESERVED'
   elif len(live)>=p['max_positions']:reason='POSITION_LIMIT'
   elif metrics.reservation_exceeded:reason='RESERVATION_LIMIT'
   elif metrics.cash_insufficient:reason='INSUFFICIENT_CASH'
   elif metrics.drawdown_exceeded:reason='DRAWDOWN_LIMIT'
  accepted=reason=='APPROVED';collateral=str(metrics.collateral) if accepted else '0'
  risk=dict(schema='terminan.paper.causal-account-risk.v2',reservation_id=candidate['id'],accepted=accepted,reason=reason,policy_sha256=self.ownership.policy_sha256,candidate_sha256=_hash(candidate),ledger_sha256=_hash(records),cash_usdt=str(balance.cash),reserved_usdt=str(balance.reserved),collateral_usdt=collateral,decision_ms=s['decision_ms'],mode='SYNTHETIC_OFFLINE',execution_authority=False,trading_authorized=False)
  return dict(candidate=candidate,at_ms=now_ms,status='RESERVED' if accepted else 'DENIED',collateral=collateral,risk_receipt=risk,uncertainty=None)
 def _event(self,db,record,now_ms,sequence,previous):
  if sequence>=4096:raise ValueError('causal event capacity refused')
  event=dict(sequence=sequence+1,at_ms=now_ms,previous_sha256=previous,record=record)
  receipt=dict(schema='terminan.paper.causal-account-event.v2',run_id='causal-event-'+str(sequence+1).zfill(8),request_sha256=_hash(event),event=event,status='OFFLINE_UNATTESTED',provenance='CALLER_SUPPLIED_UNATTESTED',execution_authority=False,trading_authorized=False)
  receipt['result_sha256']=_hash(receipt);raw=canonical_json(receipt)
  if len(raw)>32768:raise ValueError('causal event byte budget refused')
  _current(self.require_current)
  db.execute('INSERT INTO paper_replay_receipts VALUES(?,?,?)',(receipt['run_id'],receipt['request_sha256'],raw.decode()))
 def reserve(self,request_id,*,signal,strategy,strategy_revision,evidence_class,reference_quote,funding,now_ms):
  from .causal_quotes import _clock
  _clock(now_ms);candidate=self._candidate(id=request_id,signal=signal,strategy=strategy,strategy_revision=strategy_revision,evidence_class=evidence_class,reference_quote=reference_quote,funding=funding)
  with self._transaction() as (db,(records,last,sequence,previous)):
   if request_id in records:
    old=records[request_id]
    if old['candidate']!=candidate:raise ValueError('causal reservation identity collision')
    return copy.deepcopy(old['risk_receipt'])
   if now_ms<last or len(records)>=512:raise ValueError('causal clock or capacity refused')
   record=self._risk(candidate,records,now_ms);self._event(db,record,now_ms,sequence,previous);return copy.deepcopy(record['risk_receipt'])
 def mark_uncertain(self,request_id,reason,*,now_ms):
  from .causal_quotes import _clock
  _clock(now_ms)
  if type(reason) is not str or reason not in ('SOURCE_GAP','FUNDING_CHANGED','RESTART','REVOKED','QUOTE_TIMEOUT'):raise ValueError('bounded uncertainty reason required')
  with self._transaction() as (db,(records,last,sequence,previous)):
   old=records[request_id]
   if old['status']=='UNCERTAIN':return
   if old['status']!='RESERVED' or now_ms<last:raise ValueError('uncertainty transition refused')
   record=copy.deepcopy(old);record.update(status='UNCERTAIN',uncertainty=reason);self._event(db,record,now_ms,sequence,previous)
 def snapshot(self):
  records,last,sequence,previous=self._verify();value=self._balances(records)
  return dict(schema='terminan.paper.causal-account.snapshot.v2',account_id=self.ownership.account_id,sequence=sequence,cash_usdt=str(value.cash),peak_usdt=str(value.peak),reserved_usdt=str(value.reserved),available_usdt=str(value.available_cash),execution_authority=False,trading_authorized=False,source_authenticity='NOT_EVALUATED',state='INITIALIZED_ONLY' if not sequence else 'RESERVATIONS_ONLY',reservations=copy.deepcopy(list(records.values())))

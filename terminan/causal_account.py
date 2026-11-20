"""Offline causal reservation, intent and settlement control around one PaperEngine.
State and finalized results reuse existing PaperReplayLedger storage. Cross-DB
commits are not atomic: ambiguous intents retain collateral without reexecution.
Local ownership receipts never authenticate market sources or grant authority.
"""
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import json,os,re,stat,uuid,copy
from .causal_quotes import _decimal_value
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
  number=_decimal_value(text)
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
   rows=self._result_rows();value=self._read_log(db,rows)
  self._verify_results(value[0],rows);_current(self.require_current);return (*value,rows)
 def _read_log(self,db,rows):
  if tuple(db.execute("SELECT name FROM sqlite_schema WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"))!=(('paper_replay_receipts',),):raise ValueError('foreign causal state schema refused')
  count=db.execute('SELECT count(*) FROM paper_replay_receipts').fetchone()[0]
  if not 1<=count<=4097:raise ValueError('causal event capacity refused')
  if db.execute('SELECT 1 FROM paper_replay_receipts WHERE length(CAST(receipt AS BLOB))>32768 LIMIT 1').fetchone():raise ValueError('causal event byte budget refused')
  receipt=PaperReplayLedger._read(db,'causal-account-initial',self.ownership.policy_sha256)
  if receipt is not None and db.execute('SELECT receipt FROM paper_replay_receipts WHERE run_id=?',('causal-account-initial',)).fetchone()[0]!=canonical_json(receipt).decode():raise ValueError('noncanonical initial receipt refused')
  if receipt is not None:fields(receipt,('schema','run_id','request_sha256','account_id','policy','status','provenance','execution_authority','trading_authorized','result_sha256'))
  if receipt is None or receipt.get('schema')!='terminan.paper.causal-account.initial.v2' or receipt.get('account_id')!=self.ownership.account_id or receipt.get('policy')!=self.policy:raise ValueError('account ownership binding mismatch')
  previous=receipt['result_sha256'];records={};last=0;sequence=0
  for ident,pin in db.execute("SELECT run_id,request_sha256 FROM paper_replay_receipts WHERE run_id!='causal-account-initial' ORDER BY run_id"):
   sequence+=1
   if ident!='causal-event-'+str(sequence).zfill(8):raise ValueError('causal event ordering refused')
   stored=PaperReplayLedger._read(db,ident,pin);fields(stored,('schema','run_id','request_sha256','event','status','provenance','execution_authority','trading_authorized','result_sha256'))
   if db.execute('SELECT receipt FROM paper_replay_receipts WHERE run_id=?',(ident,)).fetchone()[0]!=canonical_json(stored).decode():raise ValueError('noncanonical event receipt refused')
   if stored['schema']!='terminan.paper.causal-account-event.v2':raise ValueError('causal event schema refused')
   event=stored.get('event');fields(event,('sequence','at_ms','previous_sha256','record'))
   from .causal_quotes import _clock
   _clock(event['at_ms'])
   if event['sequence']!=sequence or type(event['sequence']) is not int or event['at_ms']<last or event['previous_sha256']!=previous or _hash(event)!=pin:raise ValueError('causal event chain refused')
   record=event['record']
   if type(record) is not dict or not 6<=len(record)<=15:raise ValueError('bounded causal progression record required')
   candidate=self._candidate(**record['candidate']);old=records.get(candidate['id'])
   if old is None:
    if record!=self._risk(candidate,records,event['at_ms'],rows):raise ValueError('causal risk replay mismatch')
   else:
    self._progress(old,record,event['at_ms'],sequence)
   records[candidate['id']]=record;previous=stored['result_sha256'];last=event['at_ms']
  return records,last,sequence,previous
 @contextmanager
 def _transaction(self):
  self._verify()
  with self._state._paper_event_transaction(write=True) as db:
   rows=self._result_rows();value=self._read_log(db,rows);self._verify_results(value[0],rows);_current(self.require_current)
   yield db,(*value,rows)
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
  if reference_quote is not None:self._quote(reference_quote)
  if funding is not None:
   _receipt_shape(funding,('kind','observed_ms','previous_ms','next_ms','interval_ms','events'))
   if type(funding['events']) is not list or len(funding['events'])!=0 or type(funding['kind']) is not str or funding['kind']!='COMPLETE_INTERVAL':raise ValueError('reservation requires a complete declared no-funding interval')
   for k in ('observed_ms','previous_ms','next_ms','interval_ms'):_clock(funding[k])
   _receipt(funding,('kind','observed_ms','previous_ms','next_ms','interval_ms','events'))
  return json.loads(canonical_json(dict(id=id,signal=signal,strategy=strategy,strategy_revision=strategy_revision,evidence_class=evidence_class,reference_quote=reference_quote,funding=funding)))
 def _balances(self,records,rows=None,*,include_pending=True):
  from market_math import paper_account_balances
  rows={} if rows is None else rows;settled=sorted((r for r in records.values() if r['status']=='SETTLED'),key=lambda r:r['settled_sequence']);settled_ids={r['candidate']['id'] for r in settled}
  return paper_account_balances(Decimal(self.policy['initial_cash_usdt']),tuple(Decimal(rows[r['candidate']['id']]['metrics']['net']) for r in settled),tuple(Decimal(row['metrics']['net']) for ident,row in rows.items() if include_pending and ident not in settled_ids),tuple(Decimal(r['collateral']) for r in records.values() if r['status'] not in ('DENIED','SETTLED')))
 def _risk(self,candidate,records,now_ms,rows=None):
  from .causal_quotes import _clock
  _clock(now_ms);p=self.policy;s=candidate['signal'];q=candidate['reference_quote'];f=candidate['funding']
  if not s['decision_ms']<=now_ms<s['expires_ms']:raise ValueError('reservation clock refused')
  balance=self._balances(records,rows,include_pending=False);live=[r for r in records.values() if r['status'] not in ('DENIED','SETTLED')];reason='APPROVED';metrics=None
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
  return sequence+1,receipt['result_sha256']
 def reserve(self,request_id,*,signal,strategy,strategy_revision,evidence_class,reference_quote,funding,now_ms):
  from .causal_quotes import _clock
  _clock(now_ms);candidate=self._candidate(id=request_id,signal=signal,strategy=strategy,strategy_revision=strategy_revision,evidence_class=evidence_class,reference_quote=reference_quote,funding=funding)
  with self._transaction() as (db,(records,last,sequence,previous,rows)):
   if request_id in records:
    old=records[request_id]
    if old['candidate']!=candidate:raise ValueError('causal reservation identity collision')
    return copy.deepcopy(old['risk_receipt'])
   if now_ms<last or len(records)>=512:raise ValueError('causal clock or capacity refused')
   sequence,previous=self._reconcile(db,records,rows,now_ms,sequence,previous)
   record=self._risk(candidate,records,now_ms,rows);self._event(db,record,now_ms,sequence,previous);return copy.deepcopy(record['risk_receipt'])
 def mark_uncertain(self,request_id,reason,*,now_ms):
  from .causal_quotes import _clock
  _clock(now_ms)
  if type(reason) is not str or reason not in ('SOURCE_GAP','FUNDING_CHANGED','RESTART','REVOKED','QUOTE_TIMEOUT'):raise ValueError('bounded uncertainty reason required')
  with self._transaction() as (db,(records,last,sequence,previous,rows)):
   old=records[request_id]
   if old['status']=='UNCERTAIN':return
   if old['status'] in ('DENIED','SETTLED') or now_ms<last:raise ValueError('uncertainty transition refused')
   record=copy.deepcopy(old);record.update(status='UNCERTAIN',uncertainty=reason);self._event(db,record,now_ms,sequence,previous)
 def snapshot(self):
  records,last,sequence,previous,rows=self._verify();value=self._balances(records,rows)
  return dict(schema='terminan.paper.causal-account.snapshot.v2',account_id=self.ownership.account_id,sequence=sequence,cash_usdt=str(value.cash),peak_usdt=str(value.peak),reserved_usdt=str(value.reserved),available_usdt=str(value.available_cash),execution_authority=False,trading_authorized=False,source_authenticity='NOT_EVALUATED',state='INITIALIZED_ONLY' if not sequence else 'CAUSAL_JOURNAL',reservations=copy.deepcopy(list(records.values())))

 def _decision(self,value,*,opening):
  from .causal_quotes import _receipt_shape,_receipt,_clock
  keys=('decision_ms','observed_ms','expires_ms','side') if opening else ('decision_ms','observed_ms','expires_ms')
  _receipt_shape(value,keys)
  for key in ('decision_ms','observed_ms','expires_ms'):_clock(value[key])
  if not value['observed_ms']<=value['decision_ms']<value['expires_ms']:raise ValueError('decision clock ordering refused')
  if opening and (type(value['side']) is not str or value['side'] not in ('long','short')):raise ValueError('decision side refused')
  _receipt(value,keys)
 def _quote(self,value):
  from .causal_quotes import _receipt_shape,_receipt,_clock,_label,_decimal_text
  _receipt_shape(value,('epoch','sequence','event_ms','observed_ms','bid','ask'))
  if not _label(value['epoch']) or not _decimal_text(value['bid']) or not _decimal_text(value['ask']):raise ValueError('bounded causal book required')
  for key in ('sequence','event_ms','observed_ms'):_clock(value[key])
  if value['event_ms']>value['observed_ms']:raise ValueError('book clock ordering refused')
  _receipt(value,('epoch','sequence','event_ms','observed_ms','bid','ask'))
  from market_math import paper_quote_book_valid
  if paper_quote_book_valid(_decimal_value(value['bid']),_decimal_value(value['ask'])) is not True:raise ValueError('Math book domain refused')
 def _progress(self,old,record,now_ms,sequence):
  mutable={'status','decision','entry_quote','close_decision','request','admitted_ms','result_sha256','settled_at_ms','settled_sequence','uncertainty'}
  if any(type(k) is not str for k in record) or set(record)-set(old)-mutable or any(record.get(k)!=v for k,v in old.items() if k not in mutable):raise ValueError('immutable causal record changed')
  for key in mutable-{'status','uncertainty'}:
   if key in old and record.get(key)!=old[key]:raise ValueError('causal progression rewrites admitted history')
  status=record['status'];expected=copy.deepcopy(old)
  if status=='UNCERTAIN':
   if old['status'] in ('DENIED','SETTLED','UNCERTAIN') or type(record['uncertainty']) is not str or record['uncertainty'] not in ('SOURCE_GAP','FUNDING_CHANGED','RESTART','REVOKED','QUOTE_TIMEOUT'):raise ValueError('uncertainty transition refused')
   expected.update(status=status,uncertainty=record['uncertainty'])
  elif status=='DECIDED':
   d=record.get('decision');self._decision(d,opening=True);s=old['candidate']['signal'];f=old['candidate']['funding'];q=old['candidate']['reference_quote']
   basis=dict(schema='terminan.paper.risk-decision-input.v2',proposal_sha256=s['sha256'],risk_sha256=_hash(old['risk_receipt']))
   if old['status']!='RESERVED' or d['source_id']!='terminan_paper_risk_decision' or d['raw_sha256']!=_hash(basis) or d['symbol']!=s['symbol'] or d['side']!=s['side'] or not s['decision_ms']<=d['observed_ms']<=d['decision_ms']==now_ms or d['expires_ms']!=s['expires_ms'] or now_ms+self.policy['latency_ms']>d['expires_ms'] or now_ms-q['event_ms']>self.policy['max_quote_age_ms'] or f is None or d['expires_ms']+self.policy['hold_ms']+self.policy['exit_wait_ms']>=f['next_ms']:raise ValueError('risk-bound opening decision refused')
   expected.update(status=status,decision=d)
  elif status=='ENTRY_SELECTED':
   q=record.get('entry_quote');self._quote(q);d=old.get('decision');prior=old['candidate']['reference_quote'];f=old['candidate']['funding']
   if old['status']!='DECIDED' or q['symbol']!=d['symbol'] or q['epoch']!=prior['epoch'] or q['source_id']!=prior['source_id'] or q['sequence']<=prior['sequence'] or not d['decision_ms']+self.policy['latency_ms']<=q['event_ms']<=q['observed_ms']<=now_ms<=d['expires_ms'] or now_ms-q['event_ms']>self.policy['max_quote_age_ms'] or q['event_ms']>=f['next_ms']:raise ValueError('fresh causal entry refused')
   expected.update(status=status,entry_quote=q)
  elif status=='EXIT_DECIDED':
   d=record.get('close_decision');self._decision(d,opening=False);entry=old.get('entry_quote');opening=old.get('decision');f=old['candidate']['funding']
   if old['status']!='ENTRY_SELECTED':raise ValueError('close decision requires an admitted entry')
   basis=dict(schema='terminan.paper.close-decision-input.v2',opening_decision_sha256=opening['sha256'],entry_quote_sha256=entry['sha256'],risk_sha256=_hash(old['risk_receipt']),hold_ms=self.policy['hold_ms'])
   if d['source_id']!='terminan_paper_close_decision' or d['raw_sha256']!=_hash(basis) or d['symbol']!=opening['symbol'] or not entry['observed_ms']+self.policy['hold_ms']<=d['observed_ms']<=d['decision_ms']==now_ms or d['expires_ms']!=now_ms+self.policy['exit_wait_ms'] or d['expires_ms']>=f['next_ms']:raise ValueError('risk-bound close decision refused')
   expected.update(status=status,close_decision=d)
  elif status=='CLOSE_READY':
   from .causal_replay import prepare_causal_request,calculate_causal_receipt
   q=prepare_causal_request(record.get('request'),now_ms=record.get('admitted_ms'));c=old['candidate'];p=self.policy
   policy=dict(notional=p['notional_usdt'],fee_bps=p['fee_bps'],slippage_bps=p['slippage_bps'],latency_ms=p['latency_ms'],max_quote_age_ms=p['max_quote_age_ms'],max_hold_ms=p['hold_ms']+p['exit_wait_ms'])
   if old['status']!='EXIT_DECIDED' or record['admitted_ms']!=now_ms or q['request_id']!=c['id'] or q['symbol']!=c['signal']['symbol'] or q['signal']!=old['decision'] or q['close_signal']!=old['close_decision'] or q['quotes'][0]!=old['entry_quote'] or q['funding']!=c['funding'] or q['policy']!=policy or any(q[k]!=c[k] for k in ('strategy','strategy_revision','evidence_class')):raise ValueError('recorded causal close intent mismatch')
   calculate_causal_receipt(q,now_ms=record['admitted_ms']);expected.update(status=status,request=q,admitted_ms=record['admitted_ms'])
  elif status=='SETTLED':
   if old['status'] not in ('CLOSE_READY','UNCERTAIN') or 'request' not in old or type(record.get('result_sha256')) is not str or re.fullmatch('[a-f0-9]{64}',record['result_sha256']) is None or record.get('settled_at_ms')!=now_ms or type(record.get('settled_at_ms')) is not int or record.get('settled_sequence')!=sequence or type(record.get('settled_sequence')) is not int:raise ValueError('verified causal settlement required')
   expected.update(status=status,result_sha256=record['result_sha256'],settled_at_ms=now_ms,settled_sequence=sequence)
  else:raise ValueError('unsupported causal progression')
  if record!=expected:raise ValueError('closed causal progression fields refused')
 def _record_progress(self,request_id,key,value,status,*,now_ms):
  from .causal_replay import label
  from .causal_quotes import _clock
  label(request_id);_clock(now_ms)
  if key=='entry_quote':self._quote(value)
  else:self._decision(value,opening=(key=='decision'))
  value=json.loads(canonical_json(value))
  with self._transaction() as (db,(records,last,sequence,previous,rows)):
   old=records[request_id]
   if key in old:
    if old[key]!=value:raise ValueError('causal progression identity collision')
    return copy.deepcopy(old)
   if now_ms<last:raise ValueError('causal clock regressed')
   record=copy.deepcopy(old);record.update(status=status,**{key:value});self._progress(old,record,now_ms,sequence+1);self._event(db,record,now_ms,sequence,previous);return copy.deepcopy(record)
 def record_decision(self,request_id,decision,*,now_ms):return self._record_progress(request_id,'decision',decision,'DECIDED',now_ms=now_ms)
 def record_entry(self,request_id,quote,*,now_ms):return self._record_progress(request_id,'entry_quote',quote,'ENTRY_SELECTED',now_ms=now_ms)
 def record_exit_decision(self,request_id,decision,*,now_ms):return self._record_progress(request_id,'close_decision',decision,'EXIT_DECIDED',now_ms=now_ms)

 def _result_rows(self):
  rows={}
  with PaperReplayLedger._existing_database(self.root/'results.sqlite') as db:
   if db is None:raise ValueError('missing completed ledger')
   if tuple(db.execute("SELECT name FROM sqlite_schema WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"))!=(('paper_replay_receipts',),):raise ValueError('foreign completed schema refused')
   if db.execute('SELECT count(*) FROM paper_replay_receipts').fetchone()[0]>200 or db.execute('SELECT 1 FROM paper_replay_receipts WHERE length(CAST(receipt AS BLOB))>300000 LIMIT 1').fetchone():raise ValueError('completed receipt capacity refused')
   for ident,pin in db.execute('SELECT run_id,request_sha256 FROM paper_replay_receipts ORDER BY rowid'):
    rows[ident]=PaperReplayLedger._read(db,ident,pin)
    if db.execute('SELECT receipt FROM paper_replay_receipts WHERE run_id=?',(ident,)).fetchone()[0]!=canonical_json(rows[ident]).decode():raise ValueError('noncanonical completed receipt refused')
  return rows
 def _verify_results(self,records,rows):
  from .causal_replay import calculate_causal_receipt
  for ident,row in rows.items():
   old=records.get(ident)
   if old is None or old['status'] not in ('CLOSE_READY','UNCERTAIN','SETTLED') or 'request' not in old or row['request_sha256']!=_hash(old['request']) or old.get('result_sha256') not in (None,row['result_sha256']):raise ValueError('foreign completed receipt without exact close intent')
   expected=calculate_causal_receipt(old['request'],now_ms=old['admitted_ms'])
   if expected!=row:raise ValueError('completed receipt differs from sole PaperEngine verification')
  if any(r['status']=='SETTLED' and ident not in rows for ident,r in records.items()):raise ValueError('settled result is missing')
 def _reconcile(self,db,records,rows,now_ms,sequence,previous):
  self._verify_results(records,rows)
  for ident,row in rows.items():
   old=records[ident]
   if old['status']!='SETTLED':
    record=copy.deepcopy(old);record.update(status='SETTLED',result_sha256=row['result_sha256'],settled_at_ms=now_ms,settled_sequence=sequence+1)
    self._progress(old,record,now_ms,sequence+1);sequence,previous=self._event(db,record,now_ms,sequence,previous);records[ident]=record
  return sequence,previous
 def _before_result_commit(self):pass  # Pure-test crash boundary only.
 def _after_result_commit(self):pass  # Pure-test acknowledgement boundary only.
 def close_trade(self,request,*,now_ms):
  from .causal_replay import bound_causal_request,prepare_causal_request,calculate_causal_receipt
  from .causal_quotes import _clock
  _clock(now_ms);request=bound_causal_request(request);ident=request['request_id'];first=False
  with self._transaction() as (db,(records,last,sequence,previous,rows)):
   old=records[ident]
   if old['status']=='SETTLED':
    if request!=old['request']:raise ValueError('completed close identity collision')
    return copy.deepcopy(rows[ident])
   if now_ms<last:raise ValueError('causal clock regressed')
   if old['status'] in ('CLOSE_READY','UNCERTAIN'):
    if old.get('request')!=request:raise ValueError('close intent identity collision')
    if ident not in rows:raise ValueError('CLOSE_INTENT_UNKNOWN_NO_REEXECUTION')
    self._reconcile(db,records,rows,now_ms,sequence,previous);return copy.deepcopy(rows[ident])
   result=calculate_causal_receipt(request,now_ms=now_ms)
   if self.root.joinpath('results.sqlite').stat().st_size+4*len(canonical_json(result))+65536>2*1024*1024:raise ValueError('completed receipt capacity refused')
   record=copy.deepcopy(old);record.update(status='CLOSE_READY',request=request,admitted_ms=now_ms)
   self._progress(old,record,now_ms,sequence+1);self._event(db,record,now_ms,sequence,previous);first=True
  # Intent is durable first. Result publication holds the state writer lock so
  # another admission cannot ignore a concurrently committed loss/profit.
  with self._transaction() as (db,(records,last,sequence,previous,rows)):
   old=records[ident]
   if not first or old['status']!='CLOSE_READY' or old['request']!=request:raise ValueError('causal intent custody changed')
   if ident in rows:raise ValueError('CLOSE_RESULT_UNKNOWN_NO_REEXECUTION')
   if len(rows)>=200:raise ValueError('completed receipt capacity refused')
   result=calculate_causal_receipt(request,now_ms=old['admitted_ms'])
   if self.root.joinpath('results.sqlite').stat().st_size+4*len(canonical_json(result))+65536>2*1024*1024:raise ValueError('completed receipt capacity refused')
   _current(self.require_current);self._before_result_commit()
   self._results.record(result);self._after_result_commit();_current(self.require_current)
   rows=self._result_rows();self._verify_results(records,rows);self._reconcile(db,records,rows,now_ms,sequence,previous)
   return copy.deepcopy(rows[ident])
 def reconcile(self,*,now_ms):
  from .causal_quotes import _clock
  _clock(now_ms)
  with self._transaction() as (db,(records,last,sequence,previous,rows)):
   if now_ms<last:raise ValueError('causal clock regressed')
   self._reconcile(db,records,rows,now_ms,sequence,previous)

"""Fresh-owned offline causal account namespace, backed by existing receipt ledgers.
Ownership is an external local custody receipt, never source authentication.
This foundation intentionally exposes no reserve/settle operation yet.
"""
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import json,os,re,stat,uuid
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
 def _verify(self):
  _current(self.require_current)
  if _identity(self.root,directory=True)!=self.ownership.root_identity:raise ValueError('account directory identity changed')
  names=[]
  for child in self.root.iterdir():
   names.append(child.name)
   if len(names)>2:raise ValueError('foreign account namespace content')
  if set(names)!={'state.sqlite','results.sqlite'}:raise ValueError('incomplete account namespace')
  for name,expected in (('state.sqlite',self.ownership.state_identity),('results.sqlite',self.ownership.results_identity)):
   target=self.root/name
   if _identity(target)!=expected or not 100<=target.stat().st_size<=2*1024*1024:raise ValueError('account file identity or budget changed')
   with PaperReplayLedger._existing_database(target) as db:
    if db is None:raise ValueError('missing account ledger')
    if db.execute('SELECT count(*) FROM paper_replay_receipts').fetchone()[0]!=(1 if name=='state.sqlite' else 0):raise ValueError('unsupported causal account progression')
    if name=='state.sqlite':
     receipt=PaperReplayLedger._read(db,'causal-account-initial',self.ownership.policy_sha256)
     if receipt is None or receipt.get('schema')!='terminan.paper.causal-account.initial.v2' or receipt.get('account_id')!=self.ownership.account_id or receipt.get('policy')!=self.policy:raise ValueError('account ownership binding mismatch')
  _current(self.require_current)
 def snapshot(self):
  self._verify()
  from market_math import paper_account_balances
  value=paper_account_balances(Decimal(self.policy['initial_cash_usdt']),(),(),())
  return dict(schema='terminan.paper.causal-account.snapshot.v2',account_id=self.ownership.account_id,sequence=0,cash_usdt=str(value.cash),peak_usdt=str(value.peak),reserved_usdt=str(value.reserved),available_usdt=str(value.available_cash),execution_authority=False,trading_authorized=False,source_authenticity='NOT_EVALUATED',state='INITIALIZED_ONLY')

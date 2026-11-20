"""Pure bounded reader for canonical causal paper artifacts; no I/O/authority.
Receipt numerics are replay-verified. Account balances remain producer claims:
this artifact does not contain the policy/state journal needed to derive them.
"""
import json,re
from hashlib import sha256
from .paper_ledger import canonical_json
from .causal_replay import fields,bound_causal_request,calculate_causal_receipt
from .causal_quotes import _clock,_decimal_value
ARTIFACT_SCHEMA='terminan.paper.causal-ledger.v2'
BALANCES_BASIS='PRODUCER_CLAIMED_LOCAL_ACCOUNT_SNAPSHOT_NOT_RECONSTRUCTABLE_FROM_RECEIPTS'
CONSISTENCY='VERIFIED_LOCAL_READS_NOT_CROSS_DATABASE_ATOMIC'
ARTIFACT_FIELDS=('schema','account_id','policy_sha256','sequence','row_count','rows','balances','balances_basis','consistency','source_authenticity','point_in_time_availability','execution_authority','trading_authorized')
RESULT_FIELDS=('schema','run_id','request_sha256','request','admitted_ms','symbol','strategy','strategy_revision','evidence_class','units','entry_ts_ms','exit_ts_ms','metrics','status','provenance','source_authenticity','point_in_time_availability','model','execution_authority','trading_authorized','training_authorized','paper_eligible','result_sha256')
METRIC_FIELDS=('entry_price','exit_price','qty','signed_qty','gross_raw','gross_fill','slippage','fees','funding','net')
def _refuse(*args):raise ValueError('noncanonical causal artifact scalar')
def _pairs(items):
 if len(items)>32:raise ValueError('causal artifact object cardinality')
 out={}
 for key,value in items:
  if type(key) is not str or not 1<=len(key)<=64 or key in out:raise ValueError('duplicate or oversized causal artifact key')
  out[key]=value
 return out

def validate_causal_ledger_artifact(raw:bytes,*,expected_sha256:str)->dict:
 """Return fresh decoded data only after byte/hash/shape/receipt replay checks.

 A caller-selected SHA establishes byte identity, not source authenticity.
 No database, filesystem, transport, callback grant or financial state exists.
 """
 if type(raw) is not bytes or not 0<len(raw)<=4*1024*1024:raise ValueError('bounded causal artifact bytes required')
 if type(expected_sha256) is not str or len(expected_sha256)!=64 or re.fullmatch('[a-f0-9]{64}',expected_sha256) is None:raise ValueError('explicit causal artifact digest required')
 if sha256(raw).hexdigest()!=expected_sha256:raise ValueError('causal artifact digest mismatch')
 try:value=json.loads(raw,object_pairs_hook=_pairs,parse_float=_refuse,parse_constant=_refuse)
 except (UnicodeError,ValueError,RecursionError) as exc:raise ValueError('closed canonical artifact JSON required') from exc
 fields(value,ARTIFACT_FIELDS)
 if value['schema']!=ARTIFACT_SCHEMA or type(value['schema']) is not str or type(value['account_id']) is not str or re.fullmatch('[a-f0-9]{32}',value['account_id']) is None or type(value['policy_sha256']) is not str or re.fullmatch('[a-f0-9]{64}',value['policy_sha256']) is None:raise ValueError('canonical paper artifact identity required')
 if type(value['sequence']) is not int or not 0<=value['sequence']<=4096 or type(value['row_count']) is not int or not 0<=value['row_count']<=200 or type(value['rows']) is not list or len(value['rows'])!=value['row_count']:raise ValueError('bounded paper artifact rows required')
 fixed={'balances_basis':BALANCES_BASIS,'consistency':CONSISTENCY,'source_authenticity':'NOT_EVALUATED','point_in_time_availability':'UNKNOWN','execution_authority':False,'trading_authorized':False}
 if any(type(value[k]) is not type(expected) or value[k]!=expected for k,expected in fixed.items()):raise ValueError('unqualified causal artifact evidence required')
 fields(value['balances'],('cash_usdt','peak_usdt','reserved_usdt','available_usdt'))
 for number in value['balances'].values():
  if type(number) is not str or len(number)>256 or len(_decimal_value(number).as_tuple().digits)>128:raise ValueError('bounded producer-claimed balance representation required')
 seen=set()
 for row in value['rows']:
  fields(row,RESULT_FIELDS)
  for key in ('admitted_ms','entry_ts_ms','exit_ts_ms'):_clock(row[key])
  for key in ('execution_authority','trading_authorized','training_authorized'):
   if row[key] is not False:raise ValueError('paper result authority upgrade refused')
  for key in set(RESULT_FIELDS)-{'request','units','metrics','admitted_ms','entry_ts_ms','exit_ts_ms','execution_authority','trading_authorized','training_authorized'}:
   if type(row[key]) is not str or not 1<=len(row[key])<=256:raise ValueError('bounded result metadata required')
  for key in ('result_sha256','request_sha256'):
   if re.fullmatch('[a-f0-9]{64}',row[key]) is None:raise ValueError('bounded result digest required')
  fields(row['units'],('price','qty'))
  if any(type(v) is not str or not 1<=len(v)<=64 for v in row['units'].values()):raise ValueError('bounded result unit required')
  fields(row['metrics'],METRIC_FIELDS)
  for number in row['metrics'].values():_decimal_value(number)
  request=bound_causal_request(row['request'])
  if row['run_id']!=request['request_id'] or row['run_id'] in seen:raise ValueError('duplicate or mismatched paper result')
  seen.add(row['run_id']);expected=calculate_causal_receipt(request,now_ms=row['admitted_ms'])
  if canonical_json(row)!=canonical_json(expected):raise ValueError('paper receipt differs from canonical replay')
 if canonical_json(value)!=raw:raise ValueError('noncanonical causal artifact JSON')
 return value

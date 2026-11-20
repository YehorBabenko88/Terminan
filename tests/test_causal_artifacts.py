import copy,hashlib,json,unittest
from unittest.mock import patch
from terminan.causal_replay import calculate_causal_receipt,digest
from terminan.paper_ledger import canonical_json
from test_causal_receipt import request
from test_causal_quote_schedule import fixture

def artifact():
 row=calculate_causal_receipt(request(),now_ms=fixture()['now_ms'])
 return dict(schema='terminan.paper.causal-ledger.v2',account_id='a'*32,policy_sha256='b'*64,sequence=7,row_count=1,rows=[row],balances=dict(cash_usdt='10000',peak_usdt='10000',reserved_usdt='0',available_usdt='10000'),balances_basis='PRODUCER_CLAIMED_LOCAL_ACCOUNT_SNAPSHOT_NOT_RECONSTRUCTABLE_FROM_RECEIPTS',consistency='VERIFIED_LOCAL_READS_NOT_CROSS_DATABASE_ATOMIC',source_authenticity='NOT_EVALUATED',point_in_time_availability='UNKNOWN',execution_authority=False,trading_authorized=False)
class CausalArtifactTests(unittest.TestCase):
 def validate(self,value):
  from terminan.causal_artifacts import validate_causal_ledger_artifact
  raw=canonical_json(value);return validate_causal_ledger_artifact(raw,expected_sha256=hashlib.sha256(raw).hexdigest())
 def test_pure_reader_replays_actual_receipt_and_keeps_balance_claim_honest(self):
  a=artifact();b=self.validate(a);self.assertEqual(a,b);b['rows'][0]['metrics']['net']='changed';self.assertEqual(self.validate(a),a);a['balances']['cash_usdt']='12345';self.assertEqual(self.validate(a)['balances']['cash_usdt'],'12345');self.assertIn('NOT_RECONSTRUCTABLE',self.validate(a)['balances_basis']);self.assertFalse(self.validate(a)['execution_authority'])
 def test_hash_valid_changed_financial_result_or_original_admission_refuses(self):
  for change in ('net','admitted','digest'):
   a=artifact();r=a['rows'][0]
   if change=='net':r['metrics']['net']='9999'
   elif change=='admitted':r['admitted_ms']=True
   else:r['request_sha256']='0'*64
   r.pop('result_sha256');r['result_sha256']=digest(r)
   with self.subTest(change=change),self.assertRaises(ValueError):self.validate(a)
 def test_duplicate_keys_unknown_fields_and_noncanonical_json_refuse(self):
  from terminan.causal_artifacts import validate_causal_ledger_artifact
  raw=canonical_json(artifact())
  for bad in (b' '+raw,raw[:-1]+b',"schema":"terminan.paper.causal-ledger.v2"}',raw[:-1]+b',"extra":0}'):
   with self.assertRaises(ValueError):validate_causal_ledger_artifact(bad,expected_sha256=hashlib.sha256(bad).hexdigest())
 def test_raw_byte_and_row_cardinality_bounds_precede_hash_or_replay(self):
  from terminan.causal_artifacts import validate_causal_ledger_artifact
  with patch('terminan.causal_artifacts.sha256',side_effect=AssertionError('NO_OVERSIZED_HASH')),self.assertRaises(ValueError):validate_causal_ledger_artifact(b' '*(4*1024*1024+1),expected_sha256='a'*64)
  a=artifact();a['rows']=[{}]*100001;a['row_count']=100001
  with patch('terminan.causal_artifacts.calculate_causal_receipt',side_effect=AssertionError('NO_OVERSIZED_REPLAY')),self.assertRaises(ValueError):self.validate(a)
 def test_declared_authority_or_balance_type_upgrade_is_refused(self):
  for key,value in (('execution_authority',True),('point_in_time_availability','VERIFIED'),('balances_basis','INDEPENDENTLY_VERIFIED'),('row_count',True),('balances',dict(cash_usdt=True,peak_usdt='10000',reserved_usdt='0',available_usdt='10000'))):
   a=artifact();a[key]=value
   with self.subTest(key=key),self.assertRaises(ValueError):self.validate(a)

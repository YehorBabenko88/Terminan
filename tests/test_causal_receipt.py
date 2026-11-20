import copy,unittest
from decimal import Decimal,localcontext
from unittest.mock import patch
from test_causal_quote_schedule import fixture
from terminan.causal_replay import prepare_causal_request,calculate_causal_receipt,digest

def request():
 a=fixture()
 return dict(schema='terminan.paper.causal-quote.request.v2',request_id='causal-1',strategy='causal_quote',strategy_revision='1'*40,evidence_class='SYNTHETIC',symbol='BTCUSDT',units={'price':'USDT/BTC','qty':'BTC'},policy={'notional':'100','fee_bps':'10','slippage_bps':'10','latency_ms':a['latency_ms'],'max_quote_age_ms':a['max_quote_age_ms'],'max_hold_ms':a['max_hold_ms']},signal=a['open_decision'],close_signal=a['close_decision'],quotes=a['quotes'],funding=a['funding'])
class CausalReceiptTests(unittest.TestCase):
 def test_pure_receipt_uses_one_engine_and_is_deterministic_without_input_mutation(self):
  q=request();before=copy.deepcopy(q);a=calculate_causal_receipt(q,now_ms=fixture()['now_ms']);b=calculate_causal_receipt(q,now_ms=fixture()['now_ms']);self.assertEqual(a,b);self.assertEqual(q,before);self.assertEqual(a['request_sha256'],digest(q));self.assertFalse(a['execution_authority']);self.assertEqual(a['point_in_time_availability'],'UNKNOWN');self.assertEqual(a['source_authenticity'],'NOT_EVALUATED');self.assertEqual(a['schema'],'terminan.paper.causal-quote.result.v2')
 def test_closed_top_level_and_policy_refuse_before_serialization(self):
  for target in ('request','policy'):
   q=request();(q if target=='request' else q['policy'])['extra']='x'*5000000
   with patch('terminan.causal_replay.canonical_json',side_effect=AssertionError('MUST_NOT_SERIALIZE')),self.assertRaises(ValueError):prepare_causal_request(q,now_ms=fixture()['now_ms'])
 def test_canonical_strategy_and_units_have_no_legacy_alias(self):
  for field,value in (('strategy','meta.poc.next_minute'),('strategy','strattester'),('units',{'price':'USD','qty':'BTC'}),('evidence_class',True)):
   q=request();q[field]=value
   with self.subTest(field=field,value=value),self.assertRaises(ValueError):calculate_causal_receipt(q,now_ms=fixture()['now_ms'])
 def test_disabled_math_capability_cannot_emit_receipt(self):
  with patch('market_math.paper_quote_funding_valid',None),self.assertRaises(ValueError):calculate_causal_receipt(request(),now_ms=fixture()['now_ms'])
 def test_hostile_ambient_context_cannot_change_receipt(self):
  q=request();expected=calculate_causal_receipt(q,now_ms=fixture()['now_ms'])
  with localcontext() as c:
   c.prec=1;c.Emax=2;c.Emin=-2
   for signal in c.traps:c.traps[signal]=True
   c.clear_flags();actual=calculate_causal_receipt(q,now_ms=fixture()['now_ms']);self.assertEqual(actual,expected);self.assertFalse(any(c.flags.values()))

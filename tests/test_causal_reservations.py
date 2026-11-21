import copy,unittest
from dataclasses import replace
import test_causal_account as account_helpers
from decimal import Decimal
policy=account_helpers.policy
from test_causal_quote_schedule import receipt
class ReservationTests(unittest.TestCase):
 setUp=account_helpers.CausalAccountOwnershipTests.setUp
 create=account_helpers.CausalAccountOwnershipTests.create
 def candidate(self,ident='r1',side='long'):
  return dict(request_id=ident,signal=receipt('signal-'+ident,decision_ms=100,observed_ms=99,expires_ms=600,side=side),strategy='causal_quote',strategy_revision='1'*40,evidence_class='SYNTHETIC',reference_quote=receipt('reference-'+ident,epoch='e',sequence=1,event_ms=95,observed_ms=96,bid='100',ask='100.1'),funding=receipt('funding-'+ident,kind='COMPLETE_INTERVAL',observed_ms=90,previous_ms=0,next_ms=2000,interval_ms=2000,events=[]),now_ms=100)
 def reserve(self,account,candidate):
  c=copy.deepcopy(candidate);ident=c.pop('request_id');return account.reserve(ident,**c)
 def test_reservation_is_durable_exact_retry_and_uses_math_collateral(self):
  from terminan.causal_account import CausalAccountJournal
  a=self.create();c=self.candidate();r=self.reserve(a,c);self.assertTrue(r['accepted']);self.assertEqual(Decimal(r['collateral_usdt']),Decimal('100.1'));first=a.snapshot();self.assertEqual(Decimal(first['reserved_usdt']),Decimal('100.1'));self.assertEqual(self.reserve(a,c),r);self.assertEqual(a.snapshot(),first)
  b=CausalAccountJournal.open(self.root,policy(),ownership=a.ownership,require_current=lambda:True);self.assertEqual(b.snapshot(),first)
 def test_long_only_and_symbol_reservation_denial_do_not_release_collateral(self):
  a=self.create();self.assertEqual(self.reserve(a,self.candidate('short','short'))['reason'],'LONG_ONLY');self.assertEqual(a.snapshot()['reserved_usdt'],'0');self.reserve(a,self.candidate());self.assertEqual(self.reserve(a,self.candidate('r2'))['reason'],'SYMBOL_RESERVED');self.assertEqual(Decimal(a.snapshot()['reserved_usdt']),Decimal('100.1'))
 def test_uncertain_gap_retains_collateral_after_restart(self):
  from terminan.causal_account import CausalAccountJournal
  a=self.create();self.reserve(a,self.candidate());a.mark_uncertain('r1','SOURCE_GAP',now_ms=101);b=CausalAccountJournal.open(self.root,policy(),ownership=a.ownership,require_current=lambda:True);self.assertEqual(Decimal(b.snapshot()['reserved_usdt']),Decimal('100.1'));self.assertEqual(b.snapshot()['reservations'][0]['status'],'UNCERTAIN')
 def test_conflicting_retry_and_invalid_last_field_do_not_write(self):
  a=self.create();self.reserve(a,self.candidate());before={p.name:p.read_bytes() for p in self.root.iterdir()};changed=self.candidate();changed['evidence_class']='LIVE'
  with self.assertRaises(ValueError):self.reserve(a,changed)
  malformed=self.candidate('r2');malformed['reference_quote']['ask']='x'*5000000
  with self.assertRaises(ValueError):self.reserve(a,malformed)
  self.assertEqual({p.name:p.read_bytes() for p in self.root.iterdir()},before)

 def test_spread_staleness_and_funding_refusal_are_durable_denials(self):
  from test_causal_quote_schedule import seal
  from terminan.causal_account import CausalAccountJournal
  for ident,changes,expected in (('spread',{'bid':'100','ask':'102'},'SPREAD_LIMIT'),('stale',{'event_ms':0,'observed_ms':1},'STALE_QUOTE')):
   c=self.candidate(ident);q=dict(c['reference_quote']);q.pop('sha256');q.update(changes);c['reference_quote']=seal(q)
   if ident=='stale':c['now_ms']=550
   p=policy();p['max_quote_age_ms']=100;a=CausalAccountJournal.create(self.root,p,require_current=lambda:True);self.assertEqual(self.reserve(a,c)['reason'],expected);self.assertEqual(a.snapshot()['reserved_usdt'],'0');self.temp.cleanup();self.setUp()
 def test_revocation_before_transaction_commit_rolls_back_exact_state_bytes(self):
  from unittest.mock import patch
  a=self.create();before={p.name:p.read_bytes() for p in self.root.iterdir()};original=a._event
  def revoke_after_insert(*args,**kwargs):
   original(*args,**kwargs);a.require_current=lambda:False
  with patch.object(a,'_event',side_effect=revoke_after_insert),self.assertRaises(ValueError):self.reserve(a,self.candidate())
  self.assertEqual({p.name:p.read_bytes() for p in self.root.iterdir()},before)
 def test_hash_valid_foreign_completed_receipt_blocks_without_adoption(self):
  from terminan.causal_replay import calculate_causal_receipt
  from test_causal_receipt import request
  from test_causal_quote_schedule import fixture
  a=self.create();a._results.record(calculate_causal_receipt(request(),now_ms=fixture()['now_ms']));before={p.name:p.read_bytes() for p in self.root.iterdir()}
  with self.assertRaises(ValueError):a.snapshot()
  with self.assertRaises(ValueError):self.reserve(a,self.candidate())
  self.assertEqual({p.name:p.read_bytes() for p in self.root.iterdir()},before)
 def test_hostile_context_preserves_math_risk_decision(self):
  from decimal import localcontext
  a=self.create()
  with localcontext() as c:
   c.prec=1;c.Emax=2;c.Emin=-2
   for signal in c.traps:c.traps[signal]=True
   c.clear_flags();r=self.reserve(a,self.candidate());self.assertTrue(r['accepted']);self.assertEqual(Decimal(a.snapshot()['reserved_usdt']),Decimal('100.1'));self.assertFalse(any(c.flags.values()))

 def test_misordered_policy_is_refused_before_any_namespace(self):
  from terminan.causal_account import CausalAccountJournal
  for changes in ({'max_reserved_usdt':'99'},{'initial_cash_usdt':'1000'},{'max_drawdown_fraction':'1'},{'max_spread_bps':'0'},{'latency_ms':500}):
   p=policy();p.update(changes)
   with self.subTest(changes=changes),self.assertRaises(ValueError):CausalAccountJournal.create(self.root,p,require_current=lambda:True)
   self.assertFalse(self.root.exists())
 def test_missing_funding_is_denied_without_reserved_collateral(self):
  a=self.create();c=self.candidate();c['funding']=None;self.assertEqual(self.reserve(a,c)['reason'],'FUNDING_UNPROVEN');self.assertEqual(a.snapshot()['reserved_usdt'],'0')

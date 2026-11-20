import copy,unittest
from decimal import Decimal
from unittest.mock import patch
import test_causal_account as account_helpers
import test_causal_reservations as reservations
from test_causal_quote_schedule import receipt,seal
from terminan.causal_replay import digest
class SettlementTests(unittest.TestCase):
 setUp=account_helpers.CausalAccountOwnershipTests.setUp
 create=account_helpers.CausalAccountOwnershipTests.create
 candidate=reservations.ReservationTests.candidate
 reserve=reservations.ReservationTests.reserve
 def prepared(self,policy=None,after_reserve=None):
  from terminan.causal_account import CausalAccountJournal
  a=self.create() if policy is None else CausalAccountJournal.create(self.root,policy,require_current=lambda:True)
  c=self.candidate();risk=self.reserve(a,c)
  if after_reserve:after_reserve(a)
  decision=receipt('admitted-open',decision_ms=101,observed_ms=100,expires_ms=600,side='long');decision.pop('sha256');decision['source_id']='terminan_paper_risk_decision';decision['raw_sha256']=digest(dict(schema='terminan.paper.risk-decision-input.v2',proposal_sha256=c['signal']['sha256'],risk_sha256=digest(risk)));decision=seal(decision)
  a.record_decision('r1',decision,now_ms=101)
  entry=receipt('fresh-entry',epoch='e',sequence=2,event_ms=111,observed_ms=112,bid='99.9',ask='100');a.record_entry('r1',entry,now_ms=112)
  close=receipt('admitted-close',decision_ms=300,observed_ms=300,expires_ms=800);close.pop('sha256');close['source_id']='terminan_paper_close_decision';close['raw_sha256']=digest(dict(schema='terminan.paper.close-decision-input.v2',opening_decision_sha256=decision['sha256'],entry_quote_sha256=entry['sha256'],risk_sha256=digest(risk),hold_ms=100));close=seal(close);a.record_exit_decision('r1',close,now_ms=300)
  q=dict(schema='terminan.paper.causal-quote.request.v2',request_id='r1',strategy='causal_quote',strategy_revision='1'*40,evidence_class='SYNTHETIC',symbol='BTCUSDT',units={'price':'USDT/BTC','qty':'BTC'},policy={'notional':'100','fee_bps':'10','slippage_bps':'10','latency_ms':10,'max_quote_age_ms':1000,'max_hold_ms':600},signal=decision,close_signal=close,quotes=[entry,receipt('fresh-exit',epoch='e',sequence=3,event_ms=310,observed_ms=311,bid='110',ask='110.1')],funding=c['funding'])
  return a,q
 def test_durable_decisions_fresh_quotes_and_one_completed_receipt(self):
  a,q=self.prepared();r=a.close_trade(q,now_ms=320);s=a.snapshot();self.assertEqual(s['reservations'][0]['status'],'SETTLED');self.assertEqual(Decimal(s['reserved_usdt']),Decimal(0));self.assertEqual(a.close_trade(q,now_ms=321),r);self.assertEqual(r['admitted_ms'],320);self.assertEqual(a.close_trade(q,now_ms=200000),r)
 def test_commit_then_ack_failure_keeps_collateral_and_pending_profit_out_of_peak(self):
  from terminan.causal_account import CausalAccountJournal
  a,q=self.prepared()
  with patch.object(a,'_after_result_commit',side_effect=RuntimeError('ACK_UNKNOWN')),self.assertRaises(RuntimeError):a.close_trade(q,now_ms=320)
  s=a.snapshot();self.assertEqual(s['reservations'][0]['status'],'CLOSE_READY');self.assertGreater(Decimal(s['cash_usdt']),Decimal(10000));self.assertEqual(Decimal(s['peak_usdt']),Decimal(10000));self.assertEqual(Decimal(s['reserved_usdt']),Decimal('100.1'))
  b=CausalAccountJournal.open(self.root,account_helpers.policy(),ownership=a.ownership,require_current=lambda:True)
  with patch.object(b._results,'record',side_effect=AssertionError('NO_REEXECUTION')):b.reconcile(now_ms=400)
  s=b.snapshot();self.assertEqual(s['reservations'][0]['status'],'SETTLED');self.assertGreater(Decimal(s['peak_usdt']),Decimal(10000));self.assertEqual(s['reservations'][0]['admitted_ms'],320);self.assertEqual(s['reservations'][0]['settled_at_ms'],400)
 def test_intent_without_completed_result_is_unknown_and_never_reexecuted(self):
  a,q=self.prepared()
  with patch.object(a,'_before_result_commit',side_effect=RuntimeError('CRASH_BEFORE_RESULT')),self.assertRaises(RuntimeError):a.close_trade(q,now_ms=320)
  with patch.object(a._results,'record',side_effect=AssertionError('NO_REEXECUTION')),self.assertRaises(ValueError):a.close_trade(q,now_ms=321)
  a.reconcile(now_ms=400);s=a.snapshot();self.assertEqual(s['reservations'][0]['status'],'CLOSE_READY');self.assertEqual(Decimal(s['reserved_usdt']),Decimal('100.1'));self.assertEqual(Decimal(s['cash_usdt']),Decimal(10000))
 def test_predecision_or_new_epoch_entry_cannot_advance_or_mutate(self):
  a=self.create();c=self.candidate();self.reserve(a,c);before={p.name:p.read_bytes() for p in self.root.iterdir()}
  for epoch,event in (('e',100),('foreign',111)):
   with self.assertRaises(ValueError):a.record_entry('r1',receipt('entry',epoch=epoch,sequence=2,event_ms=event,observed_ms=event,bid='100',ask='100'),now_ms=112)
  self.assertEqual({p.name:p.read_bytes() for p in self.root.iterdir()},before)

 def test_future_profitable_result_cannot_improve_earlier_drawdown_decision(self):
  from terminan.causal_account import CausalAccountJournal
  seen={}
  def earlier_denial(a):
   c=self.candidate('r2')
   for key in ('signal','reference_quote','funding'):
    r=dict(c[key]);r.pop('sha256');r['symbol']='ETHUSDT';c[key]=seal(r)
   seen['risk']=self.reserve(a,c);self.assertEqual(seen['risk']['reason'],'DRAWDOWN_LIMIT');self.assertEqual(Decimal(seen['risk']['cash_usdt']),Decimal(10000))
  p=account_helpers.policy();p['max_drawdown_fraction']='0.02';a,q=self.prepared(p,after_reserve=earlier_denial);a.close_trade(q,now_ms=320)
  b=CausalAccountJournal.open(self.root,p,ownership=a.ownership,require_current=lambda:True);s=b.snapshot();self.assertGreater(Decimal(s['cash_usdt']),Decimal(10000));denied=next(r for r in s['reservations'] if r['candidate']['id']=='r2');self.assertEqual(denied['risk_receipt'],seen['risk']);self.assertEqual(denied['status'],'DENIED')
 def test_hash_valid_wrong_financial_result_is_not_adopted_or_repaired(self):
  from terminan.causal_replay import calculate_causal_receipt
  a,q=self.prepared()
  with patch.object(a,'_before_result_commit',side_effect=RuntimeError('CRASH')),self.assertRaises(RuntimeError):a.close_trade(q,now_ms=320)
  wrong=calculate_causal_receipt(q,now_ms=320);wrong['metrics']['net']='99999';wrong.pop('result_sha256');wrong['result_sha256']=digest(wrong);a._results.record(wrong);before={p.name:p.read_bytes() for p in self.root.iterdir()}
  with self.assertRaises(ValueError):a.reconcile(now_ms=400)
  self.assertEqual({p.name:p.read_bytes() for p in self.root.iterdir()},before)

 def test_foreign_schema_or_noncanonical_stored_receipt_is_never_adopted(self):
  import sqlite3
  from contextlib import closing
  a=self.create()
  with closing(sqlite3.connect(self.root/'state.sqlite')) as db,db:db.execute('CREATE TABLE foreign_state(secret TEXT)')
  before={p.name:p.read_bytes() for p in self.root.iterdir()}
  with self.assertRaises(ValueError):a.snapshot()
  self.assertEqual({p.name:p.read_bytes() for p in self.root.iterdir()},before)

 def test_noncanonical_hash_valid_initial_json_refuses_without_repair(self):
  import sqlite3
  from contextlib import closing
  a=self.create()
  with closing(sqlite3.connect(self.root/'state.sqlite')) as db,db:db.execute("UPDATE paper_replay_receipts SET receipt=' '||receipt WHERE run_id='causal-account-initial'")
  before={p.name:p.read_bytes() for p in self.root.iterdir()}
  with self.assertRaises(ValueError):a.snapshot()
  self.assertEqual({p.name:p.read_bytes() for p in self.root.iterdir()},before)
 def test_gap_after_entry_keeps_position_collateral_and_blocks_new_close(self):
  a,q=self.prepared();a.mark_uncertain('r1','SOURCE_GAP',now_ms=301);before={p.name:p.read_bytes() for p in self.root.iterdir()}
  with self.assertRaises(ValueError):a.close_trade(q,now_ms=320)
  self.assertEqual({p.name:p.read_bytes() for p in self.root.iterdir()},before);self.assertEqual(Decimal(a.snapshot()['reserved_usdt']),Decimal('100.1'));self.assertEqual(a.snapshot()['reservations'][0]['status'],'UNCERTAIN')

 def test_completed_receipt_forces_full_synchronous_before_publication(self):
  a,q=self.prepared();original=a._results._connect;trace=[]
  def connection():
   db=original();db.execute('PRAGMA synchronous=OFF');db.set_trace_callback(trace.append);return db
  with patch.object(a._results,'_connect',side_effect=connection):a.close_trade(q,now_ms=320)
  commands=[x.strip().upper() for x in trace];self.assertTrue('PRAGMA SYNCHRONOUS = FULL' in commands,'receipt publication must explicitly require FULL durability');self.assertLess(commands.index('PRAGMA SYNCHRONOUS = FULL'),commands.index('BEGIN IMMEDIATE'))

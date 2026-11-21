import copy,hashlib,sqlite3,tempfile,unittest
from pathlib import Path
from contextlib import closing
from dataclasses import replace

def policy():return dict(schema='terminan.paper.causal-account-policy.v2',mode='SYNTHETIC_OFFLINE',long_only=True,initial_cash_usdt='10000',notional_usdt='100',max_reserved_usdt='2000',max_positions=10,max_drawdown_fraction='0.5',max_quote_age_ms=1000,max_spread_bps='100',fee_bps='10',slippage_bps='10',latency_ms=10,entry_wait_ms=500,exit_wait_ms=500,hold_ms=100)
class CausalAccountOwnershipTests(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)/'account'
 def create(self,**kwargs):
  from terminan.causal_account import CausalAccountJournal
  return CausalAccountJournal.create(self.root,policy(),require_current=kwargs.get('current',lambda:True))
 def test_owned_creation_reopen_and_initial_balances_use_existing_ledger(self):
  from terminan.causal_account import CausalAccountJournal
  from terminan.paper_ledger import PaperReplayLedger
  account=self.create();self.assertIs(type(account._state),PaperReplayLedger);self.assertIs(type(account._results),PaperReplayLedger)
  first=account.snapshot();self.assertEqual((first['cash_usdt'],first['reserved_usdt'],first['available_usdt']),('10000','0','10000'));self.assertFalse(first['execution_authority']);self.assertEqual(first['sequence'],0)
  reopened=CausalAccountJournal.open(self.root,policy(),ownership=account.ownership,require_current=lambda:True);self.assertEqual(reopened.snapshot(),first)
 def test_invalid_policy_or_revocation_precedes_all_files(self):
  from terminan.causal_account import CausalAccountJournal
  invalid=policy();invalid['max_positions']=True
  for value,current in ((invalid,lambda:True),(policy(),lambda:1),(policy(),lambda:False)):
   with self.assertRaises(ValueError):CausalAccountJournal.create(self.root,value,require_current=current)
   self.assertFalse(self.root.exists())
 def test_existing_foreign_namespace_is_never_adopted(self):
  self.root.mkdir();foreign=self.root/'foreign';foreign.write_bytes(b'preserve')
  with self.assertRaises(ValueError):self.create()
  self.assertEqual(list(self.root.iterdir()),[foreign]);self.assertEqual(foreign.read_bytes(),b'preserve')
 def test_foreign_owner_changed_policy_and_replaced_file_refuse_without_repair(self):
  from terminan.causal_account import CausalAccountJournal
  account=self.create();before=(self.root/'state.sqlite').read_bytes()
  with self.assertRaises(ValueError):CausalAccountJournal.open(self.root,policy(),ownership=replace(account.ownership,account_id='0'*32),require_current=lambda:True)
  changed=policy();changed['notional_usdt']='101'
  with self.assertRaises(ValueError):CausalAccountJournal.open(self.root,changed,ownership=account.ownership,require_current=lambda:True)
  self.assertEqual((self.root/'state.sqlite').read_bytes(),before)
  path=self.root/'state.sqlite';path.write_bytes(b'')
  with self.assertRaises((ValueError,RuntimeError)):CausalAccountJournal.open(self.root,policy(),ownership=account.ownership,require_current=lambda:True)
  self.assertEqual(path.read_bytes(),b'')

 def test_read_only_reopen_and_snapshot_never_invoke_database_constructor(self):
  from terminan.causal_account import CausalAccountJournal
  from unittest.mock import patch
  account=self.create();before={p.name:p.read_bytes() for p in self.root.iterdir()}
  with patch('terminan.paper_ledger.PaperReplayLedger.__init__',side_effect=AssertionError('NO_DDL_OR_ADOPTION')):
   reopened=CausalAccountJournal.open(self.root,policy(),ownership=account.ownership,require_current=lambda:True);reopened.snapshot()
  self.assertEqual({p.name:p.read_bytes() for p in self.root.iterdir()},before)
 def test_retained_hot_sidecar_refuses_without_cleanup(self):
  from terminan.causal_account import CausalAccountJournal
  account=self.create();side=self.root/'state.sqlite-wal';side.write_bytes(b'not-owned-recovery');before={p.name:p.read_bytes() for p in self.root.iterdir()}
  with self.assertRaises((RuntimeError,ValueError)):CausalAccountJournal.open(self.root,policy(),ownership=account.ownership,require_current=lambda:True)
  self.assertEqual({p.name:p.read_bytes() for p in self.root.iterdir()},before)
 def test_snapshot_requires_current_exact_literal_true(self):
  from terminan.causal_account import CausalAccountJournal
  current=[True];account=CausalAccountJournal.create(self.root,policy(),require_current=lambda:current[0]);before={p.name:p.read_bytes() for p in self.root.iterdir()}
  current[0]=1
  with self.assertRaises(ValueError):account.snapshot()
  self.assertEqual({p.name:p.read_bytes() for p in self.root.iterdir()},before)

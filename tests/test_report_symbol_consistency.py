"""Instrument consistency of caller-supplied modeled executions, not origin proof."""
import unittest
from dataclasses import replace
from unittest.mock import patch
import test_research_reporting as fixtures

class ReportSymbolConsistencyTests(unittest.TestCase):
 def fixture(self):return fixtures.ResearchReportingTests().evaluation()
 def changed(self,source,*,dataset=None,entry=None,underlying=None,pair_entry=None,pair_signal=None,fill=None,nonfilled=None):
  from terminan.research_evaluation import EvaluationDisposition
  base_entry=source.entries[0];base_out=source.evaluation.outcomes[0];base_pair=source.outcomes[0]
  new_entry=base_entry if entry is None else replace(base_entry,signal=replace(base_entry.signal,symbol=entry))
  new_under=base_out if underlying is None else replace(base_out,signal=replace(base_out.signal,symbol=underlying))
  new_pair_entry=base_pair.entry if pair_entry is None else replace(base_pair.entry,signal=replace(base_pair.entry.signal,symbol=pair_entry))
  new_pair_out=base_pair.outcome if pair_signal is None else replace(base_pair.outcome,signal=replace(base_pair.outcome.signal,symbol=pair_signal))
  if fill is not None:
   new_under=replace(new_under,execution=replace(new_under.execution,fill=replace(new_under.execution.fill,symbol=fill)))
   new_pair_out=replace(new_pair_out,execution=replace(new_pair_out.execution,fill=replace(new_pair_out.execution.fill,symbol=fill)))
  if nonfilled is not None:
   new_under=replace(new_under,disposition=nonfilled,execution=None);new_pair_out=replace(new_pair_out,disposition=nonfilled,execution=None)
  ds=source.evaluation.dataset if dataset is None else replace(source.evaluation.dataset,symbol=dataset)
  return replace(source,entries=(new_entry,),evaluation=replace(source.evaluation,dataset=ds,outcomes=(new_under,)),outcomes=(replace(base_pair,entry=new_pair_entry,outcome=new_pair_out),))
 def refused_before_owners(self,value):
  from terminan import research_reporting as api
  with patch('terminan.research_entry_evaluation._admit',side_effect=AssertionError('RICH_ADMIT_CALLED')),patch('history_statistics.project_decimal_observations',side_effect=AssertionError('MATH_CALLED')),patch('history_statistics.numeric_trade_summary',side_effect=AssertionError('SUMMARY_CALLED')),patch('terminan.research_evaluation.evaluate_research_signals',side_effect=AssertionError('EVAL_CALLED')):
   with self.assertRaises(ValueError):api.build_research_report(value,value_unit='USDT')
 def test_genuine_and_consistently_declared_symbols_keep_no_origin_claim(self):
  from terminan.research_reporting import build_research_report
  source=self.fixture();btc=build_research_report(source,value_unit='USDT');self.assertEqual(btc.trades[0].identity,('BTCUSDT',60000))
  changed=self.changed(source,dataset='ETHUSDT',entry='ETHUSDT',underlying='ETHUSDT',pair_entry='ETHUSDT',pair_signal='ETHUSDT',fill='ETHUSDT')
  eth=build_research_report(changed,value_unit='USDT');self.assertEqual(eth.trades[0].identity,('ETHUSDT',60000));self.assertTrue(hasattr(eth,'execution_basis'));self.assertEqual(eth.execution_basis,'CALLER_SUPPLIED_MODELED_EXECUTIONS_NOT_REEXECUTED');self.assertEqual(eth.source_authentication,'NOT_EVALUATED');self.assertIs(eth.execution_authority,False)
 def test_dataset_entry_outcome_and_fill_symbol_mismatches_refuse_before_owners(self):
  source=self.fixture()
  variants=({'dataset':'ETHUSDT'},{'entry':'ETHUSDT'},{'underlying':'ETHUSDT'},{'pair_entry':'ETHUSDT'},{'pair_signal':'ETHUSDT'},{'fill':'ETHUSDT'},{'entry':'ETHUSDT','underlying':'ETHUSDT','pair_entry':'ETHUSDT','pair_signal':'ETHUSDT'},{'dataset':'ETHUSDT','fill':'ETHUSDT'},{'entry':'ETHUSDT','fill':'ETHUSDT'},{'entry':True,'underlying':True,'pair_entry':True,'pair_signal':True},{'entry':'','underlying':'','pair_entry':'','pair_signal':''})
  for variant in variants:
   with self.subTest(variant=variant):self.refused_before_owners(self.changed(source,**variant))
 def test_nonfilled_all_states_still_require_dataset_and_all_signal_symbols(self):
  from terminan.research_evaluation import EvaluationDisposition
  source=self.fixture()
  for state in (EvaluationDisposition.NOT_FILLED,EvaluationDisposition.POSITION_OCCUPIED,EvaluationDisposition.OUTSIDE_TEST_WINDOW):
   for variant in ({'dataset':'ETHUSDT'},{'entry':'ETHUSDT','underlying':'ETHUSDT','pair_entry':'ETHUSDT','pair_signal':'ETHUSDT'},{'underlying':'ETHUSDT'},{'pair_signal':'ETHUSDT'}):
    with self.subTest(state=state,variant=variant):self.refused_before_owners(self.changed(source,nonfilled=state,**variant))
 def test_same_clock_different_instruments_cannot_alias_trade_identity(self):
  source=self.fixture();other=self.changed(source,entry='ETHUSDT',underlying='ETHUSDT',pair_entry='ETHUSDT',pair_signal='ETHUSDT',fill='ETHUSDT')
  mixed=replace(source,entries=source.entries+other.entries,outcomes=source.outcomes+other.outcomes,evaluation=replace(source.evaluation,outcomes=source.evaluation.outcomes+other.evaluation.outcomes))
  self.refused_before_owners(mixed)
 def test_foreign_symbol_leaves_refuse_without_equality_or_hash_callbacks(self):
  source=self.fixture();calls=[]
  class Foreign(str):
   def __eq__(self,other):calls.append('eq');return str.__eq__(self,other)
   def __hash__(self):calls.append('hash');return str.__hash__(self)
   def __str__(self):calls.append('str');return str.__str__(self)
  for variant in ({'dataset':Foreign('BTCUSDT')},{'entry':Foreign('BTCUSDT')},{'fill':Foreign('BTCUSDT')},{'pair_signal':Foreign('BTCUSDT')}):self.refused_before_owners(self.changed(source,**variant))
  self.assertEqual(calls,[])
 def test_snapshot_keeps_all_symbols_when_first_math_callback_mutates_originals(self):
  from terminan.research_reporting import build_research_report
  import history_statistics as owner
  source=self.fixture();expected=build_research_report(source,value_unit='USDT');original=owner.project_decimal_observations
  def mutate(values):
   object.__setattr__(source.evaluation.dataset,'symbol','ETHUSDT');object.__setattr__(source.entries[0].signal,'symbol','ETHUSDT');object.__setattr__(source.outcomes[0].outcome.execution.fill,'symbol','ETHUSDT');return original(values)
  with patch.object(owner,'project_decimal_observations',side_effect=mutate):actual=build_research_report(source,value_unit='USDT')
  self.assertEqual(actual,expected);self.assertEqual(actual.trades[0].identity,('BTCUSDT',60000))
 def test_pair_execution_fill_is_checked_even_when_underlying_fill_is_consistent(self):
  source=self.fixture();pair=source.outcomes[0];out=pair.outcome;wrong=replace(out,execution=replace(out.execution,fill=replace(out.execution.fill,symbol='ETHUSDT')))
  self.refused_before_owners(replace(source,outcomes=(replace(pair,outcome=wrong),)))

"""Pure reports preserve modeled accounting and caller-declared uncertainty."""
import unittest,importlib.util
from dataclasses import replace
from decimal import Decimal as D
from types import MappingProxyType
from unittest.mock import patch
import test_rich_entry_transfer as fixtures

class ResearchReportingTests(unittest.TestCase):
 def api(self):
  self.assertIsNotNone(importlib.util.find_spec('terminan.research_reporting'),'pure research report missing')
  from terminan import research_reporting as api
  return api
 def evaluation(self,*,fee=D('0.001')):
  f=fixtures.RichEntryTransferTests();return f.evaluate((f.entry(),),fee_rate=fee)
 def build(self,evaluation=None,rows=(),**changes):
  return self.api().build_research_report(self.evaluation() if evaluation is None else evaluation,rows,value_unit='USDT',**changes)
 def declaration(self,evaluation,**changes):
  api=self.api();row=evaluation.outcomes[0]
  return api.DeclaredTradeMetadata(row.entry.signal.symbol,row.entry.decision_ms,row.outcome.known_at_ms,**changes)
 def test_actual_fill_gross_fees_and_net_are_distinct_from_net_gain_partition(self):
  e=self.evaluation();r=self.build(e);fill=e.outcomes[0].outcome.execution.fill
  self.assertEqual(r.trades[0].gross_pnl,fill.gross);self.assertEqual(r.trades[0].net_pnl,fill.net);self.assertEqual(r.trades[0].fees,fill.fees)
  self.assertNotEqual(fill.gross,fill.net);self.assertGreater(r.all_filled.fees_total,0);self.assertEqual(r.all_filled.gross_pnl_total,float(fill.gross));self.assertEqual(r.all_filled.net.numeric.total,float(fill.net))
 def test_unclassified_is_preserved_in_all_filled_and_volatility_partition(self):
  r=self.build();self.assertEqual(r.all_filled.net.numeric.count,1)
  self.assertEqual([p.numeric.net.numeric.count for p in r.by_coverage],[0,0,1]);self.assertEqual(r.by_coverage[-1].trade_ids,(r.trades[0].identity,))
  self.assertEqual(r.by_volatility[0].label,'HIGH');self.assertEqual(r.by_volatility[0].trade_ids,r.by_coverage[-1].trade_ids)
 def test_missing_optional_metrics_remain_none_and_count_zero(self):
  r=self.build();self.assertIsNone(r.all_filled.mae.mean);self.assertEqual(r.all_filled.mae.count,0);self.assertIsNone(r.units.mae);self.assertIsNone(r.trades[0].declaration)
 def test_declared_optional_zero_is_observed_and_requires_explicit_units(self):
  e=self.evaluation();row=self.declaration(e,mae=D(0),mae_unit='PRICE_POINTS',r_multiple=D('-1.2'),r_multiple_unit='DIMENSIONLESS_R_MULTIPLE')
  r=self.build(e,(row,));self.assertEqual((r.all_filled.mae.count,r.all_filled.mae.mean),(1,0.0));self.assertEqual(r.units.mae,'PRICE_POINTS');self.assertEqual(r.all_filled.r_multiple.mean,-1.2)
  with self.assertRaises(ValueError):self.build(e,(replace(row,mae_unit=None),))
  with self.assertRaises(ValueError):self.build(e,(replace(row,mae=None),))
 def test_posthoc_declaration_cannot_precede_actual_dependency_release_or_cutoff(self):
  e=self.evaluation();row=self.declaration(e)
  for clock in (row.available_at_ms-1,180001,True):
   with self.assertRaises(ValueError):self.build(e,(replace(row,available_at_ms=clock),))
  with self.assertRaises(ValueError):self.build(e,(row,),report_as_of_ms=row.available_at_ms-1)
  from terminan.research_evaluation import EvaluationDisposition
  pair=e.outcomes[0];changed=replace(pair.outcome,disposition=EvaluationDisposition.NOT_FILLED,known_at_ms=180001,execution=None)
  future=replace(e,outcomes=(replace(pair,outcome=changed),),evaluation=replace(e.evaluation,outcomes=(changed,)))
  with self.assertRaises(ValueError):self.build(future)
 def test_unused_duplicate_and_nonfilled_metadata_refuse(self):
  e=self.evaluation();row=self.declaration(e)
  for rows in ((row,row),(replace(row,decision_ms=0),),(replace(row,symbol='ETHUSDT'),)):
   with self.assertRaises(ValueError):self.build(e,rows)
 def test_all_graphs_detach_before_first_math_projection_callback(self):
  e=self.evaluation();row=self.declaration(e,mae=D(2),mae_unit='PRICE_POINTS');expected=self.build(e,(row,));import history_statistics as owner
  original=owner.project_decimal_observations
  def mutate(values):
   object.__setattr__(e.outcomes[0].outcome.execution.fill,'gross',D(999));object.__setattr__(row,'mae',D(999));object.__setattr__(e.entries[0].evidence,'volume_ratio',0);return original(values)
  with patch.object(owner,'project_decimal_observations',side_effect=mutate):actual=self.build(e,(row,))
  self.assertEqual(actual,expected)
 def test_foreign_metadata_keys_proxy_referents_and_typed_leaves_never_callback(self):
  e=self.evaluation();calls=[]
  class Key(str):
   def __eq__(self,v):calls.append('eq');return str.__eq__(self,v)
   __hash__=str.__hash__
  class Meta(type):
   def __eq__(self,v):calls.append('meta');return False
  class Leaf(metaclass=Meta):pass
  for metadata in ({Key('unused'):1},{'unused':Leaf()}):
   with patch('history_statistics.project_decimal_observations',side_effect=AssertionError('MATH_CALLED')):
    with self.assertRaises(ValueError):self.build(e,metadata=metadata)
  self.assertEqual(calls,[])
 def test_modeled_holding_uses_execution_bar_starts_not_known_clock(self):
  r=self.build();trade=r.trades[0];self.assertEqual(trade.holding_ms,0);self.assertGreater(trade.outcome.outcome.known_at_ms,trade.exit_ms)
  self.assertEqual(r.holding_basis,'MODELED_BAR_START_DURATION');self.assertEqual((r.all_filled.holding_ms.count,r.all_filled.holding_ms.mean),(1,0.0))
 def test_report_fingerprint_binds_declared_coverage_units_and_control_metadata(self):
  e=self.evaluation();api=self.api();a=self.build(e);b=self.build(e,(self.declaration(e,coverage=api.CoverageDeclaration.COMPLETE_HISTORY),));c=self.build(e,metadata={'note':'caller'})
  self.assertNotEqual(a.input_sha256,b.input_sha256);self.assertNotEqual(a.input_sha256,c.input_sha256);self.assertEqual(a.all_filled,b.all_filled)
 def test_report_never_promotes_declared_completeness_or_authority(self):
  e=self.evaluation();api=self.api();r=self.build(e,(self.declaration(e,coverage=api.CoverageDeclaration.COMPLETE_HISTORY),))
  self.assertEqual(r.coverage_basis,'CALLER_DECLARATIONS_ONLY');self.assertIs(r.completeness_qualified,False);self.assertIs(r.execution_authority,False);self.assertIs(r.trading_authorized,False);self.assertEqual(r.source_authentication,'NOT_EVALUATED')

 def test_malformed_typed_entry_or_verdict_refuses_before_math(self):
  e=self.evaluation()
  for bad in (replace(e,entries=('wrong',)),replace(e,evaluation=replace(e.evaluation,verdict='wrong')),replace(e,evaluation=replace(e.evaluation,folds=('wrong',))),replace(e,evaluation=replace(e.evaluation,numeric='wrong')),replace(e,evaluation=replace(e.evaluation,bootstrap='wrong')),replace(e,evaluation=replace(e.evaluation,numeric=e.evaluation.numeric._replace(gross_profit=True)))):
   with patch('history_statistics.project_decimal_observations',side_effect=AssertionError('MATH_CALLED')):
    with self.assertRaises(ValueError):self.build(bad)
 def test_math_summary_boolean_or_wrong_nested_record_refuses(self):
  import history_statistics as owner
  original=owner.numeric_trade_summary;e=self.evaluation()
  for field,value in (('gross_pnl_total',True),('net','wrong')):
   def altered(rows,field=field,value=value):return original(rows)._replace(**{field:value})
   with patch.object(owner,'numeric_trade_summary',side_effect=altered):
    with self.assertRaises(ValueError):self.build(e)
 def test_nonfinite_math_output_is_refused(self):
  import history_statistics as owner
  original=owner.numeric_trade_summary;e=self.evaluation()
  with patch.object(owner,'numeric_trade_summary',side_effect=lambda rows:original(rows)._replace(fees_total=float('inf'))):
   with self.assertRaises(ValueError):self.build(e)
 def test_metadata_for_nonfilled_outcome_is_unused_and_refused(self):
  from terminan import research_evaluation as owner
  e=self.evaluation();pair=e.outcomes[0];outcome=replace(pair.outcome,disposition=owner.EvaluationDisposition.NOT_FILLED,execution=None);pair=replace(pair,outcome=outcome);e=replace(e,outcomes=(pair,),evaluation=replace(e.evaluation,outcomes=(outcome,)))
  row=self.declaration(e)
  with self.assertRaises(ValueError):self.build(e,(row,))
 def test_duplicate_outcome_or_foreign_flag_does_not_pass_association(self):
  e=self.evaluation();bad=replace(e,outcomes=(e.outcomes[0],e.outcomes[0]))
  with self.assertRaises(ValueError):self.build(bad)
  object.__setattr__(e.evaluation,'point_in_time_qualified',True)
  with self.assertRaises(ValueError):self.build(e)
 def test_callback_mapping_proxy_is_rejected_without_iteration(self):
  from collections.abc import Mapping
  calls=[]
  class Foreign(Mapping):
   def __iter__(self):calls.append('iter');return iter(())
   def __len__(self):calls.append('len');return 0
   def __getitem__(self,key):calls.append('get');raise KeyError(key)
  with self.assertRaises(ValueError):self.build(metadata=MappingProxyType(Foreign()))
  self.assertEqual(calls,[])
 def test_oversized_graph_and_declared_units_are_refused(self):
  e=self.evaluation()
  with self.assertRaises(ValueError):self.build(e,metadata={'oversized':'x'*8388609})
  with self.assertRaises(ValueError):self.api().build_research_report(e,(),value_unit='EUR')
  row=self.declaration(e,r_multiple=D(1),r_multiple_unit='USDT')
  with self.assertRaises(ValueError):self.build(e,(row,))

 def multiple(self,*,delayed=None):
  from terminan.continuation_strategy import CandleBodyObservation,generate_continuation_entries
  from terminan.volatility import VolatilityRegime
  from terminan.research_entry_evaluation import evaluate_research_entries
  from terminan.research_evaluation import EvaluationCandle,EvaluationDataset
  f=fixtures.RichEntryTransferTests();entries=generate_continuation_entries('BTCUSDT',tuple(CandleBodyObservation(i*60000,(i+1)*60000,(i+1)*60000,100,101) for i in range(3)),tuple(f.vol(event_start_ms=i*60000,available_at_ms=(i+1)*60000,regime=regime) for i,regime in enumerate((VolatilityRegime.HIGH,VolatilityRegime.LOW,VolatilityRegime.EXTREME))),as_of_ms=180000)
  rows=tuple(EvaluationCandle(i*60000,(i+1)*60000,delayed if i==1 and delayed is not None else (i+1)*60000,D(101),D(103),D(99),D(101),D(1)) for i in range(6))
  return evaluate_research_entries('volatility_continuation_v2',entries,rows,dataset=EvaluationDataset('a'*64,'BTCUSDT','USDT',0,360000),bar_ms=60000,folds=1,fee_rate=D('0.001'))
 def test_all_filled_and_three_coverage_partitions_conserve_real_trades(self):
  e=self.multiple();api=self.api();rows=tuple(api.DeclaredTradeMetadata(p.entry.signal.symbol,p.entry.decision_ms,p.outcome.known_at_ms,coverage=c) for p,c in zip(e.outcomes,(api.CoverageDeclaration.COMPLETE_HISTORY,api.CoverageDeclaration.PARTIAL_HISTORY,None)))
  r=self.build(e,rows);self.assertEqual(r.all_filled.net.numeric.count,3);self.assertEqual([p.numeric.net.numeric.count for p in r.by_coverage],[1,1,1]);self.assertEqual(len({i for p in r.by_coverage for i in p.trade_ids}),3)
  self.assertEqual(sum(len(p.trade_ids) for p in r.by_volatility),3);self.assertEqual({p.label for p in r.by_volatility},{'HIGH','LOW','EXTREME'})
  from terminan.volatility import VolatilityRegime
  original_primary='tests/research/test_statistics_reporting.py::test_primary_report_excludes_partial_history'
  with self.subTest(original_id=original_primary):
   source=self.original_partition_vector((D(2),D(100)),(VolatilityRegime.HIGH,VolatilityRegime.HIGH))
   declared=tuple(api.DeclaredTradeMetadata(pair.entry.signal.symbol,pair.entry.decision_ms,pair.outcome.known_at_ms,coverage=coverage) for pair,coverage in zip(source.outcomes,(api.CoverageDeclaration.COMPLETE_HISTORY,api.CoverageDeclaration.PARTIAL_HISTORY)))
   report=self.build(source,declared);complete,partial,unknown=report.by_coverage
   self.assertEqual((complete.numeric.net.numeric.count,complete.numeric.net.numeric.total),(1,2.0));self.assertEqual((partial.numeric.net.numeric.count,partial.numeric.net.numeric.total),(1,100.0))
   self.assertEqual(tuple(t.net_pnl for t in report.trades),(D(2),D(100)));self.assertEqual((report.all_filled.net.numeric.count,report.all_filled.net.numeric.total),(2,102.0));self.assertEqual(unknown.trade_ids,())
   self.assertEqual(complete.trade_ids,(report.trades[0].identity,));self.assertEqual(partial.trade_ids,(report.trades[1].identity,));self.assertEqual(set(complete.trade_ids)|set(partial.trade_ids),{t.identity for t in report.trades});self.assertTrue(set(complete.trade_ids).isdisjoint(partial.trade_ids))
   self.assertEqual(report.coverage_basis,'CALLER_DECLARATIONS_ONLY');self.assertIs(report.completeness_qualified,False);self.assertIs(report.execution_authority,False);self.assertIs(report.trading_authorized,False);self.assertEqual(report.source_authentication,'NOT_EVALUATED')
  original_volatility='tests/research/test_statistics_reporting.py::test_volatility_breakdown_keeps_sample_counts_and_coverage_separate'
  with self.subTest(original_id=original_volatility):
   source=self.original_partition_vector((D(2),D(-1),D(3)),(VolatilityRegime.HIGH,VolatilityRegime.LOW,VolatilityRegime.HIGH))
   declared=tuple(api.DeclaredTradeMetadata(pair.entry.signal.symbol,pair.entry.decision_ms,pair.outcome.known_at_ms,coverage=coverage) for pair,coverage in zip(source.outcomes,(api.CoverageDeclaration.COMPLETE_HISTORY,api.CoverageDeclaration.COMPLETE_HISTORY,api.CoverageDeclaration.PARTIAL_HISTORY)))
   report=self.build(source,declared);complete,partial,unknown=report.by_coverage;complete_vol={p.label:p for p in complete.by_volatility};partial_vol={p.label:p for p in partial.by_volatility}
   self.assertEqual(set(complete_vol),{'HIGH','LOW'});self.assertEqual(set(partial_vol),{'HIGH'})
   self.assertEqual((complete_vol['HIGH'].numeric.net.numeric.count,complete_vol['HIGH'].numeric.net.numeric.total),(1,2.0));self.assertEqual((complete_vol['LOW'].numeric.net.numeric.count,complete_vol['LOW'].numeric.net.numeric.total),(1,-1.0));self.assertEqual((partial_vol['HIGH'].numeric.net.numeric.count,partial_vol['HIGH'].numeric.net.numeric.total),(1,3.0))
   self.assertEqual((complete.numeric.net.numeric.count,complete.numeric.net.numeric.total),(2,1.0));self.assertEqual((partial.numeric.net.numeric.count,partial.numeric.net.numeric.total),(1,3.0));self.assertEqual((report.all_filled.net.numeric.count,report.all_filled.net.numeric.total),(3,4.0));self.assertEqual(tuple(t.net_pnl for t in report.trades),(D(2),D(-1),D(3)))
   self.assertEqual(complete_vol['HIGH'].trade_ids,(report.trades[0].identity,));self.assertEqual(complete_vol['LOW'].trade_ids,(report.trades[1].identity,));self.assertEqual(partial_vol['HIGH'].trade_ids,(report.trades[2].identity,));self.assertEqual(unknown.trade_ids,())
   self.assertEqual(set(complete.trade_ids)|set(partial.trade_ids),{t.identity for t in report.trades});self.assertTrue(set(complete.trade_ids).isdisjoint(partial.trade_ids));self.assertEqual(tuple(i for p in complete.by_volatility for i in p.trade_ids),complete.trade_ids)
   self.assertEqual(report.coverage_basis,'CALLER_DECLARATIONS_ONLY');self.assertIs(report.completeness_qualified,False);self.assertIs(report.execution_authority,False);self.assertIs(report.trading_authorized,False);self.assertEqual(report.source_authentication,'NOT_EVALUATED')
 def test_mixed_optional_units_refuse_and_uniform_units_summarize(self):
  e=self.multiple();api=self.api();rows=tuple(api.DeclaredTradeMetadata(p.entry.signal.symbol,p.entry.decision_ms,p.outcome.known_at_ms,mae=D(index+1),mae_unit='PRICE_POINTS') for index,p in enumerate(e.outcomes[:2]))
  r=self.build(e,rows);self.assertEqual((r.all_filled.mae.count,r.all_filled.mae.mean),(2,1.5))
  with self.assertRaises(ValueError):self.build(e,(rows[0],replace(rows[1],mae_unit='USDT')))
 def test_missing_volatility_has_its_own_none_bucket(self):
  from test_strategy_entries import StrategyEntryTests
  from terminan.research_entry_evaluation import evaluate_research_entries
  from terminan.research_evaluation import EvaluationCandle,EvaluationDataset
  entry,=StrategyEntryTests().reclaim();rows=tuple(EvaluationCandle(i*60000,(i+1)*60000,(i+1)*60000,D(101),D(103),D(99),D(101),D(1)) for i in range(4))
  e=evaluate_research_entries('profile_reclaim_v2',(entry,),rows,dataset=EvaluationDataset('a'*64,'BTCUSDT','USDT',0,240000),bar_ms=60000,folds=1)
  r=self.build(e);self.assertEqual(len(r.by_volatility),1);self.assertIsNone(r.by_volatility[0].label);self.assertEqual(r.by_volatility[0].numeric.net.numeric.count,1)
 def test_posthoc_clock_waits_actual_delayed_dependency_max(self):
  e=self.multiple(delayed=300000);api=self.api();first=e.outcomes[0];self.assertEqual(first.outcome.known_at_ms,300000)
  old=api.DeclaredTradeMetadata('BTCUSDT',first.entry.decision_ms,120000,mae=D(1),mae_unit='PRICE_POINTS')
  with self.assertRaises(ValueError):self.build(e,(old,))
  r=self.build(e,(replace(old,available_at_ms=300000),));self.assertEqual(r.trades[0].holding_ms,0);self.assertEqual(r.all_filled.mae.count,1)
 def test_stable_reordered_declarations_keep_trade_association(self):
  e=self.multiple();api=self.api();rows=tuple(api.DeclaredTradeMetadata(p.entry.signal.symbol,p.entry.decision_ms,p.outcome.known_at_ms,mae=D(index),mae_unit='POINTS') for index,p in enumerate(e.outcomes))
  r=self.build(e,tuple(reversed(rows)));self.assertEqual(r.input_sha256,self.build(e,rows).input_sha256);self.assertEqual([t.identity[1] for t in r.trades],[60000,120000,180000]);self.assertEqual([t.declaration.mae for t in r.trades],[D(0),D(1),D(2)])
 def test_empty_evaluation_stays_empty_without_manufactured_metrics(self):
  from terminan.research_entry_evaluation import evaluate_research_entries
  from terminan.research_evaluation import EvaluationCandle,EvaluationDataset
  e=evaluate_research_entries('volatility_continuation_v2',(),(EvaluationCandle(0,60000,60000,D(1),D(1),D(1),D(1),D(0)),),dataset=EvaluationDataset('a'*64,'BTCUSDT','USDT',0,60000),bar_ms=60000,folds=1)
  r=self.build(e);self.assertEqual(r.trades,());self.assertEqual(r.all_filled.net.numeric.count,0);self.assertIsNone(r.all_filled.r_multiple.mean);self.assertEqual(r.by_volatility,())

 def test_foreign_math_projection_result_refuses_without_sequence_callbacks(self):
  calls=[];e=self.evaluation()
  class Foreign(list):
   def __getitem__(self,key):calls.append('get');return super().__getitem__(key)
   def __iter__(self):calls.append('iter');return super().__iter__()
  with patch('history_statistics.project_decimal_observations',return_value=Foreign((1.,2.,3.))):
   with self.assertRaises(ValueError):self.build(e)
  self.assertEqual(calls,[])

 def original_partition_vector(self,nets,regimes):
  # Exact original reporting amounts from the existing sole evaluator/engine.
  # These synthetic executions remain caller-declared and confer no authority.
  from terminan.continuation_strategy import CandleBodyObservation,generate_continuation_entries
  from terminan.research_entry_evaluation import evaluate_research_entries
  from terminan.research_evaluation import EvaluationCandle,EvaluationDataset
  f=fixtures.RichEntryTransferTests();count=len(nets)
  entries=generate_continuation_entries('BTCUSDT',tuple(CandleBodyObservation(i*60000,(i+1)*60000,(i+1)*60000,100,101) for i in range(count)),tuple(f.vol(event_start_ms=i*60000,available_at_ms=(i+1)*60000,regime=regime) for i,regime in enumerate(regimes)),as_of_ms=count*60000)
  targets=(D(103),D(201)) if count==2 else (D(103),D(103),D(104))
  entries=tuple(replace(entry,signal=replace(entry.signal,stop=D(100),target=target)) for entry,target in zip(entries,targets))
  prices=(D(103),D(201)) if count==2 else (D(103),D(100),D(104))
  rows=(EvaluationCandle(0,60000,60000,D(101),D(101),D(101),D(101),D(1)),)+tuple(EvaluationCandle((i+1)*60000,(i+2)*60000,(i+2)*60000,D(101),max(D(101),price),min(D(101),price),price,D(1)) for i,price in enumerate(prices))
  owner=evaluate_research_entries('volatility_continuation_v2',entries,rows,dataset=EvaluationDataset('a'*64,'BTCUSDT','USDT',0,(count+1)*60000),bar_ms=60000,folds=1,notional=D(101),fee_rate=D(0),slippage_bps=D(0))
  self.assertEqual(tuple(pair.outcome.execution.fill.net for pair in owner.outcomes),nets)
  return owner

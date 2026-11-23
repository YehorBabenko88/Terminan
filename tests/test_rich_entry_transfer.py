"""Rich-entry selection and metadata conservation; no live effects."""
import unittest
from dataclasses import replace
from decimal import Decimal as D
from types import MappingProxyType
from unittest.mock import patch
from terminan.volatility import VolatilityMetrics,VolatilityRegime
from terminan.continuation_strategy import CandleBodyObservation

class RichEntryTransferTests(unittest.TestCase):
 def vol(self,**changes):return replace(VolatilityMetrics(0,60000,.01,.01,.01,.01,2.,2.,.8,VolatilityRegime.HIGH,'test.v1'),**changes)
 def entry(self,**changes):
  import terminan.continuation_strategy as api
  fn=getattr(api,'generate_continuation_entries',None);self.assertTrue(callable(fn),'rich continuation selector missing')
  return fn('BTCUSDT',(CandleBodyObservation(0,60000,60000,100,101),),(self.vol(),),as_of_ms=60000)[0] if not changes else replace(self.entry(),**changes)
 def evaluate(self,entries,**changes):
  import importlib.util
  self.assertIsNotNone(importlib.util.find_spec('terminan.research_entry_evaluation'),'rich evaluation wrapper missing')
  import terminan.research_entry_evaluation as api
  from terminan.research_evaluation import EvaluationCandle,EvaluationDataset
  rows=tuple(EvaluationCandle(i*60000,(i+1)*60000,(i+1)*60000,D(101),D(103),D(99),D(101),D(1)) for i in range(3))
  kwargs=dict(dataset=EvaluationDataset('a'*64,'BTCUSDT','USDT',0,180000),bar_ms=60000,folds=1,fee_rate=D(0),slippage_bps=D(0));kwargs.update(changes)
  return api.evaluate_research_entries('volatility_continuation_v2',entries,rows,**kwargs)
 def test_continuation_retains_body_and_actual_selected_volatility(self):
  x=self.entry();self.assertEqual(x.version,'strategy_entries.v2');self.assertEqual(x.reference,101)
  self.assertEqual((x.evidence.body_reference.open,x.evidence.body_reference.close),(100,101))
  self.assertEqual((x.evidence.volatility.event_start_ms,x.evidence.volatility.available_at_ms),(0,60000))
  self.assertEqual((x.evidence.atr_percentile,x.evidence.volume_ratio,x.evidence.volatility_regime.value),(.8,2.,'HIGH'))
  self.assertEqual((x.evidence.risk_atr_fraction,x.evidence.risk_basis.value),(.01,'CALLER_DECLARED_VOLATILITY_ATR'))
  self.assertEqual((x.signal.stop,x.signal.target),(D('100.2425'),D('102.13625')))
 def test_context_uses_matching_revision_not_unrelated_newest(self):
  import terminan.continuation_strategy as api
  fn=getattr(api,'generate_continuation_entries',None);self.assertTrue(callable(fn))
  v=self.vol();x,=fn('BTCUSDT',(CandleBodyObservation(0,60000,60000,100,101),),(v,self.vol(event_start_ms=1,atr_fraction=.5)),as_of_ms=60000)
  self.assertEqual(x.context['volatility']['event_start_ms'],0);self.assertEqual(x.evidence.risk_atr_fraction,.01);self.assertIsNot(x.evidence.volatility,v)
 def test_revision_prefix_retains_selected_actual_dto(self):
  import terminan.continuation_strategy as api
  fn=getattr(api,'generate_continuation_entries',None);self.assertTrue(callable(fn))
  bodies=(CandleBodyObservation(0,60000,60000,100,101),);vols=(self.vol(volume_ratio=1.),self.vol(available_at_ms=65000),self.vol(available_at_ms=66000,atr_fraction=.2))
  before=fn('BTCUSDT',bodies,vols,as_of_ms=65000);after=fn('BTCUSDT',bodies,vols,as_of_ms=70000)
  self.assertEqual(before,after);self.assertEqual(after[0].evidence.volatility.available_at_ms,65000);self.assertEqual(after[0].evidence.volatility.atr_fraction,.01)
 def test_all_four_catalog_generators_return_entries_under_closed_v2_ids(self):
  from terminan.strategy_catalog import research_strategy_catalog,ResearchOutput,research_strategy
  rows=[r for r in research_strategy_catalog() if r.generator is not None]
  self.assertEqual({r.id for r in rows},{'sweep_reclaim_v2','breakout_retest_v2','volatility_continuation_v2','profile_reclaim_v2'})
  self.assertTrue(all(r.version=='2' and r.output is ResearchOutput.ENTRIES for r in rows))
  for old in ('sweep_reclaim','breakout_retest','volatility_continuation','profile_reclaim'):
   with self.assertRaises(ValueError):research_strategy(old)
 def test_wrapper_preserves_detached_evidence_context_and_signal_outcome(self):
  x=self.entry();out=self.evaluate((x,));self.assertEqual(out.version,'research_entry_evaluation.v2');self.assertEqual(out.entries,(x,));self.assertIsNot(out.entries[0],x)
  row,=out.outcomes;self.assertEqual(row.entry,x);self.assertEqual(row.outcome.signal,x.signal);self.assertEqual(row.outcome.disposition.value,'FILLED');self.assertEqual(row.outcome.execution.fill.reason,'stop')
  object.__setattr__(x.evidence.volatility,'volume_ratio',0);self.assertEqual(out.entries[0].evidence.volatility.volume_ratio,2.)
 def test_wrapper_fingerprint_includes_metadata_while_execution_stays_same(self):
  x=self.entry();ctx=dict(x.context);ctx['metadata']={'note':'distinct'};y=replace(x,context=MappingProxyType(ctx))
  a=self.evaluate((x,));b=self.evaluate((y,));self.assertNotEqual(a.input_sha256,b.input_sha256);self.assertEqual(a.evaluation,b.evaluation)
 def test_all_entry_graphs_detach_before_first_numeric_callback(self):
  import market_math
  x=self.entry();original=market_math.candle_ohlcv_valid
  expected=self.evaluate((x,))
  def mutate(*args):
   object.__setattr__(x.evidence,'entry_price',999);object.__setattr__(x.evidence.volatility,'volume_ratio',0);object.__setattr__(x.signal,'target',D(999));return original(*args)
  with patch.object(market_math,'candle_ohlcv_valid',side_effect=mutate):actual=self.evaluate((x,))
  self.assertEqual(actual,expected)
 def test_foreign_unused_context_key_and_leaf_refuse_before_evaluation(self):
  x=self.entry();calls=[]
  class Key(str):
   def __eq__(self,v):calls.append('eq');return str.__eq__(self,v)
   __hash__=str.__hash__
  class Meta(type):
   def __eq__(self,v):calls.append('meta');return False
  class Leaf(metaclass=Meta):pass
  for metadata in ({Key('unused'):1},{'unused':Leaf()}):
   ctx=dict(x.context);ctx['metadata']=metadata
   with patch('terminan.research_evaluation.evaluate_research_signals',side_effect=AssertionError('EVAL_CALLED')):
    with self.assertRaises(ValueError):self.evaluate((replace(x,context=MappingProxyType(ctx)),))
  self.assertEqual(calls,[])
 def test_last_future_foreign_evidence_refuses_before_evaluation(self):
  x=self.entry();y=replace(x,decision_ms=120000,signal=replace(x.signal,decision_ms=120000));object.__setattr__(y.evidence,'volume_ratio',True)
  with patch('terminan.research_evaluation.evaluate_research_signals',side_effect=AssertionError('EVAL_CALLED')):
   with self.assertRaises(ValueError):self.evaluate((x,y))
 def test_duplicate_clock_association_refuses_before_evaluation(self):
  x=self.entry()
  with patch('terminan.research_evaluation.evaluate_research_signals',side_effect=AssertionError('EVAL_CALLED')):
   with self.assertRaises(ValueError):self.evaluate((x,x))
 def test_entry_signal_and_context_clocks_must_agree(self):
  x=self.entry()
  for y in (replace(x,decision_ms=60001),replace(x,side=__import__('terminan.strategy_entries',fromlist=['EntrySide']).EntrySide.SHORT)):
   with self.assertRaises(ValueError):self.evaluate((y,))
 def test_missing_flow_profile_and_body_for_other_patterns_stay_none(self):
  from test_strategy_entries import StrategyEntryTests
  x,=StrategyEntryTests().reclaim();self.assertTrue(hasattr(x.evidence,'body_reference'),'v2 evidence missing');self.assertIsNone(x.evidence.body_reference);self.assertIsNone(x.evidence.volatility);self.assertIsNone(x.evidence.atr_percentile);self.assertIsNone(x.evidence.flow)
 def test_tampered_authority_context_or_evidence_refuses(self):
  x=self.entry()
  for target in ('entry','evidence','context'):
   y=replace(x,evidence=replace(x.evidence));ctx=dict(x.context)
   if target=='context':ctx['trading_authorized']=True;y=replace(y,context=MappingProxyType(ctx))
   else:object.__setattr__(y if target=='entry' else y.evidence,'trading_authorized',True)
   with self.assertRaises(ValueError):self.evaluate((y,))
 def test_graph_byte_node_depth_and_batch_budgets_refuse_before_eval(self):
  x=self.entry()
  for metadata in ({'x':'a'*8388609},{'x':[[[[[[[[[[[[[[[[[0]]]]]]]]]]]]]]]]]}):
   ctx=dict(x.context);ctx['metadata']=metadata
   with patch('terminan.research_evaluation.evaluate_research_signals',side_effect=AssertionError('EVAL_CALLED')):
    with self.assertRaises(ValueError):self.evaluate((replace(x,context=MappingProxyType(ctx)),))
  with self.assertRaises(ValueError):self.evaluate([x]*513)
 def test_no_source_pit_oos_or_trading_authority_is_created(self):
  out=self.evaluate((self.entry(),))
  self.assertEqual(out.source_authentication,'NOT_EVALUATED');self.assertIs(out.execution_authority,False);self.assertIs(out.trading_authorized,False)
  self.assertIs(out.evaluation.point_in_time_qualified,False);self.assertIs(out.evaluation.out_of_sample_qualified,False)

 def test_context_metric_boolean_cannot_impersonate_actual_selected_numeric(self):
  import terminan.continuation_strategy as api
  x,=api.generate_continuation_entries('BTCUSDT',(CandleBodyObservation(0,60000,60000,100,101),),(self.vol(atr_percentile=1.),),as_of_ms=60000)
  ctx=dict(x.context);vol=dict(ctx['volatility']);vol['atr_percentile']=True;ctx['volatility']=MappingProxyType(vol)
  with patch('terminan.research_evaluation.evaluate_research_signals',side_effect=AssertionError('EVAL_CALLED')):
   with self.assertRaises(ValueError):self.evaluate((replace(x,context=MappingProxyType(ctx)),))
 def test_mapping_proxy_cannot_hide_callback_mapping(self):
  from collections.abc import Mapping
  calls=[]
  class Foreign(Mapping):
   def __iter__(self):calls.append('iter');return iter(())
   def __len__(self):calls.append('len');return 0
   def __getitem__(self,key):calls.append('get');raise KeyError(key)
  x=self.entry();ctx=dict(x.context);ctx['metadata']=MappingProxyType(Foreign())
  with self.assertRaises(ValueError):self.evaluate((replace(x,context=MappingProxyType(ctx)),))
  self.assertEqual(calls,[])
 def test_other_three_patterns_preserve_profile_flow_and_missing_fields_in_wrapper(self):
  from test_strategy_entries import StrategyEntryTests
  from terminan.research_entry_evaluation import evaluate_research_entries
  from terminan.research_evaluation import EvaluationCandle,EvaluationDataset
  f=StrategyEntryTests();rows=tuple(EvaluationCandle(i*60000,(i+1)*60000,(i+1)*60000,D(101),D(103),D(98),D(101),D(1)) for i in range(6))
  for x in (f.sweep()[0],f.retest()[0],f.reclaim()[0]):
   out=evaluate_research_entries(x.pattern.value,(x,),rows,dataset=EvaluationDataset('a'*64,'BTCUSDT','USDT',0,360000),bar_ms=60000,folds=1)
   self.assertEqual(out.outcomes[0].entry,x);self.assertEqual(out.outcomes[0].outcome.signal,x.signal);self.assertIsNone(out.entries[0].evidence.body_reference)
 def test_not_filled_occupied_and_outside_outcomes_keep_exact_entry_association(self):
  import terminan.continuation_strategy as api
  x=self.entry();y,=api.generate_continuation_entries('BTCUSDT',(CandleBodyObservation(60000,120000,120000,100,101),),(self.vol(event_start_ms=60000,available_at_ms=120000),),as_of_ms=120000)
  z,=api.generate_continuation_entries('BTCUSDT',(CandleBodyObservation(120000,180000,180000,100,101),),(self.vol(event_start_ms=120000,available_at_ms=180000),),as_of_ms=180000)
  x=replace(x,signal=replace(x.signal,entry_kind='limit',entry_price=D(50),stop=D(49),target=D(51)))
  out=self.evaluate((x,y,z));self.assertEqual([r.outcome.disposition.value for r in out.outcomes],['NOT_FILLED','POSITION_OCCUPIED','OUTSIDE_TEST_WINDOW'])
  self.assertEqual([r.entry.decision_ms for r in out.outcomes],[60000,120000,180000]);self.assertEqual(tuple(r.entry for r in out.outcomes),out.entries)
 def test_outcome_signal_tamper_is_refused_instead_of_positional_zip(self):
  from terminan import research_evaluation as owner
  original=owner.evaluate_research_signals
  def changed(*args,**kwargs):
   result=original(*args,**kwargs);first=result.outcomes[0];wrong=replace(first,signal=replace(first.signal,target=D(999)))
   return replace(result,outcomes=(wrong,))
  x=self.entry()
  with patch.object(owner,'evaluate_research_signals',side_effect=changed):
   with self.assertRaisesRegex(ValueError,'ASSOCIATION'):self.evaluate((x,))
 def test_entry_dataset_and_last_candle_snapshot_precede_evaluation_callback(self):
  from terminan import research_evaluation as owner
  from terminan.research_entry_evaluation import evaluate_research_entries
  rows=(owner.EvaluationCandle(0,60000,60000,D(101),D(103),D(99),D(101),D(1)),owner.EvaluationCandle(60000,120000,120000,D(101),D(103),D(99),D(101),D(1)))
  dataset=owner.EvaluationDataset('a'*64,'BTCUSDT','USDT',0,120000);x=self.entry();original=owner.evaluate_research_signals
  def mutate(*args,**kwargs):
   object.__setattr__(rows[-1],'high',D(999));object.__setattr__(dataset,'value_unit','WRONG');object.__setattr__(x.evidence.body_reference,'close',1)
   return original(*args,**kwargs)
  with patch.object(owner,'evaluate_research_signals',side_effect=mutate):out=evaluate_research_entries('volatility_continuation_v2',(x,),rows,dataset=dataset,bar_ms=60000,folds=1)
  self.assertEqual(out.evaluation.dataset.value_unit,'USDT');self.assertEqual(out.entries[0].evidence.body_reference.close,101);self.assertEqual(out.outcomes[0].outcome.execution.fill.reason,'stop')

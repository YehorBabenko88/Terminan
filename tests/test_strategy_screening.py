import unittest
from dataclasses import FrozenInstanceError
class ResearchScreeningTests(unittest.TestCase):
 def api(self):
  from terminan.strategy_screening import screen_research_pattern
  from history_statistics import NumericFoldObservation,ProfitFactorObservation
  return screen_research_pattern,NumericFoldObservation,ProfitFactorObservation
 def rows(self,values):
  _,F,P=self.api();return tuple(F(n,e,P('FINITE',pf)) for n,e,pf in values)
 def test_original_majority_loss_is_rejected(self):
  fn,_,_=self.api();v=fn('sweep_reclaim_v2',self.rows(((30,-.4,.8),(30,-.2,.9),(30,.1,1.1))))
  self.assertEqual(v.status.value,'REJECT');self.assertIn('MAJORITY_LOSS_MAKING',v.reasons)
 def test_original_stable_folds_survive_only_as_research(self):
  fn,_,_=self.api();v=fn('sweep_reclaim_v2',self.rows(((30,.4,1.2),(30,.2,1.1),(30,.3,1.15))))
  self.assertEqual(v.status.value,'KEEP');self.assertIs(v.trading_authorized,False);self.assertIs(v.execution_authority,False)
 def test_empty_rejects_with_ordered_reasons(self):
  fn,_,_=self.api();v=fn('sweep_reclaim_v2',())
  self.assertEqual(v.status.value,'REJECT');self.assertEqual(v.reasons,('INSUFFICIENT_FOLDS','INSUFFICIENT_SAMPLES','NON_POSITIVE_EXPECTANCY','LOW_PROFIT_FACTOR'))
 def test_no_loss_factor_is_explicit_not_synthetic_zero(self):
  fn,F,P=self.api();v=fn('sweep_reclaim_v2',(F(90,1,P('NO_LOSSES',None)),),min_folds=1)
  self.assertIsNone(v.numeric.mean_profit_factor);self.assertIn('LOW_PROFIT_FACTOR',v.reasons);self.assertEqual(v.status.value,'REJECT')
 def test_fold_means_stay_unweighted(self):
  fn,_,_=self.api();v=fn('sweep_reclaim_v2',self.rows(((1,9,2),(99,-1,2))),min_folds=2,min_profitable_fraction=.5,max_loss_fold_fraction=.5)
  self.assertEqual(v.numeric.mean_expectancy,4);self.assertEqual(v.status.value,'KEEP')
 def test_threshold_equalities_and_reason_order(self):
  fn,_,_=self.api();v=fn('sweep_reclaim_v2',self.rows(((30,0,1.05),(30,-1,1))),min_folds=3,min_profitable_fraction=.5,max_loss_fold_fraction=.5)
  self.assertEqual(v.reasons,('INSUFFICIENT_FOLDS','UNSTABLE_OOS_EDGE','NON_POSITIVE_EXPECTANCY','LOW_PROFIT_FACTOR'))
 def test_specification_only_cannot_be_screened_for_generator_ranking(self):
  fn,_,_=self.api()
  for identity in ('level_impulse','SCALP_SWEEP_RECLAIM','unknown',True):
   with self.assertRaises(ValueError):fn(identity,())
 def test_closed_policy_refuses_bad_values(self):
  fn,_,_=self.api()
  for change in ({'min_folds':True},{'min_samples':4097},{'min_profitable_fraction':1.1},{'max_loss_fold_fraction':float('nan')},{'min_expectancy':True},{'min_profit_factor':-1}):
   with self.assertRaises(ValueError):fn('sweep_reclaim_v2',(),**change)
 def test_result_is_immutable_and_has_explicit_numeric_policy(self):
  fn,_,_=self.api();v=fn('sweep_reclaim_v2',())
  self.assertEqual(v.numeric_policy,'ORDERED_BINARY64_V1');self.assertEqual(v.factor_policy,'LEGACY_LT_1E100_V1')
  with self.assertRaises(FrozenInstanceError):v.pattern='changed'
 def test_all_future_fold_records_are_preflighted(self):
  fn,F,P=self.api()
  with self.assertRaises(ValueError):fn('sweep_reclaim_v2',(F(60,1,P('FINITE',2)),F(1,float('nan'),P('FINITE',2))))
 def test_segments_keep_all_dimensions_and_explicit_units(self):
  from terminan.strategy_screening import SegmentObservation,summarize_research_segments
  xs=(SegmentObservation(2,(('symbol','BTCUSDT'),('volatility_regime','HIGH'))),SegmentObservation(-1,(('symbol','ETHUSDT'),('volatility_regime','HIGH'))))
  out=summarize_research_segments(xs,dimensions=('symbol','volatility_regime'),value_unit='USDT')
  self.assertEqual([(x.dimension,x.label,x.numeric.count) for x in out],[('symbol','BTCUSDT',1),('symbol','ETHUSDT',1),('volatility_regime','HIGH',2)])
  self.assertEqual(out[-1].numeric.mean,.5);self.assertEqual(out[-1].numeric.positive_fraction,.5);self.assertEqual(out[-1].value_unit,'USDT')
 def test_missing_segment_label_is_unknown_and_empty_is_empty(self):
  from terminan.strategy_screening import SegmentObservation,summarize_research_segments
  out=summarize_research_segments((SegmentObservation(0,()),),dimensions=('symbol',),value_unit='USDT')
  self.assertEqual(out[0].label,'UNKNOWN');self.assertEqual(summarize_research_segments((),value_unit='USDT'),())
 def test_segments_reject_iterators_conflicts_and_foreign_leaves(self):
  from terminan.strategy_screening import SegmentObservation,summarize_research_segments
  for xs in (iter(()),(SegmentObservation(1,(('symbol','A'),('symbol','B'))),),(SegmentObservation(float('inf'),()),)):
   with self.assertRaises(ValueError):summarize_research_segments(xs,value_unit='USDT')
 def test_foreign_types_never_receive_callbacks(self):
  from terminan.strategy_screening import summarize_research_segments
  fn,_,_=self.api()
  class Meta(type):
   def __eq__(cls,other):raise AssertionError('foreign eq')
  class Foreign(metaclass=Meta):pass
  for call in (lambda:fn('sweep_reclaim_v2',Foreign()),lambda:fn('sweep_reclaim_v2',(),min_profitable_fraction=Foreign()),lambda:summarize_research_segments(Foreign(),value_unit='USDT')):
   with self.assertRaises(ValueError):call()

 def test_segment_leaves_detach_before_first_numeric_call(self):
  from terminan.strategy_screening import SegmentObservation,summarize_research_segments
  import market_math as owner
  a=SegmentObservation(2,(('symbol','A'),));b=SegmentObservation(-1,(('symbol','B'),));old=owner.lossless_binary64_valid
  def numeric(value):object.__setattr__(b,'net_value',100);object.__setattr__(b,'labels',(('symbol','A'),));return old(value)
  owner.lossless_binary64_valid=numeric
  try:out=summarize_research_segments((a,b),dimensions=('symbol',),value_unit='USDT')
  finally:owner.lossless_binary64_valid=old
  self.assertEqual([(x.label,x.numeric.mean) for x in out],[('A',2),('B',-1)])
 def test_plain_fold_list_detaches_before_first_numeric_call(self):
  fn,_,_=self.api();rows=list(self.rows(((30,.4,1.2),(30,.2,1.1),(30,.3,1.15))))
  import market_math as owner
  old=owner.lossless_nonnegative_binary64_valid
  def numeric(value):rows.clear();return old(value)
  owner.lossless_nonnegative_binary64_valid=numeric
  try:out=fn('sweep_reclaim_v2',rows)
  finally:owner.lossless_nonnegative_binary64_valid=old
  self.assertEqual(out.numeric.folds,3);self.assertEqual(out.status.value,'KEEP')
 def test_unexpected_math_record_refuses_without_foreign_access(self):
  import history_statistics as owner
  fn,_,_=self.api();old=owner.numeric_fold_summary
  class Foreign:
   def __getattr__(self,key):raise AssertionError('foreign output callback')
  owner.numeric_fold_summary=lambda *args,**kwargs:Foreign()
  try:
   with self.assertRaises(ValueError):fn('sweep_reclaim_v2',())
  finally:owner.numeric_fold_summary=old

 def test_absent_factor_mean_preserves_legacy_zero_threshold_policy(self):
  fn,F,P=self.api()
  for factor in (P('NO_LOSSES',None),P('FINITE',1e100)):
   out=fn('sweep_reclaim_v2',(F(90,1,factor),),min_folds=1,min_profit_factor=0)
   self.assertIsNone(out.numeric.mean_profit_factor);self.assertEqual(out.status.value,'KEEP');self.assertNotIn('LOW_PROFIT_FACTOR',out.reasons)
  out=fn('sweep_reclaim_v2',(),min_profit_factor=0)
  self.assertEqual(out.status.value,'REJECT');self.assertNotIn('LOW_PROFIT_FACTOR',out.reasons)

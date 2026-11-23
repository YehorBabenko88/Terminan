import unittest
from decimal import Decimal as D,localcontext
from dataclasses import replace
from unittest.mock import patch
import test_research_evaluation as fixtures
class EvaluationBoundaryTests(unittest.TestCase):
 def setUp(self):self.f=fixtures.ResearchEvaluationTests()
 def test_equal_release_allows_next_offer(self):
  x=self.f.evaluate((self.f.signal(0),self.f.signal(60000)),self.f.rows(2),dataset=self.f.dataset(2),folds=1);self.assertEqual([o.disposition.value for o in x.outcomes],['FILLED','FILLED'])
 def test_offgrid_market_uses_first_start_ge_decision(self):
  x=self.f.evaluate((self.f.signal(1),),self.f.rows(2),dataset=self.f.dataset(2),folds=1);self.assertEqual(x.outcomes[0].execution.entry_ms,60000)
 def test_catalog_style_foreign_dataset_flag_is_rejected_without_callback(self):
  calls=[]
  class Foreign(str):
   def __eq__(self,other):calls.append('eq');return str.__eq__(self,other)
   def __ne__(self,other):calls.append('ne');return str.__ne__(self,other)
  dataset=self.f.dataset(2);object.__setattr__(dataset,'source_authentication',Foreign('NOT_EVALUATED'))
  with self.assertRaises(ValueError):self.f.evaluate((),self.f.rows(2),dataset=dataset,folds=1)
  self.assertEqual(calls,[])
 def test_bad_last_signal_prevents_every_execution(self):
  from terminan.paper import PaperEngine
  calls=[]
  with patch.object(PaperEngine,'execute_signal',side_effect=lambda *a,**k:calls.append(True)):
   with self.assertRaises(ValueError):self.f.evaluate((self.f.signal(0),self.f.signal(60000,stop=-1)),self.f.rows(2),dataset=self.f.dataset(2),folds=1)
  self.assertEqual(calls,[])
 def test_non_no_fill_value_error_aborts_result(self):
  from terminan.paper import PaperEngine
  with patch.object(PaperEngine,'execute_signal',side_effect=ValueError('ADMISSION_FAILURE')):
   with self.assertRaisesRegex(ValueError,'ADMISSION_FAILURE'):self.f.evaluate((self.f.signal(0),),self.f.rows(2),dataset=self.f.dataset(2),folds=1)
 def test_codec_rejects_before_math_without_decimal_context_flags(self):
  import market_math
  for value in (D('1e129'),D('1e-129'),D('1'*65),D('sNaN')):
   rows=self.f.rows(1);bad=(replace(rows[0],open=value),)
   with patch.object(market_math,'candle_ohlcv_valid',side_effect=AssertionError('MATH_CALLED')):
    with localcontext() as ctx:
     before=dict(ctx.flags)
     with self.assertRaises(ValueError):self.f.evaluate((),bad,dataset=self.f.dataset(1),folds=1)
     self.assertEqual(before,dict(ctx.flags))
 def test_decimal_representation_is_part_of_input_hash(self):
  a=self.f.rows(1);b=(replace(a[0],volume=D('1.0')),)
  x=self.f.evaluate((),a,dataset=self.f.dataset(1),folds=1);y=self.f.evaluate((),b,dataset=self.f.dataset(1),folds=1);self.assertNotEqual(x.input_sha256,y.input_sha256)
 def test_real_bootstrap_crossing_zero_downgrades_only_keep(self):
  x=self.f.evaluate((self.f.signal(0),),self.f.rows(1),dataset=self.f.dataset(1),folds=1,min_folds=1,min_samples=0,min_profitable_fraction=0,min_expectancy=-2,min_profit_factor=0,max_loss_fold_fraction=1)
  self.assertEqual(x.verdict.status.value,'NEEDS_MORE_DATA');self.assertIn('BOOTSTRAP_CROSSES_ZERO',x.verdict.reasons)
 def test_gaps_and_partial_embargo_are_explicit(self):
  rows=self.f.rows(3)
  with self.assertRaises(ValueError):self.f.evaluate((),rows[:1]+rows[2:],dataset=self.f.dataset(3),folds=1)
  x=self.f.evaluate((self.f.signal(0),self.f.signal(60000)),rows,dataset=self.f.dataset(3),folds=1,embargo_ms=1);self.assertEqual([o.disposition.value for o in x.outcomes],['OUTSIDE_TEST_WINDOW','FILLED'])
 def test_all_outputs_are_immutable_false_authority(self):
  from dataclasses import FrozenInstanceError
  x=self.f.evaluate((),self.f.rows(1),dataset=self.f.dataset(1),folds=1)
  self.assertIs(x.execution_authority,False);self.assertIs(x.trading_authorized,False);self.assertIs(x.point_in_time_qualified,False);self.assertIs(x.out_of_sample_qualified,False)
  with self.assertRaises(FrozenInstanceError):x.input_sha256='changed'

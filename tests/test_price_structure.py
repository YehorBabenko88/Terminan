import unittest
from dataclasses import replace
from decimal import localcontext
class PriceStructureTests(unittest.TestCase):
 def api(self):
  from terminan.price_structure import PriceRangeObservation,analyze_price_structure
  return PriceRangeObservation,analyze_price_structure
 def rows(self,*,gap=False,delay=None):
  cls,_=self.api();pairs=((10,8),(12,10),(15,13)) if gap else ((1,0),(3,1),(2,1))
  return tuple(cls(i*60,(i+1)*60,delay if i==0 and delay is not None else (i+1)*60,h,l) for i,(h,l) in enumerate(pairs))
 def analyze(self,rows=None,*,cutoff=180):
  _,fn=self.api();return fn(self.rows() if rows is None else rows,as_of_ms=cutoff,left=1,right=1)
 def test_original_swing_uses_actual_confirmation_dependencies(self):
  x,=self.analyze();self.assertEqual((x.event_start_ms,x.available_at_ms,x.kind.value,x.low,x.high),(60,180,'HIGH_SWING',3,3));self.assertEqual((x.dependency_start_ms,x.dependency_end_ms),(0,180))
 def test_original_gap_keeps_literal_price_boundaries(self):
  x,=self.analyze(self.rows(gap=True));self.assertEqual((x.kind.value,x.low,x.high),('UPWARD_GAP',10,13))
 def test_delayed_left_observation_is_not_replaced_by_bar_end(self):
  rows=self.rows(delay=1000);self.assertEqual(self.analyze(rows,cutoff=999),());self.assertEqual(self.analyze(rows,cutoff=1000)[0].available_at_ms,1000)
 def test_gap_middle_dependency_must_also_be_available(self):
  rows=self.rows(gap=True);rows=(rows[0],replace(rows[1],available_at_ms=240),rows[2])
  self.assertEqual(self.analyze(rows,cutoff=180),());self.assertEqual(self.analyze(rows,cutoff=240)[0].available_at_ms,240)
 def test_future_confirmation_does_not_leak(self):self.assertEqual(self.analyze(cutoff=179),())
 def test_valid_future_append_cannot_change_already_available_prefix(self):
  cls,fn=self.api();rows=self.rows();before=self.analyze(rows);after=fn(rows+(cls(180,240,240,2,1),),as_of_ms=180,left=1,right=1);self.assertEqual(after,before)
 def test_invalid_future_price_refuses_full_batch(self):
  cls,_=self.api()
  with self.assertRaises(ValueError):self.analyze(self.rows()+(cls(180,240,240,float('nan'),0),))
 def test_explicit_clock_order_and_contiguous_cadence_required(self):
  rows=self.rows()
  for bad in (replace(rows[1],available_at_ms=119),replace(rows[1],event_start_ms=True),replace(rows[1],event_start_ms=61),replace(rows[1],event_end_ms=121)):
   with self.assertRaises(ValueError):self.analyze((rows[0],bad,rows[2]))
 def test_literal_containers_and_rows_refuse_foreign_callbacks(self):
  cls,fn=self.api()
  class Rows(list):
   def __iter__(self):raise AssertionError('FOREIGN_ITERATION')
  class Row(cls):pass
  with self.assertRaises(ValueError):fn(Rows(self.rows()),as_of_ms=180,left=1,right=1)
  with self.assertRaises(ValueError):fn((Row(0,60,60,1,0),),as_of_ms=180,left=1,right=1)
 def test_math_refusal_propagates_without_mutating_declared_inputs(self):
  from unittest.mock import patch
  rows=self.rows()
  with patch('market_math.price_structure_patterns',side_effect=ValueError('OWNER_REFUSED')):
   with self.assertRaisesRegex(ValueError,'OWNER_REFUSED'):self.analyze(rows)
  self.assertEqual(rows,self.rows())
 def test_unknown_math_kind_refuses_without_partial_output(self):
  from unittest.mock import patch
  from market_math import PriceStructurePattern
  with patch('market_math.price_structure_patterns',return_value=(PriceStructurePattern(1,99,3,3,0,3),)):
   with self.assertRaises(ValueError):self.analyze()
 def test_malformed_math_dependency_window_refuses(self):
  from unittest.mock import patch
  from market_math import PriceStructurePattern
  for result in (PriceStructurePattern(1,0,3,3,-1,3),PriceStructurePattern(1,0,3,3,0,4),PriceStructurePattern(1,True,3,3,0,3)):
   with patch('market_math.price_structure_patterns',return_value=(result,)):
    with self.assertRaises(ValueError):self.analyze()
 def test_caller_decimal_flags_and_traps_remain_unchanged(self):
  with localcontext() as c:
   c.prec=2
   for flag in c.flags:c.flags[flag]=True;c.traps[flag]=True
   before=(dict(c.flags),dict(c.traps));self.assertEqual(len(self.analyze()),1);self.assertEqual((dict(c.flags),dict(c.traps)),before)
 def test_declared_analysis_never_grants_execution_or_source_authentication(self):
  x,=self.analyze();self.assertIs(x.execution_authority,False);self.assertIs(x.trading_authorized,False);self.assertEqual(x.source_authentication,'NOT_EVALUATED');self.assertEqual(x.availability_basis,'CALLER_DECLARED_DEPENDENCY_MAX')
  with self.assertRaises(AttributeError):x.high=0
 def test_decision_clock_domain_is_literal_and_required(self):
  _,fn=self.api()
  for cutoff in (True,None,-1,1.0,2**53):
   with self.assertRaises(ValueError):fn(self.rows(),as_of_ms=cutoff,left=1,right=1)
 def test_bounded_batch_refuses_before_iteration(self):
  _,fn=self.api()
  with self.assertRaises(ValueError):fn([self.rows()[0]]*4097,as_of_ms=180,left=1,right=1)

 def test_declared_clock_snapshot_survives_input_mutation_during_owner_call(self):
  from unittest.mock import patch
  import market_math
  rows=self.rows(delay=1000);original=market_math.price_structure_patterns
  def mutate_then_compute(prices,**policy):
   object.__setattr__(rows[0],'available_at_ms',60)
   return original(prices,**policy)
  with patch('market_math.price_structure_patterns',side_effect=mutate_then_compute):
   self.assertEqual(self.analyze(rows,cutoff=999),())

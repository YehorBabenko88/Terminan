import importlib,importlib.util,unittest
from decimal import Decimal as D
from terminan.paper import PaperEngine
from terminan.research_signals import ResearchBar
import market_math as math_owner
class ScaledLimitExecutionTests(unittest.TestCase):
 def api(self):
  self.assertIsNotNone(importlib.util.find_spec('terminan.scale_execution'),'canonical scaled execution contracts absent')
  self.assertTrue(hasattr(PaperEngine,'execute_scale_plan'),'sole PaperEngine scale method absent')
  return importlib.import_module('terminan.scale_execution')
 def bars(self,rows):
  return tuple(ResearchBar(t,*map(lambda x:D(str(x)),(o,h,l,c))) for t,o,h,l,c in rows)
 def plan(self,module,entries,targets,move=False):
  return module.ScaleExecutionPlan('BTCUSDT',0,'long',tuple(module.ScaleEntryLeg(D(str(p)),D(str(f))) for p,f in entries),D(95),tuple(module.ScaleExitTarget(D(str(p)),D(str(f))) for p,f in targets),move)
 def execute(self,plan,rows):
  engine=PaperEngine(notional=D(100),fee_rate=D(0),slippage_bps=D(0));engine.enabled=True
  result=engine.execute_scale_plan(plan,self.bars(rows),bar_ms=60,as_of_ms=rows[-1][0]+60)
  self.assertEqual(len(engine.fills),1);self.assertEqual(engine.fills[0],result.fill)
  return result
 def test_two_independent_entry_legs_and_partial_targets(self):
  m=self.api();rows=[(0,100,101,99,100),(60,99,100,98,99),(120,98,99,97,98),(180,101,102,98,101),(240,103,104,100,103)]
  result=self.execute(self.plan(m,((99,.5),(98,.5)),((101,.5),(103,.5))),rows)
  self.assertEqual(len(result.entries),2);self.assertEqual([x.reason for x in result.exits],['TP1','TP2'])
  self.assertEqual(math_owner.exact_sum(tuple(x.quantity for x in result.entries)),math_owner.exact_sum(tuple(x.quantity for x in result.exits)))
 def test_no_state_shared_between_calls(self):
  m=self.api();rows=[(0,100,101,99,100),(60,99,100,98,99),(120,101,102,98,101)]
  plan=self.plan(m,((99,1),),((101,1),))
  self.assertEqual(self.execute(plan,rows),self.execute(plan,rows))
 def test_move_stop_after_first_target(self):
  m=self.api();rows=[(0,100,100,99,100),(60,99,100,98,99),(120,101,102,100,101),(180,99,100,98,99)]
  result=self.execute(self.plan(m,((99,1),),((101,.5),(103,.5)),True),rows)
  self.assertEqual([x.reason for x in result.exits],['TP1','SL']);self.assertEqual(result.exits[-1].price,D(99))

 def engine(self,notional=D(100),fee_rate=D(0)):
  e=PaperEngine(notional=notional,fee_rate=fee_rate,slippage_bps=D(0));e.enabled=True;return e
 def test_disabled_engine_refuses_without_reading_foreign_inputs(self):
  e=PaperEngine();calls=[]
  class Foreign:
   def __iter__(self):calls.append('iter');raise AssertionError
  with self.assertRaisesRegex(ValueError,'disabled'):e.execute_scale_plan(Foreign(),Foreign(),bar_ms=60,as_of_ms=120)
  self.assertEqual(calls,[]);self.assertEqual(e.fills,[])
 def test_no_fill_is_typed_and_preserves_engine_state(self):
  from terminan.research_signals import SignalNotFilled
  m=self.api();e=self.engine();rows=self.bars([(0,110,111,109,110),(60,110,111,109,110)])
  with self.assertRaises(SignalNotFilled):e.execute_scale_plan(self.plan(m,((99,1),),((101,1),)),rows,bar_ms=60,as_of_ms=120)
  self.assertEqual((e.fills,e.positions,e.last_trade_time),([],{},{}))
 def test_fill_bar_stop_precedes_ambiguous_target(self):
  m=self.api();r=self.execute(self.plan(m,((99,1),),((101,1),)),[(0,100,101,99,100),(60,100,110,90,106)])
  self.assertEqual([x.reason for x in r.exits],['SL']);self.assertEqual(r.exits[0].price,D(95))
 def test_intrabar_target_needs_close_after_entry_proof(self):
  m=self.api();r=self.execute(self.plan(m,((99,1),),((101,1),)),[(0,102,105,100,102),(60,102,105,98,99)])
  self.assertEqual([x.reason for x in r.exits],['EOD']);self.assertEqual(r.exits[0].price,D(99))
 def test_short_side_symmetry(self):
  m=self.api();p=m.ScaleExecutionPlan('BTCUSDT',0,'short',(m.ScaleEntryLeg(D(101),D(1)),),D(105),(m.ScaleExitTarget(D(99),D(1)),))
  r=self.execute(p,[(0,100,101,99,100),(60,101,102,100,101),(120,99,102,98,99)])
  self.assertEqual([x.reason for x in r.exits],['TP1']);self.assertGreater(r.fill.net,D(0))
 def test_final_target_closes_exact_remainder_without_eod_dust(self):
  m=self.api();r=self.execute(self.plan(m,((99,1),),((101,'.3'),(103,'.7'))),[(0,100,101,99,100),(60,99,100,98,99),(120,101,102,100,101),(180,103,104,102,103)])
  self.assertEqual([x.reason for x in r.exits],['TP1','TP2'])
  self.assertEqual(math_owner.exact_sum(tuple(x.quantity for x in r.entries)),math_owner.exact_sum(tuple(x.quantity for x in r.exits)))
  self.assertFalse(r.execution_authority);self.assertFalse(r.trading_authorized);self.assertEqual(r.tick_ordering,'UNKNOWN')
 def test_full_close_cancels_still_unfilled_entry_legs(self):
  m=self.api();p=m.ScaleExecutionPlan('BTCUSDT',0,'long',(m.ScaleEntryLeg(D(99),D('.5')),m.ScaleEntryLeg(D(90),D('.5'))),D(85),(m.ScaleExitTarget(D(101),D(1)),))
  r=self.execute(p,[(0,100,101,99,100),(60,99,100,98,99),(120,101,102,98,101),(180,90,91,89,90)])
  self.assertEqual(len(r.entries),1);self.assertEqual(r.exit_ms,120);self.assertEqual(r.unfilled_entry_indices,(1,))
 def test_eod_closes_quantity_far_below_legacy_epsilon(self):
  m=self.api();e=self.engine(notional=D('1e-20'));r=e.execute_scale_plan(self.plan(m,((99,1),),((101,1),)),self.bars([(0,100,101,99,100),(60,99,100,98,99)]),bar_ms=60,as_of_ms=120)
  self.assertEqual([x.reason for x in r.exits],['EOD']);self.assertGreater(r.exits[0].quantity,D(0));self.assertLess(r.exits[0].quantity,D('1e-12'));self.assertEqual(r.exits[0].quantity,r.entries[0].quantity)
 def test_invalid_future_decimal_has_zero_callbacks_and_zero_math(self):
  from unittest.mock import patch
  m=self.api();e=self.engine();calls=[]
  class ForeignDecimal(D):
   def is_finite(self):calls.append('finite');raise AssertionError
  rows=(ResearchBar(0,D(100),D(101),D(99),D(100)),ResearchBar(60,D(99),D(100),D(98),ForeignDecimal('99')))
  with patch.object(math_owner,'paper_scale_fractions_valid',side_effect=AssertionError('Math before full graph')):
   with self.assertRaises(ValueError):e.execute_scale_plan(self.plan(m,((99,1),),((101,1),)),rows,bar_ms=60,as_of_ms=120)
  self.assertEqual(calls,[]);self.assertEqual(e.fills,[])
 def test_future_clock_refuses_before_first_math(self):
  from unittest.mock import patch
  m=self.api();e=self.engine()
  with patch.object(math_owner,'paper_scale_fractions_valid',side_effect=AssertionError('Math before future clock')):
   with self.assertRaises(ValueError):e.execute_scale_plan(self.plan(m,((99,1),),((101,1),)),self.bars([(0,100,101,99,100),(60,99,100,98,99)]),bar_ms=60,as_of_ms=60)
  self.assertEqual(e.fills,[])
 def test_entire_plan_bars_and_engine_policy_detach_before_math(self):
  from unittest.mock import patch
  m=self.api();e=self.engine();p=self.plan(m,((99,1),),((101,1),));rows=self.bars([(0,100,101,99,100),(60,99,100,98,99),(120,101,102,100,101)]);original=math_owner.paper_scale_fractions_valid;calls=[]
  def mutate(values):
   if not calls:
    object.__setattr__(p.entries[0],'price',D(1));object.__setattr__(rows[-1],'low',D(-1));e.notional=D(200)
   calls.append(1);return original(values)
  with patch.object(math_owner,'paper_scale_fractions_valid',side_effect=mutate):r=e.execute_scale_plan(p,rows,bar_ms=60,as_of_ms=180)
  self.assertEqual(r.entries[0].price,D(99));self.assertEqual(r.entries[0].quantity,math_owner.paper_position_size(D(100),D(99)));self.assertEqual(e.notional,D(200))
 def test_hostile_decimal_context_and_flags_are_preserved(self):
  from decimal import localcontext
  m=self.api();p=self.plan(m,((99,1),),((101,1),))
  with localcontext() as c:
   c.prec=2;c.Emax=2;c.Emin=-2
   for signal in c.traps:c.traps[signal]=True
   for signal in c.flags:c.flags[signal]=True
   before=c.copy();r=self.execute(p,[(0,100,101,99,100),(60,99,100,98,99),(120,101,102,100,101)])
   self.assertEqual(c.flags,before.flags);self.assertEqual(c.traps,before.traps);self.assertEqual((c.prec,c.Emin,c.Emax),(before.prec,before.Emin,before.Emax))
 def test_late_math_failure_leaves_all_engine_state_unchanged(self):
  from unittest.mock import patch
  from datetime import datetime,timezone
  m=self.api();e=self.engine();e.reference['BTCUSDT']=(datetime(1970,1,1,tzinfo=timezone.utc),D(100));before=(dict(e.reference),dict(e.positions),dict(e.last_trade_time),tuple(e.fills));original=math_owner.paper_scale_accounting
  def reject(side,events,fee_rate):
   if events and events[-1].kind=='EXIT':raise ValueError('LATE_FINANCIAL_REFUSAL')
   return original(side,events,fee_rate)
  with patch.object(math_owner,'paper_scale_accounting',side_effect=reject):
   with self.assertRaisesRegex(ValueError,'LATE_FINANCIAL_REFUSAL'):e.execute_scale_plan(self.plan(m,((99,1),),((101,1),)),self.bars([(0,100,101,99,100),(60,99,100,98,99),(120,101,102,100,101)]),bar_ms=60,as_of_ms=180)
  self.assertEqual((e.reference,e.positions,e.last_trade_time,tuple(e.fills)),before)
 def test_fraction_and_constructor_authority_masquerades_refuse(self):
  from dataclasses import replace
  m=self.api();p=self.plan(m,((99,'.9'),),((101,1),));e=self.engine()
  with self.assertRaises(ValueError):e.execute_scale_plan(p,self.bars([(0,100,101,99,100),(60,99,100,98,99)]),bar_ms=60,as_of_ms=120)
  with self.assertRaises(ValueError):e.execute_scale_plan(replace(self.plan(m,((99,1),),((101,1),)),move_stop_to_entry_after_first_target=1),self.bars([(0,100,101,99,100),(60,99,100,98,99)]),bar_ms=60,as_of_ms=120)
  r=self.execute(self.plan(m,((99,1),),((101,1),)),[(0,100,101,99,100),(60,99,100,98,99)])
  with self.assertRaises(ValueError):replace(r,execution_authority=True)

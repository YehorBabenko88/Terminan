import copy,unittest
from decimal import Decimal as D,localcontext,Inexact,Rounded,Overflow,Underflow
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from terminan.paper import PaperEngine,ClosedMinute,ExecutionTrade
T=datetime(2026,1,1,tzinfo=timezone.utc)
def event(seconds,price):return ExecutionTrade('BTCUSDT',T+timedelta(seconds=seconds),D(price))
def engine():
 e=PaperEngine();e.enabled=True;e.on_closed_minute('BTCUSDT',ClosedMinute(T,D('100'),True));return e
class MathBoundaryTests(unittest.TestCase):
 def test_invalid_owner_domain_does_not_advance_any_state(self):
  e=engine();before=copy.deepcopy(e.__dict__)
  with self.assertRaises(ValueError):e.on_trade(event(61,'1e5000'))
  self.assertEqual(e.__dict__,before)
 def test_nonliteral_completeness_refused_without_clearing_reference(self):
  e=engine();before=copy.deepcopy(e.__dict__)
  with self.assertRaises(ValueError):e.on_closed_minute('BTCUSDT',ClosedMinute(T,D('100'),'false'))
  self.assertEqual(e.__dict__,before)
 def test_fixed_policy_fill_is_independent_of_hostile_decimal_context(self):
  baseline=engine();baseline.on_trade(event(61,'102'));expected=baseline.on_trade(event(62,'100'))
  for precision in (2,7,28):
   with self.subTest(precision=precision),localcontext() as context:
    context.prec=precision
    for signal in (Inexact,Rounded,Overflow,Underflow):context.traps[signal]=True
    e=engine();e.on_trade(event(61,'102'));self.assertEqual(e.on_trade(event(62,'100')),expected)
 def test_owner_refusal_before_exit_commit_leaves_position_and_clock_unchanged(self):
  e=engine();e.on_trade(event(61,'102'));before=copy.deepcopy(e.__dict__)
  with patch('market_math.paper_fill_metrics',side_effect=ValueError('OWNER_REFUSED')),self.assertRaises(ValueError):e.on_trade(event(62,'100'))
  self.assertEqual(e.__dict__,before)

class HistoricalAccountingOwnerTests(unittest.TestCase):
 def test_sizing_policy_uses_math_net_kernel_without_mutating_input(self):
  from terminan.paper import apply_sizing
  rows=[{'pnl':-2.,'fees':.2,'slippage':.1}];before=copy.deepcopy(rows)
  with patch('market_math.paper_net_pnl',side_effect=ValueError('OWNER_REFUSED')),self.assertRaises(ValueError):apply_sizing(rows)
  self.assertEqual(rows,before)
 def test_pure_net_formula_is_not_a_terminan_api(self):
  import terminan.paper as paper
  self.assertFalse(hasattr(paper,'trade_net_pnl'))

class ExactInputBoundaryTests(unittest.TestCase):
 def test_validation_preserves_exact_poc_and_does_not_round_trade_into_signal(self):
  exact=D('100.00000000000000000000000000001');e=PaperEngine();e.enabled=True;e.on_closed_minute('BTCUSDT',ClosedMinute(T,exact,True))
  self.assertEqual(e.reference['BTCUSDT'][1],exact)
  e=engine();e.on_trade(event(61,'101.49999999999999999999999999999'))
  self.assertEqual(e.positions,{})

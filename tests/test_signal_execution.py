import copy,unittest
from decimal import Decimal as D
from unittest.mock import patch
from terminan.paper import PaperEngine
class SignalExecutionTests(unittest.TestCase):
 def engine(self):
  value=PaperEngine(fee_rate='0',slippage_bps='0');value.enabled=True;return value
 def execute(self,bars,*,side='long',kind='market',decision=60000,entry=None,stop='99',target='102',policy='SL_FIRST',engine=None,as_of=None):
  method=getattr(PaperEngine,'execute_signal',None);self.assertIsNotNone(method,'extend the canonical engine; do not introduce another simulator')
  from terminan.research_signals import ResearchSignal,ResearchBar
  signal=ResearchSignal('BTCUSDT',decision,side,kind,None if entry is None else D(entry),D(stop),D(target))
  rows=tuple(ResearchBar(t,D(o),D(h),D(l),D(c)) for t,o,h,l,c in bars)
  value=engine or self.engine()
  return value.execute_signal(signal,rows,bar_ms=60000,as_of_ms=as_of if as_of is not None else bars[-1][0]+60000,ambiguity_policy=policy),value
 def test_market_fill_checks_same_bar_stop_and_target(self):
  result,engine=self.execute([(60000,'100','101','98','100')]);self.assertEqual(result.fill.reason,'stop');self.assertEqual(result.fill.net,D('-1'));self.assertEqual(result.entry_ms,60000);self.assertEqual(engine.fills,[result.fill]);self.assertEqual(engine.positions,{})
  result,_=self.execute([(60000,'100','100.5','97','98.5')],side='short',stop='101',target='98');self.assertEqual(result.fill.reason,'target');self.assertEqual(result.fill.net,D('2'))
 def test_default_stop_first_and_explicit_optimistic_policy_are_distinct(self):
  bars=[(60000,'100','103','98','101')]
  conservative,_=self.execute(bars);optimistic,_=self.execute(bars,policy='TP_FIRST')
  self.assertEqual(conservative.fill.reason,'stop');self.assertEqual(optimistic.fill.reason,'target');self.assertIn('CONSERVATIVE',conservative.model);self.assertIn('OPTIMISTIC',optimistic.model)
 def test_intrabar_pre_entry_wick_cannot_grant_default_profit(self):
  bars=[(60000,'103','104','100','100')]
  result,_=self.execute(bars,kind='limit',decision=0,entry='100');self.assertEqual(result.fill.reason,'end_of_data');self.assertEqual(result.fill.net,D(0))
  optimistic,_=self.execute(bars,kind='limit',decision=0,entry='100',policy='TP_FIRST');self.assertEqual(optimistic.fill.reason,'target')
  proven,_=self.execute([(60000,'103','104','100','103')],kind='limit',decision=0,entry='100');self.assertEqual(proven.fill.reason,'target')
  short,_=self.execute([(60000,'97','100','96','100')],side='short',kind='limit',decision=0,entry='100',stop='101',target='98');self.assertEqual(short.fill.reason,'end_of_data')
 def test_opening_gap_order_and_conservative_target_price(self):
  gap,_=self.execute([(60000,'98','100','97','99')],kind='limit',decision=0,entry='100');self.assertEqual(gap.fill.reason,'stop_gap');self.assertEqual(gap.fill.net,D(0))
  target,_=self.execute([(60000,'100','101','99.5','100'),(120000,'104','105','103','104')]);self.assertEqual(target.fill.reason,'target_gap');self.assertEqual(target.fill.exit,D('102'))
 def test_predecision_wicks_and_limit_availability_do_not_leak(self):
  result,_=self.execute([(60000,'100','1000','1','100'),(120000,'100','101','99.5','100')],decision=60001);self.assertEqual(result.entry_ms,120000);self.assertEqual(result.fill.reason,'end_of_data')
  with self.assertRaises(ValueError):self.execute([(60000,'103','104','100','100'),(120000,'103','104','101','103')],kind='limit',decision=60000,entry='100')
 def test_full_batch_and_owner_refusal_leave_engine_unchanged(self):
  engine=self.engine();before=copy.deepcopy(engine.__dict__)
  invalid=[[(60000,'100','101','99.5','100'),(120000,'100','101','NaN','100')],[(60000,'100','101','99.5','100'),(180000,'100','101','99.5','100')],[(60000,'100','101','99.5','100'),(60000,'100','101','99.5','100')]]
  for rows in invalid:
   with self.subTest(rows=rows),self.assertRaises(ValueError):self.execute(rows,engine=engine)
   self.assertEqual(engine.__dict__,before)
  with self.assertRaises(ValueError):self.execute([(60000,'100','101','98','100')],engine=engine,as_of=119999)
  self.assertEqual(engine.__dict__,before)
  with patch('market_math.paper_fill_metrics',side_effect=ValueError('OWNER_REFUSED')),self.assertRaises(ValueError):self.execute([(60000,'100','101','98','100')],engine=engine)
  self.assertEqual(engine.__dict__,before)

 def test_nonaligned_limit_decision_uses_next_bar_boundary_for_both_sides(self):
  for side,opening,stop,target in [('long','99','98','102'),('short','101','102','98')]:
   with self.subTest(side=side):
    result,_=self.execute([(60000,'100','104','96','100'),(120000,opening,opening,opening,opening)],side=side,kind='limit',decision=60001,entry='100',stop=stop,target=target)
    self.assertEqual(result.entry_ms,120000);self.assertEqual(result.fill.entry,D(opening))

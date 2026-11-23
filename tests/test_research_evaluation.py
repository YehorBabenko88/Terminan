import unittest
from decimal import Decimal as D
class ResearchEvaluationTests(unittest.TestCase):
 def api(self):
  from terminan.research_evaluation import EvaluationCandle,EvaluationDataset,evaluate_research_signals
  from terminan.research_signals import ResearchSignal
  return EvaluationCandle,EvaluationDataset,evaluate_research_signals,ResearchSignal
 def rows(self,n=150,*,delayed_first=None):
  C,_,_,_=self.api();return tuple(C(i*60000,(i+1)*60000,delayed_first if i==0 and delayed_first is not None else(i+1)*60000,D(100),D(101),D(99),D(100),D(1)) for i in range(n))
 def dataset(self,n=150,as_of=None):
  _,S,_,_=self.api();return S('a'*64,'BTCUSDT','USDT',0,n*60000 if as_of is None else as_of)
 def signal(self,t,*,limit=None,stop=99,target=101):
  _,_,_,S=self.api();return S('BTCUSDT',t,'long','market' if limit is None else'limit',None if limit is None else D(limit),D(stop),D(target))
 def evaluate(self,signals,rows=None,*,dataset=None,**kwargs):
  _,_,fn,_=self.api();return fn('sweep_reclaim_v2',signals,self.rows() if rows is None else rows,dataset=self.dataset() if dataset is None else dataset,bar_ms=60000,notional=D(100),fee_rate=D(0),slippage_bps=D(0),**kwargs)
 def test_original_chronological_five_folds_and_verdict(self):
  result=self.evaluate(tuple(self.signal(i*60000) for i in range(5,145,5)),folds=5,min_samples=10)
  self.assertEqual(len(result.folds),5);self.assertEqual(result.numeric.numeric.count,28);self.assertEqual(result.numeric.numeric.total,-28)
  self.assertIsNotNone(result.bootstrap);self.assertIn(result.verdict.status.value,('KEEP','REJECT','NEEDS_MORE_DATA'));self.assertEqual(len(result.outcomes),28)
 def test_empty_never_becomes_keep(self):
  result=self.evaluate((),folds=5,min_samples=10);self.assertNotEqual(result.verdict.status.value,'KEEP');self.assertIsNone(result.bootstrap)
 def test_valid_limit_no_fill_is_typed_and_pending_blocks_other_offer(self):
  result=self.evaluate((self.signal(0,limit=50,stop=49,target=51),self.signal(60000)),self.rows(3),dataset=self.dataset(3),folds=1)
  self.assertEqual([x.disposition.value for x in result.outcomes],['NOT_FILLED','POSITION_OCCUPIED']);self.assertEqual(result.numeric.numeric.count,0)
 def test_occupied_release_waits_actual_availability(self):
  result=self.evaluate((self.signal(0,stop=90),self.signal(120000,stop=90)),self.rows(5,delayed_first=600000),dataset=self.dataset(5,600000),folds=1)
  self.assertEqual([x.disposition.value for x in result.outcomes],['FILLED','POSITION_OCCUPIED']);self.assertEqual(result.outcomes[0].known_at_ms,600000)
 def test_future_invalid_candle_refuses_before_any_execution(self):
  from dataclasses import replace
  from terminan.paper import PaperEngine
  rows=self.rows(3);rows=rows[:-1]+(replace(rows[-1],high=D('NaN')),);calls=[];original=PaperEngine.execute_signal
  def execute(*args,**kwargs):calls.append(1);return original(*args,**kwargs)
  PaperEngine.execute_signal=execute
  try:
   with self.assertRaises(ValueError):self.evaluate((self.signal(0),),rows,dataset=self.dataset(3),folds=1)
  finally:PaperEngine.execute_signal=original
  self.assertEqual(calls,[])
 def test_all_inputs_detach_before_first_math_call(self):
  import market_math as owner
  rows=self.rows(3);signal=self.signal(0);dataset=self.dataset(3);expected=self.evaluate((signal,),rows,dataset=dataset,folds=1);original=owner.candle_ohlcv_valid
  def numeric(*args):
   object.__setattr__(rows[-1],'high',D(999));object.__setattr__(signal,'side','short');object.__setattr__(dataset,'value_unit','CHANGED');return original(*args)
  owner.candle_ohlcv_valid=numeric
  try:actual=self.evaluate((signal,),rows,dataset=dataset,folds=1)
  finally:owner.candle_ohlcv_valid=original
  self.assertEqual(actual,expected)
 def test_every_signal_has_outcome_including_embargo_or_outside_window(self):
  result=self.evaluate((self.signal(0),self.signal(120000),self.signal(180000)),self.rows(3),dataset=self.dataset(3,240000),folds=1,embargo_ms=60000)
  self.assertEqual(len(result.outcomes),3);self.assertEqual(result.outcomes[0].disposition.value,'OUTSIDE_TEST_WINDOW');self.assertEqual(result.outcomes[-1].disposition.value,'OUTSIDE_TEST_WINDOW')
 def test_duplicate_or_foreign_inputs_refuse_without_callbacks(self):
  class Meta(type):
   def __eq__(cls,other):raise AssertionError('foreign eq')
  class Foreign(metaclass=Meta):pass
  with self.assertRaises(ValueError):self.evaluate(Foreign())
  signal=self.signal(0)
  with self.assertRaises(ValueError):self.evaluate((signal,signal))
 def test_decimal_subclasses_and_clock_coercions_refuse(self):
  from dataclasses import replace
  class ForeignDecimal(D):
   def __str__(self):raise AssertionError('foreign str')
  row=self.rows(1)[0]
  for bad in (replace(row,open=ForeignDecimal('100')),replace(row,event_start_ms=False)):
   with self.assertRaises(ValueError):self.evaluate((self.signal(0),),(bad,),dataset=self.dataset(1),folds=1)
 def test_small_uneven_folds_preserve_all_candles(self):
  result=self.evaluate((self.signal(0),self.signal(120000),self.signal(240000)),self.rows(5),dataset=self.dataset(5),folds=2)
  self.assertEqual([(x.start_ms,x.end_ms) for x in result.folds],[(0,120000),(120000,300000)]);self.assertTrue(all(x.disposition.value=='FILLED' for x in result.outcomes))
 def test_scan_budget_and_policy_are_closed(self):
  for change in ({'folds':True},{'folds':129},{'embargo_ms':True},{'ambiguity_policy':'UNKNOWN'}):
   with self.assertRaises(ValueError):self.evaluate((),**change)
  signals=tuple(self.signal(i*60000) for i in range(512))
  with self.assertRaises(ValueError):self.evaluate(signals,self.rows(4096),dataset=self.dataset(4096),folds=1)
 def test_no_fill_is_distinct_from_bad_admission(self):
  from terminan.paper import PaperEngine
  from terminan.research_signals import SignalNotFilled,ResearchBar
  engine=PaperEngine(fee_rate=D(0),slippage_bps=D(0));engine.enabled=True
  with self.assertRaises(SignalNotFilled):engine.execute_signal(self.signal(0,limit=50,stop=49,target=51),(ResearchBar(0,D(100),D(101),D(99),D(100)),),bar_ms=60000,as_of_ms=60000)
  with self.assertRaises(ValueError) as ctx:engine.execute_signal(self.signal(0,stop=-1),(ResearchBar(0,D(100),D(101),D(99),D(100)),),bar_ms=60000,as_of_ms=60000)
  self.assertIsNot(type(ctx.exception),SignalNotFilled);self.assertEqual(engine.fills,[])

import unittest
from dataclasses import replace
from decimal import Decimal as D
from terminan.volatility import VolatilityMetrics,VolatilityRegime
class ContinuationStrategyTests(unittest.TestCase):
 def api(self):
  from terminan.continuation_strategy import CandleBodyObservation,generate_continuation_entries
  return CandleBodyObservation,generate_continuation_entries
 def volatility(self,**changes):
  row=VolatilityMetrics(0,60000,.01,.01,.01,.01,2.,2.,.8,VolatilityRegime.HIGH,'test.v1')
  return replace(row,**changes)
 def generate(self,*,opening=100,closing=101,available=60000,as_of=60000,vols=None,**kwargs):
  cls,fn=self.api();return fn('BTCUSDT',(cls(0,60000,available,opening,closing),),(self.volatility(),) if vols is None else vols,as_of_ms=as_of,**kwargs)
 def test_long_signal_uses_canonical_decimal_geometry(self):
  x,=self.generate();self.assertEqual((x.side,x.decision_ms,x.signal.stop,x.signal.target),('long',60000,D('100.2425'),D('102.13625')));self.assertIsNone(x.signal.entry_price)
 def test_short_signal(self):self.assertEqual(self.generate(opening=101,closing=100)[0].side,'short')
 def test_small_body_or_policy_does_not_emit(self):
  self.assertEqual(self.generate(closing=100.1),())
  self.assertEqual(self.generate(vols=(self.volatility(volume_ratio=1.),)),())
  self.assertEqual(self.generate(vols=(self.volatility(atr_percentile=.1),)),())
 def test_explicit_late_availability_is_decision_clock(self):self.assertEqual(self.generate(available=70000,as_of=90000,vols=(self.volatility(available_at_ms=80000),))[0].decision_ms,80000)
 def test_no_future_observation_or_inferred_availability(self):
  self.assertEqual(self.generate(available=70000),())
  self.assertEqual(self.generate(vols=(self.volatility(available_at_ms=70000),)),())
  self.assertEqual(self.generate(vols=()),())
 def test_volatility_must_match_event_start(self):self.assertEqual(self.generate(vols=(self.volatility(event_start_ms=1),)),())
 def test_selection_is_chronological_not_input_order(self):
  old=self.volatility(available_at_ms=60000,volume_ratio=1.);new=self.volatility(available_at_ms=65000)
  a=self.generate(as_of=70000,vols=(old,new));b=self.generate(as_of=70000,vols=(new,old));self.assertEqual(a,b);self.assertEqual(a[0].decision_ms,65000)
 def test_conflicting_volatility_identity_refuses(self):
  with self.assertRaises(ValueError):self.generate(vols=(self.volatility(),self.volatility(atr_fraction=.02)))
 def test_future_invalid_body_and_volatility_preflight(self):
  cls,fn=self.api()
  with self.assertRaises(ValueError):fn('BTCUSDT',(cls(0,60000,60000,100,101),cls(60000,120000,120000,100,float('nan'))),(self.volatility(),),as_of_ms=60000)
  with self.assertRaises(ValueError):self.generate(vols=(self.volatility(),self.volatility(event_start_ms=60000,available_at_ms=120000,atr_fraction=float('nan'))))
 def test_literal_closed_inputs_and_clocks(self):
  cls,fn=self.api()
  for symbol in ('btc','BTC/USDT',True):
   with self.assertRaises(ValueError):fn(symbol,(),(),as_of_ms=60000)
  for row in (cls(0,0,60000,100,101),cls(0,60000,59999,100,101),cls(True,60000,60000,100,101)):
   with self.assertRaises(ValueError):fn('BTCUSDT',(row,),(),as_of_ms=60000)
  with self.assertRaises(ValueError):self.generate(min_body_atr=True)
 def test_duplicate_or_unordered_bodies_refuse(self):
  cls,fn=self.api();a=cls(0,60000,60000,100,101)
  with self.assertRaises(ValueError):fn('BTCUSDT',(a,a),(self.volatility(),),as_of_ms=60000)
 def test_generated_signal_runs_only_existing_paper_engine(self):
  from terminan.paper import PaperEngine
  from terminan.research_signals import ResearchBar
  entry,=self.generate();signal=entry.signal;engine=PaperEngine(fee_rate='0',slippage_bps='0');engine.enabled=True
  result=engine.execute_signal(signal,(ResearchBar(60000,D('101'),D('103'),D('101'),D('102')),),bar_ms=60000,as_of_ms=120000,ambiguity_policy='SL_FIRST')
  self.assertEqual(result.fill.reason,'target');self.assertEqual(engine.positions,{})

 def test_later_revision_cannot_erase_an_earlier_emitted_signal(self):
  old=self.volatility();later=self.volatility(available_at_ms=65000,volume_ratio=1.)
  before=self.generate(as_of=60000,vols=(old,later));after=self.generate(as_of=70000,vols=(old,later))
  self.assertEqual(len(before),1);self.assertEqual(after,before);self.assertEqual(after[0].decision_ms,60000)
 def test_first_qualifying_available_revision_emits_only_once(self):
  rows=(self.volatility(volume_ratio=1.),self.volatility(available_at_ms=65000),self.volatility(available_at_ms=66000,atr_fraction=.02))
  signal,=self.generate(as_of=70000,vols=rows)
  self.assertEqual(signal.decision_ms,65000);self.assertEqual(signal.signal.stop,D('100.2425'))
 def test_obsolete_versions_before_body_availability_do_not_emit(self):
  rows=(self.volatility(),self.volatility(available_at_ms=65000,volume_ratio=1.))
  self.assertEqual(self.generate(available=70000,as_of=70000,vols=rows),())

 def test_delayed_older_body_does_not_reverse_decision_event_order(self):
  cls,fn=self.api();bodies=(cls(0,60000,130000,100,101),cls(60000,120000,120000,100,101))
  vols=(self.volatility(),self.volatility(event_start_ms=60000,available_at_ms=120000))
  before=fn('BTCUSDT',bodies,vols,as_of_ms=120000);after=fn('BTCUSDT',bodies,vols,as_of_ms=130000)
  self.assertEqual(tuple(s.decision_ms for s in before),(120000,));self.assertEqual(tuple(s.decision_ms for s in after),(120000,130000));self.assertEqual(after[:1],before)

 def _during_first_numeric_policy(self,callback,run):
  import market_math as owner
  original=owner.lossless_nonnegative_binary64_valid;called=False
  def numeric(value):
   nonlocal called
   if not called:called=True;callback()
   return original(value)
  owner.lossless_nonnegative_binary64_valid=numeric
  try:return run()
  finally:owner.lossless_nonnegative_binary64_valid=original
 def test_body_snapshot_precedes_first_math_call(self):
  cls,fn=self.api();body=cls(0,60000,60000,100,101);vol=self.volatility()
  expected=fn('BTCUSDT',(body,),(vol,),as_of_ms=60000)
  actual=self._during_first_numeric_policy(lambda:object.__setattr__(body,'close',99),lambda:fn('BTCUSDT',(body,),(vol,),as_of_ms=60000))
  self.assertEqual(actual,expected);self.assertEqual(actual[0].side,'long')
 def test_all_volatility_records_detach_before_first_math_call(self):
  cls,fn=self.api();body=cls(0,60000,60000,100,101);vol=self.volatility()
  expected=fn('BTCUSDT',(body,),(vol,),as_of_ms=60000)
  actual=self._during_first_numeric_policy(lambda:object.__setattr__(vol,'volume_ratio',0),lambda:fn('BTCUSDT',(body,),(vol,),as_of_ms=60000))
  self.assertEqual(actual,expected)
 def test_future_invalid_snapshot_cannot_be_repaired_by_numeric_callback(self):
  cls,fn=self.api();body=cls(0,60000,60000,100,101);future=cls(60000,120000,120000,100,float('nan'));vol=self.volatility()
  with self.assertRaises(ValueError):
   self._during_first_numeric_policy(lambda:object.__setattr__(future,'close',101),lambda:fn('BTCUSDT',(body,future),(vol,),as_of_ms=60000))

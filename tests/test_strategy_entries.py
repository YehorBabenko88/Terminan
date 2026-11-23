"""Pure declared strategy-entry decisions; no provider, store or execution."""
import unittest
from dataclasses import replace
from decimal import Decimal,localcontext
from unittest.mock import patch
from terminan.strategy_entries import (SignedFlowObservation,ResearchEntry,ResearchEntryPattern,EntrySide,RiskBasis,
 generate_sweep_reclaim_entries,generate_breakout_retest_entries,generate_profile_reclaim_entries)
from terminan.market_structure import OHLCObservation,MarketStructureEvent,MarketStructureKind,MarketStructureReference,MarketTimeframe
from terminan.entry_context import ProfileSummary,ProfileKind
from terminan.volatility import VolatilityMetrics,VolatilityRegime
class StrategyEntryTests(unittest.TestCase):
 def bars(self):return (OHLCObservation(60000,120000,120000,99,102,98,101),OHLCObservation(120000,180000,180000,101,102,99.9,101.2))
 def event(self,kind=MarketStructureKind.BULLISH_BOS,*,level=100,known=120000):
  return MarketStructureEvent(60000,120000,known,known,kind,MarketTimeframe.M1,level,level,level,MarketStructureReference(0,60000,60000),MarketStructureReference(60000,120000,known))
 def vol(self,*,known=180000,ratio=1.5,atr=.01,event=120000):return VolatilityMetrics(event,known,atr,.01,.01,.02,ratio,ratio,.7,VolatilityRegime.HIGH,'entry.v1')
 def profile(self,known=120000,poc=100):return ProfileSummary(poc,102,98,known,ProfileKind.TRADE_DISTRIBUTION,4)
 def profile_bars(self):return (OHLCObservation(0,60000,60000,99,99.5,98.5,99),OHLCObservation(60000,120000,120000,99,101,98.8,100.5))
 def sweep(self,*,bars=None,events=None,vols=(),cutoff=999999):return generate_sweep_reclaim_entries('BTCUSDT',self.bars() if bars is None else bars,(self.event(MarketStructureKind.BULLISH_LIQUIDITY_SWEEP,level=99),) if events is None else events,vols,as_of_ms=cutoff,timeframe=MarketTimeframe.M1)
 def retest(self,*,bars=None,events=None,vols=None,cutoff=999999,**policy):return generate_breakout_retest_entries('BTCUSDT',self.bars() if bars is None else bars,(self.event(),) if events is None else events,(self.vol(),) if vols is None else vols,as_of_ms=cutoff,timeframe=MarketTimeframe.M1,**policy)
 def reclaim(self,*,bars=None,profiles=None,flow=(),vols=(),cutoff=999999):return generate_profile_reclaim_entries('BTCUSDT',self.profile_bars() if bars is None else bars,(self.profile(),) if profiles is None else profiles,flow,vols,as_of_ms=cutoff,timeframe=MarketTimeframe.M1)
 def test_original_sweep_waits_for_confirmed_structure_and_uses_reference(self):
  x,=self.sweep(events=(self.event(MarketStructureKind.BULLISH_LIQUIDITY_SWEEP,level=99,known=180000),))
  self.assertEqual((x.pattern,x.decision_ms,x.side,x.reference),(ResearchEntryPattern.SWEEP_RECLAIM,180000,EntrySide.LONG,99));self.assertEqual(x.evidence.sweep_reference.event_start_ms,60000)
 def test_sweep_decision_includes_actual_candle_availability(self):
  bars=self.bars();bars=(replace(bars[0],available_at_ms=240000),bars[1]);self.assertEqual(self.sweep(bars=bars)[0].decision_ms,240000);self.assertEqual(self.sweep(bars=bars,cutoff=239999),())
 def test_original_breakout_bar_is_not_reused_as_retest(self):
  x,=self.retest();self.assertEqual((x.decision_ms,x.reference,x.evidence.break_reference.available_at_ms),(180000,100,120000));self.assertEqual(x.signal.side,'long');self.assertEqual(x.evidence.volume_ratio,1.5)
 def test_retest_requires_later_event_and_strictly_later_decision(self):
  self.assertEqual(self.retest(bars=(self.bars()[0],)),());self.assertEqual(self.retest(events=(self.event(known=180000),)),())
  bars=self.bars();bars=(replace(bars[0],available_at_ms=300000),bars[1]);self.assertEqual(self.retest(bars=bars,events=(self.event(known=240000),)),())
 def test_retest_volume_threshold_and_first_qualifying_candidate(self):
  bars=self.bars()+(OHLCObservation(180000,240000,240000,101,102,100,101.5),)
  x,=self.retest(bars=bars,vols=(self.vol(ratio=1),self.vol(known=240000,ratio=2,event=180000)))
  self.assertEqual(x.decision_ms,240000)
  self.assertEqual(self.retest(vols=()),())
 def test_retest_first_qualifying_is_by_actual_decision_clock(self):
  bars=self.bars();bars=(bars[0],replace(bars[1],available_at_ms=300000),OHLCObservation(180000,240000,240000,101,102,100,101.5))
  self.assertEqual(self.retest(bars=bars)[0].decision_ms,240000)
 def test_retest_wait_bound_uses_declared_cadence_and_never_scans_break_bar(self):
  self.assertTrue(self.retest(max_wait_bars=1));bars=self.bars()+(OHLCObservation(180000,240000,240000,101,102,100,101.5),)
  self.assertEqual(self.retest(bars=bars,vols=(self.vol(known=240000),),max_wait_bars=1),())
 def test_original_profile_reclaim_requires_profile_known_by_decision(self):
  x,=self.reclaim();self.assertEqual((x.pattern,x.decision_ms,x.side,x.reference),(ResearchEntryPattern.PROFILE_RECLAIM,120000,EntrySide.LONG,100));self.assertEqual(x.evidence.profile_kind,ProfileKind.TRADE_DISTRIBUTION)
  self.assertEqual(self.reclaim(profiles=(self.profile(120001),)),())
 def test_profile_reclaim_includes_previous_candle_availability(self):
  bars=self.profile_bars();bars=(replace(bars[0],available_at_ms=240000),bars[1]);x,=self.reclaim(bars=bars)
  self.assertEqual(x.decision_ms,240000);self.assertEqual(self.reclaim(bars=bars,cutoff=239999),())
 def test_profile_flow_missing_stays_none_and_actual_zero_is_not_missing(self):
  x,=self.reclaim();self.assertIsNone(x.evidence.flow);self.assertIsNone(x.metadata['delta']);self.assertIsNone(x.context['volatility']);self.assertIs(x.evidence.risk_basis,RiskBasis.POLICY_DEFAULT);self.assertEqual(x.evidence.risk_atr_fraction,.002)
  for delta in (0,-1):self.assertEqual(self.reclaim(flow=(SignedFlowObservation(60000,120000,delta),)),())
  x,=self.reclaim(flow=(SignedFlowObservation(60000,120000,2),));self.assertEqual(x.evidence.flow.delta,2)
 def test_no_future_flow_or_volatility_is_used(self):
  x,=self.reclaim(flow=(SignedFlowObservation(60000,120001,-5),),vols=(self.vol(known=120001),));self.assertIsNone(x.evidence.flow);self.assertIs(x.evidence.risk_basis,RiskBasis.POLICY_DEFAULT)
 def test_latest_profile_volatility_and_flow_are_selected_by_clock_not_position(self):
  profiles=(self.profile(120000,100),self.profile(60000,100.2));vols=(self.vol(known=120000,atr=.02),self.vol(known=60000,atr=.01,event=0));flows=(SignedFlowObservation(60000,120000,2),SignedFlowObservation(0,60000,-3))
  x,=self.reclaim(profiles=profiles,vols=vols,flow=flows);self.assertEqual(x.reference,100);self.assertEqual(x.evidence.risk_atr_fraction,.02);self.assertEqual(x.evidence.flow.delta,2);self.assertIs(x.evidence.risk_basis,RiskBasis.OBSERVED_ATR)
 def test_short_sweep_retest_and_profile_cross(self):
  x,=self.sweep(events=(self.event(MarketStructureKind.BEARISH_LIQUIDITY_SWEEP,level=102),));self.assertIs(x.side,EntrySide.SHORT)
  bars=(OHLCObservation(60000,120000,120000,101,102,98,99),OHLCObservation(120000,180000,180000,99,100.1,98,99))
  x,=self.retest(bars=bars,events=(self.event(MarketStructureKind.BEARISH_BOS),));self.assertIs(x.side,EntrySide.SHORT)
  bars=(OHLCObservation(0,60000,60000,101,102,100,101),OHLCObservation(60000,120000,120000,101,102,98,99))
  x,=self.reclaim(bars=bars,flow=(SignedFlowObservation(60000,120000,-1),));self.assertIs(x.side,EntrySide.SHORT)
 def test_math_retest_predicate_and_brackets_are_sole_geometry_owners(self):
  with patch('market_math.research_retest_matches',return_value=False):self.assertEqual(self.retest(),())
  with patch('market_math.research_bracket_prices',side_effect=ValueError('BRACKET_OWNER_REFUSED')):
   with self.assertRaisesRegex(ValueError,'BRACKET_OWNER_REFUSED'):self.reclaim()
  with patch('market_math.research_retest_matches',side_effect=ValueError('RETEST_OWNER_REFUSED')):
   with self.assertRaisesRegex(ValueError,'RETEST_OWNER_REFUSED'):self.retest()
 def test_signal_risk_equals_math_decimal_presentation_and_uses_market_entry(self):
  import market_math
  x,=self.retest();self.assertEqual((x.signal.stop,x.signal.target),market_math.research_bracket_prices(101.2,.01,'long').as_decimal());self.assertIsNone(x.signal.entry_price);self.assertEqual(x.signal.entry_kind,'market');self.assertEqual(x.signal.symbol,'BTCUSDT')
 def test_future_invalid_structures_refuse_even_if_irrelevant_kind(self):
  e=self.event(known=600000);bad=replace(e,level=float('nan'))
  with self.assertRaises(ValueError):self.sweep(events=(bad,),cutoff=0)
  conflict=replace(e,level=101,low=101,high=101)
  with self.assertRaises(ValueError):self.retest(events=(e,conflict),cutoff=0)
 def test_future_invalid_flow_summary_and_ohlc_refuse_entire_batch(self):
  for delta in (True,float('nan'),float('inf'),2**53+1,Decimal(1)):
   with self.assertRaises(ValueError):self.reclaim(flow=(SignedFlowObservation(900000,900000,delta),),cutoff=0)
  p=self.profile(900000);object.__setattr__(p,'poc',float('nan'))
  with self.assertRaises(ValueError):self.reclaim(profiles=(p,),cutoff=0)
  v=self.vol(known=900000);object.__setattr__(v,'atr_fraction',float('nan'))
  with self.assertRaises(ValueError):self.sweep(vols=(v,),cutoff=0)
  bars=self.bars()+(OHLCObservation(180000,240000,900000,1,float('nan'),1,1),)
  with self.assertRaises(ValueError):self.retest(bars=bars,cutoff=0)
 def test_flow_identity_conflicts_refuse_future_and_identical_duplicates_are_harmless(self):
  a=SignedFlowObservation(60000,120000,2)
  self.assertEqual(self.reclaim(flow=(a,a)),self.reclaim(flow=(a,)))
  for b in (replace(a,delta=3),replace(a,delta=2.0)):
   for rows in ((a,b),(b,a)):
    with self.assertRaises(ValueError):self.reclaim(flow=rows,cutoff=0)
 def test_structure_and_summary_duplicates_are_not_input_order_choices(self):
  e=self.event();self.assertEqual(self.retest(events=(e,e)),self.retest(events=(e,)))
  p=self.profile();q=self.profile(poc=100.2)
  for profiles in ((p,q),(q,p)):
   with self.assertRaises(ValueError):self.reclaim(profiles=profiles)
 def test_all_inputs_detach_before_first_numeric_owner_call(self):
  import market_math
  bars=self.profile_bars();p=self.profile();v=self.vol(known=120000);f=SignedFlowObservation(60000,120000,2);original=market_math.lossless_nonnegative_binary64_valid
  def mutate_then_validate(value):
   object.__setattr__(bars[-1],'close',99);object.__setattr__(p,'poc',200);object.__setattr__(v,'atr_fraction',.5);object.__setattr__(f,'delta',-2)
   return original(value)
  with patch('market_math.lossless_nonnegative_binary64_valid',side_effect=mutate_then_validate):
   x,=self.reclaim(bars=bars,profiles=(p,),vols=(v,),flow=(f,));self.assertEqual((x.reference,x.evidence.risk_atr_fraction,x.evidence.flow.delta),(100,.01,2))
 def test_valid_future_append_cannot_change_already_emitted_prefix(self):
  before=self.reclaim(cutoff=120000);bars=self.profile_bars()+(OHLCObservation(120000,180000,180000,100.5,102,100,101),)
  self.assertEqual(self.reclaim(bars=bars,profiles=(self.profile(),self.profile(180000,101)),cutoff=120000),before)
  self.assertEqual(self.retest(cutoff=180000),self.retest(bars=self.bars()+(OHLCObservation(180000,240000,240000,101,102,100,101.5),),cutoff=180000))
 def test_literal_symbols_timeframes_clocks_containers_and_policies(self):
  for symbol in ('x','BTC/USDT',None,True):
   with self.assertRaises(ValueError):generate_profile_reclaim_entries(symbol,self.profile_bars(),(),as_of_ms=120000,timeframe=MarketTimeframe.M1)
  for tf in ('1m',MarketTimeframe.H1,None):
   with self.assertRaises(ValueError):generate_profile_reclaim_entries('BTCUSDT',self.profile_bars(),(),as_of_ms=120000,timeframe=tf)
  for clock in (True,-1,1.0,2**53):
   with self.assertRaises(ValueError):self.reclaim(cutoff=clock)
  for kwargs in ({'max_wait_bars':True},{'max_wait_bars':0},{'max_wait_bars':4097},{'retest_tolerance':float('nan')},{'min_volume_ratio':-1}):
   with self.assertRaises(ValueError):self.retest(**kwargs)
 def test_hostile_containers_rows_and_flow_values_refuse_callbacks(self):
  class Rows(list):
   def __iter__(self):raise AssertionError('FOREIGN_ITERATION')
  class Flow(SignedFlowObservation):pass
  class Delta(float):
   def __float__(self):raise AssertionError('FOREIGN_FLOAT')
  with self.assertRaises(ValueError):self.reclaim(bars=Rows(self.profile_bars()))
  with self.assertRaises(ValueError):self.reclaim(flow=(Flow(0,0,1),))
  with self.assertRaises(ValueError):self.reclaim(flow=(SignedFlowObservation(0,0,Delta(1)),))
 def test_decimal_context_untouched_and_outputs_frozen_readonly_no_authority(self):
  with localcontext() as c:
   c.prec=2
   for flag in c.flags:c.flags[flag]=True;c.traps[flag]=True
   before=(dict(c.flags),dict(c.traps));x,=self.reclaim();self.assertEqual((dict(c.flags),dict(c.traps)),before)
  self.assertFalse(x.execution_authority);self.assertFalse(x.trading_authorized);self.assertEqual(x.source_authentication,'NOT_EVALUATED');self.assertFalse(x.context['execution_authority'])
  with self.assertRaises(AttributeError):x.reference=0
  with self.assertRaises(TypeError):x.context['profile']['poc']=0
  with self.assertRaises(TypeError):x.metadata['delta']=0
 def test_disabled_canonical_paper_engine_remains_disabled(self):
  from terminan.paper import PaperEngine
  x,=self.reclaim();e=PaperEngine();self.assertIs(e.enabled,False)
  with self.assertRaisesRegex(ValueError,'disabled'):e.execute_signal(x.signal,(),bar_ms=60000,as_of_ms=x.decision_ms)
  self.assertEqual(e.positions,{});self.assertEqual(e.fills,[])

 def test_sweep_output_is_sorted_by_decision_and_input_event_permutation(self):
  a=self.event(MarketStructureKind.BULLISH_LIQUIDITY_SWEEP,level=99,known=300000)
  b=MarketStructureEvent(120000,180000,180000,180000,MarketStructureKind.BEARISH_LIQUIDITY_SWEEP,MarketTimeframe.M1,102,102,102,MarketStructureReference(0,60000,60000),MarketStructureReference(120000,180000,180000))
  x=self.sweep(events=(a,b));self.assertEqual([e.decision_ms for e in x],[180000,300000]);self.assertEqual(x,self.sweep(events=(b,a)))
 def test_outside_wait_window_earlier_arrival_does_not_stop_late_eligible_retest(self):
  bars=self.bars();bars=(bars[0],replace(bars[1],available_at_ms=360000),OHLCObservation(180000,240000,240000,101,102,100,101.5))
  x,=self.retest(bars=bars,max_wait_bars=1);self.assertEqual(x.decision_ms,360000)
 def test_future_volatility_update_does_not_erase_first_retest(self):
  x=self.retest();self.assertEqual(self.retest(vols=(self.vol(known=240000,ratio=0,event=180000),self.vol())),x)
 def test_structure_timeframe_mismatch_refuses_even_if_no_selected_pattern(self):
  event=self.event();scale=lambda r:MarketStructureReference(r.event_start_ms*5,r.event_end_ms*5,r.available_at_ms*5)
  other=replace(event,event_start_ms=300000,event_end_ms=600000,available_at_ms=600000,source_available_at_ms=600000,timeframe=MarketTimeframe.M5,swing_reference=scale(event.swing_reference),trigger_reference=scale(event.trigger_reference))
  with self.assertRaises(ValueError):self.sweep(events=(other,))
 def test_retest_owner_must_return_exact_bool_and_exact_bracket_record(self):
  with patch('market_math.research_retest_matches',return_value=1):
   with self.assertRaises(ValueError):self.retest()
  with patch('market_math.research_bracket_prices',return_value=(1,2)):
   with self.assertRaises(ValueError):self.sweep()
 def test_signed_flow_math_refusal_propagates_before_entry(self):
  with patch('market_math.lossless_binary64_valid',side_effect=ValueError('SIGNED_OWNER_REFUSED')):
   with self.assertRaisesRegex(ValueError,'SIGNED_OWNER_REFUSED'):self.reclaim(flow=(SignedFlowObservation(60000,120000,1),))
 def test_policy_fallback_is_labeled_and_uses_existing_math_bracket(self):
  import market_math
  x,=self.reclaim();self.assertEqual((x.signal.stop,x.signal.target),market_math.research_bracket_prices(100.5,.002,'long').as_decimal());self.assertIsNone(x.evidence.volatility_regime);self.assertIsNone(x.metadata['volatility_regime']);self.assertIn('NOT_OBSERVED',x.metadata['risk_basis'])
 def test_original_pattern_metadata_values_have_typed_canonical_locations(self):
  x,=self.sweep(vols=(self.vol(known=120000),));self.assertEqual((x.metadata['level'],x.metadata['sweep_event_start_ms'],x.metadata['volatility_regime']),(99,60000,'HIGH'))
  x,=self.retest();self.assertEqual((x.metadata['break_available_at_ms'],x.metadata['volume_ratio']),(120000,1.5))
  x,=self.reclaim(flow=(SignedFlowObservation(60000,120000,3),));self.assertEqual((x.metadata['poc'],x.metadata['profile_kind'],x.metadata['delta']),(100,'TRADE_DISTRIBUTION',3))
 def test_returned_evidence_never_retains_caller_record_identity(self):
  p=self.profile();v=self.vol(known=120000);f=SignedFlowObservation(60000,120000,3);x,=self.reclaim(profiles=(p,),vols=(v,),flow=(f,));self.assertIsNot(x.evidence.flow,f)
  object.__setattr__(f,'delta',-8);object.__setattr__(p,'poc',200);object.__setattr__(v,'atr_fraction',1)
  self.assertEqual((x.reference,x.evidence.flow.delta,x.context['profile']['poc'],x.evidence.risk_atr_fraction),(100,3,100,.01))
 def test_duplicate_summary_identity_with_numeric_type_conflict_refuses(self):
  a=self.profile(poc=100);b=self.profile(poc=100.0)
  with self.assertRaises(ValueError):self.reclaim(profiles=(a,b))
 def test_flow_clock_order_and_tampered_authority_refuse_future(self):
  for f in (SignedFlowObservation(2,1,1),SignedFlowObservation(True,2,1),SignedFlowObservation(0,2**53,1)):
   with self.assertRaises(ValueError):self.reclaim(flow=(f,),cutoff=0)
  f=SignedFlowObservation(0,900000,1);object.__setattr__(f,'execution_authority',True)
  with self.assertRaises(ValueError):self.reclaim(flow=(f,),cutoff=0)
 def test_bounded_ohlc_flow_and_summary_inputs_refuse_before_iteration(self):
  with self.assertRaises(ValueError):self.reclaim(bars=[self.profile_bars()[0]]*4097)
  with self.assertRaises(ValueError):self.reclaim(flow=[SignedFlowObservation(0,0,1)]*513)
  with self.assertRaises(ValueError):self.reclaim(vols=[self.vol()]*513)
 def test_missing_matching_sweep_candle_or_no_cross_emits_nothing(self):
  self.assertEqual(self.sweep(bars=()),());self.assertEqual(self.reclaim(profiles=()),())
  bars=self.profile_bars();self.assertEqual(self.reclaim(bars=(bars[0],replace(bars[1],close=99))),())
 def test_candle_finance_policy_positive_ordered_and_contiguous(self):
  bars=self.profile_bars()
  for bad in (replace(bars[1],open=102),replace(bars[1],low=0),replace(bars[1],event_start_ms=60001),replace(bars[1],available_at_ms=119999)):
   with self.assertRaises(ValueError):self.reclaim(bars=(bars[0],bad))
 def test_retest_context_does_not_use_future_volume_ratio(self):
  self.assertEqual(self.retest(vols=(self.vol(known=180001),),cutoff=180000),())
 def test_profile_pair_decisions_sorted_when_prior_candles_arrive_out_of_order(self):
  bars=(OHLCObservation(0,60000,300000,99,100,98,99),OHLCObservation(60000,120000,120000,99,102,98,101),OHLCObservation(120000,180000,180000,101,102,98,99),OHLCObservation(180000,240000,240000,99,102,98,101))
  out=self.reclaim(bars=bars,profiles=(self.profile(60000),));self.assertEqual([x.decision_ms for x in out],[180000,240000,300000]);self.assertEqual([x.side for x in out],[EntrySide.SHORT,EntrySide.LONG,EntrySide.LONG])

 def test_profile_proxy_kind_is_preserved_without_trade_coverage_claim(self):
  x,=self.reclaim(profiles=(replace(self.profile(),kind=ProfileKind.CANDLE_PROXY),));self.assertIs(x.evidence.profile_kind,ProfileKind.CANDLE_PROXY);self.assertEqual(x.context['profile']['kind'],'CANDLE_PROXY');self.assertEqual(x.source_authentication,'NOT_EVALUATED')
 def test_future_structure_authority_or_summary_identity_conflict_never_bypassed(self):
  event=self.event(known=900000);object.__setattr__(event,'trading_authorized',True)
  with self.assertRaises(ValueError):self.sweep(events=(event,),cutoff=0)
  a=self.vol(known=900000);b=replace(a,atr_fraction=.02)
  with self.assertRaises(ValueError):self.retest(events=(),vols=(a,b),cutoff=0)
 def test_exact_raw_archives_preserve_five_original_tests_and_zero_deduction(self):
  import ast,hashlib,json,pathlib
  p=pathlib.Path(__file__).resolve().parents[1]/'docs/provenance/strategy-entry-transfer';m=json.loads((p/'SOURCE.json').read_text());count=0
  for row in m['sources']:
   raw=(p/row['archive']).read_bytes();self.assertEqual(len(raw),row['bytes']);self.assertEqual(hashlib.sha256(raw).hexdigest(),row['sha256']);self.assertEqual(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),row['blob'])
   if row['path'].startswith('tests/'):count+=sum(isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name.startswith('test_') for n in ast.walk(ast.parse(raw)))
  self.assertEqual(count,5);self.assertEqual(m['originalGeneratorGoldenFunctionsReexpressed'],3);self.assertEqual(m['remainingDeclaredLegacyTestFunctions'],516);self.assertEqual(m['retirementDeduction'],0);self.assertFalse(m['oldSourcesOrConsumersRemoved'])

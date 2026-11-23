"""Pure declared-time market state; no IO, feed, paper engine or execution."""
import unittest
from dataclasses import replace
from decimal import localcontext
from unittest.mock import patch
from terminan.market_structure import (OHLCObservation,MarketTimeframe,MarketStructureKind,MarketDirection,
    MarketStructureContext,analyze_market_structure,build_multi_timeframe_structure)
class MarketStructureTests(unittest.TestCase):
 def rows(self,values=None,*,step=60000,delays=None):
  values=values or ((8,9,7,8),(8,10,8,9),(9,9.5,8,9),(9,11,9,10.5))
  return tuple(OHLCObservation(i*step,(i+1)*step,(delays or {}).get(i,(i+1)*step),*row) for i,row in enumerate(values))
 def analyze(self,rows=None,*,cutoff=10**8,left=1,right=1,timeframe=MarketTimeframe.M1):
  return analyze_market_structure(self.rows() if rows is None else rows,as_of_ms=cutoff,timeframe=timeframe,left=left,right=right)
 def kinds(self,out,kind):return [x for x in out if x.kind is kind]
 def test_original_break_known_only_on_trigger_availability(self):
  event,=self.kinds(self.analyze(),MarketStructureKind.BULLISH_BOS)
  self.assertEqual((event.event_start_ms,event.available_at_ms,event.level),(180000,240000,10))
  self.assertEqual((event.swing_reference.event_start_ms,event.swing_reference.available_at_ms),(60000,180000))
  self.assertEqual(event.trigger_reference.available_at_ms,240000)
  self.assertEqual(self.kinds(self.analyze(cutoff=239999),MarketStructureKind.BULLISH_BOS),[])
 def test_original_sweep_rejects_back_through_level(self):
  rows=self.rows(((8,9,7,8),(8,10,8,9),(9,9.5,8,9),(9,10.5,8.8,9.5)))
  event,=self.kinds(self.analyze(rows),MarketStructureKind.BEARISH_LIQUIDITY_SWEEP)
  self.assertEqual((event.event_start_ms,event.available_at_ms,event.level),(180000,240000,10))
  self.assertFalse(self.kinds(self.analyze(rows),MarketStructureKind.BULLISH_BOS))
 def test_original_opposing_order_block_only_after_break(self):
  rows=self.rows(((8,9,7,8.5),(9.5,10,8,8.5),(8.5,9.5,8,9),(9,11,8.9,10.5)))
  event,=self.kinds(self.analyze(rows),MarketStructureKind.BULLISH_ORDER_BLOCK)
  self.assertEqual((event.event_start_ms,event.available_at_ms,event.low,event.high),(60000,240000,8,10))
  self.assertEqual(event.trigger_reference.event_start_ms,180000)
  self.assertFalse(self.kinds(self.analyze(rows,cutoff=239999),MarketStructureKind.BULLISH_ORDER_BLOCK))
 def test_original_level_breaks_only_once(self):
  rows=self.rows()+ (OHLCObservation(240000,300000,300000,10.5,12,10,11.5),)
  self.assertEqual(len([x for x in self.analyze(rows) if x.kind in (MarketStructureKind.BULLISH_BOS,MarketStructureKind.BULLISH_CHOCH) and x.level==10]),1)
 def test_opposite_break_changes_character_in_both_directions(self):
  vals=((8,9,7,8),(8,10,8,9),(9,9.5,8,9),(9,11,8.9,10.5),(10.5,10.8,7,8),(8,9,8,8.5),(8.5,9,6,6.5))
  self.assertEqual(len(self.kinds(self.analyze(self.rows(vals)),MarketStructureKind.BEARISH_CHOCH)),1)
  mirror=tuple((20-o,20-l,20-h,20-c) for o,h,l,c in vals)
  self.assertEqual(len(self.kinds(self.analyze(self.rows(mirror)),MarketStructureKind.BULLISH_CHOCH)),1)
 def test_sweep_does_not_consume_unbroken_level(self):
  vals=((8,9,7,8),(8,10,8,9),(9,9.5,8,9),(9,10.5,8.8,9.5),(9.5,11,9,9.6),(9.6,12,9,10.5))
  out=self.analyze(self.rows(vals));self.assertEqual(len(self.kinds(out,MarketStructureKind.BEARISH_LIQUIDITY_SWEEP)),2);self.assertEqual(len(self.kinds(out,MarketStructureKind.BULLISH_BOS)),1)
 def test_decisions_follow_availability_before_event_time(self):
  vals=((7,10,5,7),(7,12,4,7),(7,10,5,7),(7,13,6,12.5),(7,11,3,3.5))
  out=self.analyze(self.rows(vals,delays={3:600000}))
  self.assertEqual([(x.kind,x.event_start_ms,x.available_at_ms) for x in out if x.kind in (MarketStructureKind.BULLISH_CHOCH,MarketStructureKind.BEARISH_BOS)],[(MarketStructureKind.BEARISH_BOS,240000,300000),(MarketStructureKind.BULLISH_CHOCH,180000,600000)])
 def test_swing_must_be_known_by_trigger_start_not_its_late_close(self):
  out=self.analyze(self.rows(delays={0:200000,3:600000}))
  self.assertFalse(self.kinds(out,MarketStructureKind.BULLISH_BOS))
 def test_latest_visible_level_uses_event_time_not_known_sort(self):
  vals=((8,9,7,8),(9,10,8,9),(9,9,8,9),(9,12,8,9),(9,9,8,9),(9,9,8,9),(9,9,8,9),(9,13,8,12.5))
  event,=self.kinds(self.analyze(self.rows(vals,delays={0:400000})),MarketStructureKind.BULLISH_BOS)
  self.assertEqual((event.level,event.swing_reference.event_start_ms),(12,180000))
 def test_late_opposing_candidate_not_available_at_trigger_is_excluded(self):
  vals=((8,9,7,8),(8,10,8,9),(9,9.5,8,9),(9.5,9.7,8,9),(9,11,8.9,10.5))
  out=self.analyze(self.rows(vals,delays={3:500000}),cutoff=300000)
  self.assertEqual(len(self.kinds(out,MarketStructureKind.BULLISH_BOS)),1);self.assertFalse(self.kinds(out,MarketStructureKind.BULLISH_ORDER_BLOCK))
 def test_later_event_candidate_excluded_even_if_available_before_delayed_trigger(self):
  vals=((8,9,7,8),(8,10,8,9),(9,9.5,8,9),(9,11,8.9,10.5),(9.7,9.8,8,9.2))
  out=self.analyze(self.rows(vals,delays={3:600000}))
  self.assertEqual(len(self.kinds(out,MarketStructureKind.BULLISH_BOS)),1);self.assertFalse(self.kinds(out,MarketStructureKind.BULLISH_ORDER_BLOCK))
 def test_latest_eligible_order_block_is_selected_by_event_time(self):
  vals=((8,9,7,8),(9.5,10,8,8.5),(9,9.5,8,8.8),(9,9.7,8,8.7),(9,9.8,8,8.6),(9,11,8.9,10.5))
  event,=self.kinds(self.analyze(self.rows(vals,delays={3:350000})),MarketStructureKind.BULLISH_ORDER_BLOCK)
  self.assertEqual(event.event_start_ms,240000)
 def test_future_append_does_not_change_known_prefix(self):
  rows=self.rows();out=self.analyze(rows,cutoff=240000)
  self.assertEqual(self.analyze(rows+(OHLCObservation(240000,300000,300000,10.5,12,10,11.5),),cutoff=240000),out)
 def test_delayed_left_confirmation_dependency_is_respected(self):
  out=self.analyze(self.rows(delays={0:500000}),cutoff=240000)
  self.assertFalse([x for x in out if x.kind in (MarketStructureKind.HIGH_SWING,MarketStructureKind.BULLISH_BOS)])
 def test_input_is_detached_before_first_math_policy_call(self):
  import market_math
  rows=self.rows();original=market_math.candle_ohlcv_valid
  def mutate_then_validate(*args):
   object.__setattr__(rows[-1],'available_at_ms',999999);object.__setattr__(rows[-1],'close',9)
   return original(*args)
  with patch('market_math.candle_ohlcv_valid',side_effect=mutate_then_validate):
   event,=self.kinds(self.analyze(rows,cutoff=240000),MarketStructureKind.BULLISH_BOS)
   self.assertEqual(event.available_at_ms,240000)
 def test_invalid_future_prices_refuse_entire_batch(self):
  for value in (float('nan'),float('inf'),-1,True,'9',2**53+1):
   bad=OHLCObservation(240000,300000,300000,9,value,8,9)
   with self.assertRaises(ValueError):self.analyze(self.rows()+(bad,),cutoff=240000)
 def test_financial_ohlc_policy_is_positive_and_ordered(self):
  for row in (OHLCObservation(0,60000,60000,0,1,0,0),OHLCObservation(0,60000,60000,12,10,8,9),OHLCObservation(0,60000,60000,9,10,8,11),OHLCObservation(0,60000,60000,9,8,10,9)):
   with self.assertRaises(ValueError):self.analyze((row,))
 def test_literal_clocks_and_declared_timeframe_cadence(self):
  rows=self.rows()
  for row in (replace(rows[0],event_start_ms=True),replace(rows[0],available_at_ms=59999),replace(rows[0],event_end_ms=0),replace(rows[1],event_start_ms=60001)):
   with self.assertRaises(ValueError):self.analyze((row,))
  with self.assertRaises(ValueError):self.analyze(rows,timeframe=MarketTimeframe.H1)
  for cutoff in (True,None,-1,1.,2**53):
   with self.assertRaises(ValueError):self.analyze(cutoff=cutoff)
 def test_literal_containers_rows_and_prices_refuse_callbacks(self):
  class Rows(list):
   def __iter__(self):raise AssertionError('FOREIGN_ITERATION')
  class Row(OHLCObservation):pass
  class Price(float):
   def __float__(self):raise AssertionError('FOREIGN_FLOAT')
  for rows in (Rows(self.rows()),(Row(0,60000,60000,8,9,7,8),),(OHLCObservation(0,60000,60000,8,Price(9),7,8),)):
   with self.assertRaises(ValueError):self.analyze(rows)
 def test_literal_window_and_bounded_batch(self):
  for left,right in ((True,1),(0,1),(1,0),(65,1),(1,1.)):
   with self.assertRaises(ValueError):self.analyze(left=left,right=right)
  with self.assertRaises(ValueError):self.analyze([self.rows()[0]]*4097)
 def test_math_refusal_has_no_fallback(self):
  for target in ('price_structure_patterns','candle_ohlcv_valid'):
   with patch('market_math.'+target,side_effect=ValueError('OWNER_REFUSED')):
    with self.assertRaisesRegex(ValueError,'OWNER_REFUSED'):self.analyze()
  with patch('market_math.lossless_nonnegative_binary64_valid',return_value=False):
   with self.assertRaises(ValueError):self.analyze()
 def test_malformed_math_record_is_refused(self):
  import market_math
  with patch('market_math.price_structure_patterns',return_value=(market_math.PriceStructurePattern(1,99,10,10,0,3),)):
   with self.assertRaises(ValueError):self.analyze()
 def test_decimal_context_is_unchanged_and_numeric_values_preserved(self):
  with localcontext() as c:
   c.prec=2
   for flag in c.flags:c.flags[flag]=True;c.traps[flag]=True
   before=(dict(c.flags),dict(c.traps));event,=self.kinds(self.analyze(),MarketStructureKind.BULLISH_BOS)
   self.assertEqual(event.level,10);self.assertIs(type(event.level),int);self.assertEqual((dict(c.flags),dict(c.traps)),before)
 def test_analysis_events_are_frozen_and_never_authority(self):
  for event in self.analyze():
   self.assertFalse(event.execution_authority);self.assertFalse(event.trading_authorized);self.assertEqual(event.source_authentication,'NOT_EVALUATED');self.assertEqual(event.availability_basis,'CALLER_DECLARED_CAUSAL_DEPENDENCIES')
   with self.assertRaises(AttributeError):event.level=0
 def test_mtf_original_source_timeframe_and_confirmation(self):
  out=build_multi_timeframe_structure({MarketTimeframe.H1:self.rows(step=3600000),MarketTimeframe.M5:self.rows(step=300000)},as_of_ms=14400000,left=1,right=1)
  self.assertEqual({x.timeframe for x in out},{MarketTimeframe.H1,MarketTimeframe.M5});ctx=MarketStructureContext(out)
  self.assertIsNone(ctx.bias_at(1000,MarketTimeframe.H1));self.assertIs(ctx.bias_at(14400000,MarketTimeframe.H1).direction,MarketDirection.BULLISH)
 def test_mtf_original_higher_timeframe_alignment(self):
  ctx=MarketStructureContext(build_multi_timeframe_structure({MarketTimeframe.H1:self.rows(step=3600000)},as_of_ms=14400000,left=1,right=1))
  self.assertFalse(ctx.alignment_at(1000,entry_timeframe=MarketTimeframe.M5,bias_timeframe=MarketTimeframe.H1,direction=MarketDirection.BULLISH).aligned)
  alignment=ctx.alignment_at(14400000,entry_timeframe=MarketTimeframe.M5,bias_timeframe=MarketTimeframe.H1,direction=MarketDirection.BULLISH)
  self.assertTrue(alignment.aligned);self.assertFalse(alignment.execution_authority);self.assertFalse(alignment.trading_authorized);self.assertFalse(alignment.bias.execution_authority)
 def test_context_latest_known_is_independent_of_list_order(self):
  vals=((7,10,5,7),(7,12,4,7),(7,10,5,7),(7,13,6,12.5),(7,11,3,3.5));events=self.analyze(self.rows(vals,delays={3:600000}))
  a=MarketStructureContext(events);b=MarketStructureContext(tuple(reversed(events)))
  self.assertEqual(a.bias_at(600000,MarketTimeframe.M1),b.bias_at(600000,MarketTimeframe.M1));self.assertIs(a.bias_at(300000,MarketTimeframe.M1).direction,MarketDirection.BEARISH);self.assertIs(a.bias_at(600000,MarketTimeframe.M1).direction,MarketDirection.BULLISH)
 def test_mtf_detaches_all_series_before_first_math_call(self):
  import market_math
  fast=self.rows(step=300000);slow=self.rows(step=3600000);original=market_math.price_structure_patterns
  def mutate_then_compute(*args,**kw):
   object.__setattr__(slow[-1],'available_at_ms',999999999)
   return original(*args,**kw)
  with patch('market_math.price_structure_patterns',side_effect=mutate_then_compute):
   out=build_multi_timeframe_structure({MarketTimeframe.M5:fast,MarketTimeframe.H1:slow},as_of_ms=14400000,left=1,right=1)
  self.assertTrue([x for x in out if x.timeframe is MarketTimeframe.H1 and x.kind is MarketStructureKind.BULLISH_BOS])
 def test_timeframes_directions_and_higher_order_are_explicit(self):
  ctx=MarketStructureContext(self.analyze())
  for tf in ('1m',None,True):
   with self.assertRaises(ValueError):ctx.bias_at(240000,tf)
   with self.assertRaises(ValueError):self.analyze(timeframe=tf)
  for tf in (MarketTimeframe.M1,MarketTimeframe.M5):
   with self.assertRaises(ValueError):ctx.alignment_at(240000,entry_timeframe=MarketTimeframe.M5,bias_timeframe=tf,direction=MarketDirection.BULLISH)
  with self.assertRaises(ValueError):ctx.alignment_at(240000,entry_timeframe=MarketTimeframe.M1,bias_timeframe=MarketTimeframe.H1,direction='bullish')
 def test_context_is_detached_and_rejects_nonliteral_events(self):
  events=list(self.analyze());ctx=MarketStructureContext(events);bos=self.kinds(events,MarketStructureKind.BULLISH_BOS)[0];object.__setattr__(bos,'kind',MarketStructureKind.BEARISH_BOS);events.clear()
  self.assertIs(ctx.bias_at(240000,MarketTimeframe.M1).direction,MarketDirection.BULLISH)
  with self.assertRaises(ValueError):MarketStructureContext([{}])
 def test_context_rejects_tampered_authority_and_invalid_clock(self):
  event=self.kinds(self.analyze(),MarketStructureKind.BULLISH_BOS)[0];object.__setattr__(event,'execution_authority',True)
  with self.assertRaises(ValueError):MarketStructureContext((event,))
  event=self.kinds(self.analyze(),MarketStructureKind.BULLISH_BOS)[0]
  with self.assertRaises(ValueError):MarketStructureContext((replace(event,available_at_ms=0),))
 def test_mtf_hostile_mapping_and_untrusted_future_series_refuse_whole_batch(self):
  class Series(dict):
   def items(self):raise AssertionError('FOREIGN_ITEMS')
  with self.assertRaises(ValueError):build_multi_timeframe_structure(Series(),as_of_ms=240000)
  with self.assertRaises(ValueError):build_multi_timeframe_structure({'1m':self.rows()},as_of_ms=240000)
  bad=list(self.rows(step=3600000));bad[-1]=replace(bad[-1],open=float('nan'))
  with self.assertRaises(ValueError):build_multi_timeframe_structure({MarketTimeframe.M1:self.rows(),MarketTimeframe.H1:bad},as_of_ms=240000,left=1,right=1)

 def test_tied_decision_availability_uses_event_start_order(self):
  vals=((7,10,5,7),(7,12,4,7),(7,10,5,7),(7,13,6,12.5),(7,11,3,3.5))
  out=self.analyze(self.rows(vals,delays={3:300000}))
  self.assertEqual([(e.kind,e.event_start_ms) for e in out if e.kind in (MarketStructureKind.BULLISH_BOS,MarketStructureKind.BEARISH_CHOCH)],[(MarketStructureKind.BULLISH_BOS,180000),(MarketStructureKind.BEARISH_CHOCH,240000)])
 def test_bearish_sweep_and_opposing_block_symmetry(self):
  sweep=((8,9,7,8),(8,10,8,9),(9,9.5,8,9),(9,10.5,8.8,9.5))
  block=((8,9,7,8.5),(9.5,10,8,8.5),(8.5,9.5,8,9),(9,11,8.9,10.5))
  for values,kind in ((sweep,MarketStructureKind.BULLISH_LIQUIDITY_SWEEP),(block,MarketStructureKind.BEARISH_ORDER_BLOCK)):
   out=self.analyze(self.rows(tuple((20-o,20-l,20-h,20-c) for o,h,l,c in values)))
   self.assertEqual(len(self.kinds(out,kind)),1)
 def test_context_validates_reference_clocks_and_price_evidence(self):
  event=self.kinds(self.analyze(),MarketStructureKind.BULLISH_BOS)[0]
  for bad in (replace(event,swing_reference=replace(event.swing_reference,available_at_ms=200000)),replace(event,trigger_reference=None),replace(event,level=float('nan')),replace(event,low=9),replace(event,source_available_at_ms=250000)):
   with self.assertRaises(ValueError):MarketStructureContext((bad,))
 def test_context_output_events_do_not_expose_internal_mutable_identity(self):
  ctx=MarketStructureContext(self.analyze());events=ctx.events;bos=self.kinds(events,MarketStructureKind.BULLISH_BOS)[0];object.__setattr__(bos,'kind',MarketStructureKind.BEARISH_BOS);object.__setattr__(bos.swing_reference,'available_at_ms',999999999)
  self.assertIs(ctx.bias_at(240000,MarketTimeframe.M1).direction,MarketDirection.BULLISH)
 def test_context_and_mtf_empty_inputs_remain_no_bias(self):
  self.assertEqual(build_multi_timeframe_structure({},as_of_ms=0),());self.assertEqual(self.analyze((),cutoff=0),());ctx=MarketStructureContext(())
  self.assertIsNone(ctx.bias_at(0,MarketTimeframe.H1));self.assertFalse(ctx.alignment_at(0,entry_timeframe=MarketTimeframe.M1,bias_timeframe=MarketTimeframe.H1,direction=MarketDirection.BULLISH).aligned)

 def test_all_explicit_timeframe_labels_accept_their_declared_duration(self):
  durations=(60000,180000,300000,900000,1800000,3600000,7200000,14400000,21600000,43200000,86400000)
  for tf,step in zip(tuple(MarketTimeframe),durations):
   event,=self.kinds(self.analyze(self.rows(step=step),cutoff=4*step,timeframe=tf),MarketStructureKind.BULLISH_BOS)
   self.assertEqual(event.timeframe,tf);self.assertEqual(event.available_at_ms,4*step)
 def test_mtf_mapping_order_has_no_effect_on_output(self):
  a={MarketTimeframe.M5:self.rows(step=300000),MarketTimeframe.H1:self.rows(step=3600000)}
  self.assertEqual(build_multi_timeframe_structure(a,as_of_ms=14400000,left=1,right=1),build_multi_timeframe_structure(dict(reversed(tuple(a.items()))),as_of_ms=14400000,left=1,right=1))
 def test_context_bounds_literal_container_and_decision_clock(self):
  class Events(list):
   def __iter__(self):raise AssertionError('FOREIGN_EVENTS')
  with self.assertRaises(ValueError):MarketStructureContext(Events())
  with self.assertRaises(ValueError):MarketStructureContext([self.analyze()[0]]*400001)
  ctx=MarketStructureContext(self.analyze())
  for clock in (True,None,-1,1.0,2**53):
   with self.assertRaises(ValueError):ctx.bias_at(clock,MarketTimeframe.M1)
 def test_exact_raw_source_archives_and_no_retirement_deduction(self):
  import ast,hashlib,json,pathlib
  p=pathlib.Path(__file__).resolve().parents[1]/'docs/provenance/market-structure-transfer';manifest=json.loads((p/'SOURCE.json').read_text());count=0
  for item in manifest['sources']:
   raw=(p/item['archive']).read_bytes();self.assertEqual(len(raw),item['bytes']);self.assertEqual(hashlib.sha256(raw).hexdigest(),item['sha256']);self.assertEqual(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),item['blob'])
   if item['path'].startswith('tests/'):
    count+=sum(isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name.startswith('test_') for n in ast.walk(ast.parse(raw)))
  self.assertEqual(count,7);self.assertEqual(manifest['remainingDeclaredLegacyTestFunctions'],516);self.assertEqual(manifest['legacyDeclaredTestFunctions'],547);self.assertEqual(manifest['deductedLegacyTestFunctions'],0);self.assertFalse(manifest['oldSourcesOrConsumersRemoved'])
 def test_ohlc_domain_refuses_numeric_objects_before_foreign_callbacks(self):
  from decimal import Decimal
  class Price:
   def __str__(self):raise AssertionError('FOREIGN_STR')
   def __float__(self):raise AssertionError('FOREIGN_FLOAT')
  for value in (Price(),Decimal('9')):
   with self.assertRaises(ValueError):self.analyze((OHLCObservation(0,60000,60000,8,value,7,8),))

 def test_same_event_identity_conflicting_price_evidence_refuses_in_both_orders(self):
  event=self.kinds(self.analyze(),MarketStructureKind.BULLISH_BOS)[0]
  for level in (9,11):
   conflict=replace(event,level=level,low=level,high=level)
   for events in ((event,conflict),(conflict,event)):
    with self.assertRaisesRegex(ValueError,'CONFLICTING_EVENT_IDENTITY'):MarketStructureContext(events)
 def test_future_conflicting_identity_refuses_before_any_projection(self):
  event=self.kinds(self.analyze(),MarketStructureKind.BULLISH_BOS)[0]
  future=replace(event,available_at_ms=600000,source_available_at_ms=600000,trigger_reference=replace(event.trigger_reference,available_at_ms=600000))
  conflict=replace(future,level=11,low=11,high=11)
  with self.assertRaisesRegex(ValueError,'CONFLICTING_EVENT_IDENTITY'):MarketStructureContext((future,conflict))
 def test_identical_duplicate_events_are_harmless_and_detached(self):
  events=self.analyze();copies=tuple(replace(e,swing_reference=replace(e.swing_reference),trigger_reference=None if e.trigger_reference is None else replace(e.trigger_reference)) for e in events)
  ctx=MarketStructureContext(events+copies);original=MarketStructureContext(events)
  self.assertEqual(len(ctx.events),len(original.events));self.assertEqual(ctx.bias_at(240000,MarketTimeframe.M1),original.bias_at(240000,MarketTimeframe.M1))
  object.__setattr__(copies[-1],'level',1);self.assertEqual(ctx.bias_at(240000,MarketTimeframe.M1),original.bias_at(240000,MarketTimeframe.M1))
 def test_same_identity_conflicting_reference_or_numeric_representation_refuses(self):
  event=self.kinds(self.analyze(),MarketStructureKind.BULLISH_BOS)[0]
  conflict=replace(event,swing_reference=replace(event.swing_reference,available_at_ms=179999))
  typed=replace(event,level=float(event.level),low=float(event.low),high=float(event.high))
  for bad in (conflict,typed):
   for events in ((event,bad),(bad,event)):
    with self.assertRaisesRegex(ValueError,'CONFLICTING_EVENT_IDENTITY'):MarketStructureContext(events)
 def test_same_identity_order_block_range_conflict_refuses(self):
  rows=self.rows(((8,9,7,8.5),(9.5,10,8,8.5),(8.5,9.5,8,9),(9,11,8.9,10.5)))
  event=self.kinds(self.analyze(rows),MarketStructureKind.BULLISH_ORDER_BLOCK)[0]
  for bad in (replace(event,low=7.5),replace(event,high=10.5)):
   with self.assertRaisesRegex(ValueError,'CONFLICTING_EVENT_IDENTITY'):MarketStructureContext((event,bad))

 def test_opposite_structural_events_at_one_trigger_preserve_high_then_low_state(self):
  values=((8,9,7,8),(9,10,8,9),(9,9,8,9),(13,15,12.5,13),(13,16,13,14),(13,17,12,13),(14,18,13,14),(11,19,10.5,11))
  events=self.analyze(self.rows(values,delays={0:400000}),cutoff=480000)
  structural=[e for e in events if e.kind in (MarketStructureKind.BULLISH_BOS,MarketStructureKind.BEARISH_BOS,MarketStructureKind.BULLISH_CHOCH,MarketStructureKind.BEARISH_CHOCH)]
  self.assertEqual({e.kind for e in structural},{MarketStructureKind.BULLISH_BOS,MarketStructureKind.BEARISH_CHOCH})
  self.assertEqual({(e.event_start_ms,e.available_at_ms) for e in structural},{(420000,480000)})
  for supplied in (events,tuple(reversed(events))):
   bias=MarketStructureContext(supplied).bias_at(480000,MarketTimeframe.M1)
   self.assertIs(bias.direction,MarketDirection.BEARISH);self.assertIs(bias.evidence.kind,MarketStructureKind.BEARISH_CHOCH)

 def test_same_side_bos_and_choch_classification_conflict_refuses_in_both_orders(self):
  event=self.kinds(self.analyze(),MarketStructureKind.BULLISH_BOS)[0]
  opposite_label=replace(event,kind=MarketStructureKind.BULLISH_CHOCH)
  for events in ((event,opposite_label),(opposite_label,event)):
   with self.assertRaisesRegex(ValueError,'CONFLICTING_SIDE_CLASSIFICATION'):MarketStructureContext(events)
  bearish=replace(event,kind=MarketStructureKind.BEARISH_BOS);bearish_label=replace(event,kind=MarketStructureKind.BEARISH_CHOCH)
  for events in ((bearish,bearish_label),(bearish_label,bearish)):
   with self.assertRaisesRegex(ValueError,'CONFLICTING_SIDE_CLASSIFICATION'):MarketStructureContext(events)
 def test_future_same_side_classification_conflict_is_not_filtered_out(self):
  event=self.kinds(self.analyze(),MarketStructureKind.BULLISH_BOS)[0]
  future=replace(event,available_at_ms=600000,source_available_at_ms=600000,trigger_reference=replace(event.trigger_reference,available_at_ms=600000))
  label=replace(future,kind=MarketStructureKind.BULLISH_CHOCH)
  for events in ((future,label),(label,future)):
   with self.assertRaisesRegex(ValueError,'CONFLICTING_SIDE_CLASSIFICATION'):MarketStructureContext(events)

 def test_later_event_clock_outranks_low_side_precedence_at_equal_known_time(self):
  values=((7,10,5,7),(7,12,4,7),(7,10,5,7),(7,13,6,12.5),(7,11,3,3.5))
  mirrored=tuple((20-o,20-l,20-h,20-c) for o,h,l,c in values)
  events=self.analyze(self.rows(mirrored,delays={3:300000}),cutoff=300000)
  for supplied in (events,tuple(reversed(events))):
   bias=MarketStructureContext(supplied).bias_at(300000,MarketTimeframe.M1)
   self.assertIs(bias.direction,MarketDirection.BULLISH);self.assertEqual(bias.evidence.event_start_ms,240000)

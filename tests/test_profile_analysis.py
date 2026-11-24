"""Pure synthetic analysis integration; clocks are declared, never attested."""
import unittest
from terminan.profile_analysis import analyze_trade_profile,analyze_candle_proxy_profile
from terminan.entry_context import ProfileSummary,ProfileKind,build_entry_context

class ProfileAnalysisTests(unittest.TestCase):
 def trades(self):
  return [{'event_ms':1,'available_at_ms':1,'price':100,'volume':2},{'event_ms':2,'available_at_ms':2,'price':101,'volume':1},{'event_ms':3,'available_at_ms':3,'price':100,'volume':3}]
 def test_original_trade_fixture_numeric_values_and_actual_clock(self):
  value=analyze_trade_profile(self.trades(),decision_ms=10)
  self.assertIs(type(value),ProfileSummary)
  self.assertEqual((value.poc,value.value_area_high,value.value_area_low,value.value_area_width),(100,100,100,0))
  self.assertIs(value.kind,ProfileKind.TRADE_DISTRIBUTION)
  self.assertEqual(value.available_at_ms,3)
 def test_original_candle_proxy_fixture_remains_explicitly_proxy(self):
  rows=[dict(event_start_ms=0,event_end_ms=60,available_at_ms=65,high=101,low=99,close=100,volume=5)]
  value=analyze_candle_proxy_profile(rows,decision_ms=100)
  self.assertEqual(value.poc,100)
  self.assertIs(value.kind,ProfileKind.CANDLE_PROXY)
  self.assertEqual(value.available_at_ms,65)
 def test_future_availability_never_replaced_with_event_time(self):
  rows=self.trades();before=analyze_trade_profile(rows,decision_ms=10)
  rows.append(dict(event_ms=4,available_at_ms=11,price=200,volume=100))
  self.assertEqual(analyze_trade_profile(rows,decision_ms=10),before)
 def test_candle_cannot_be_observed_before_explicit_end(self):
  rows=[dict(event_start_ms=0,event_end_ms=60000,available_at_ms=60000,high=101,low=99,close=100,volume=5)]
  with self.assertRaises(ValueError):analyze_candle_proxy_profile(rows,decision_ms=59999)
 def test_wide_representable_price_preserved_and_lossy_integer_refused(self):
  value=analyze_trade_profile([dict(event_ms=1,available_at_ms=1,price=2**54,volume=1)],decision_ms=1)
  self.assertIs(type(value.poc),int)
  self.assertEqual(value.poc,2**54)
  with self.assertRaises(ValueError):analyze_trade_profile([dict(event_ms=1,available_at_ms=1,price=2**53+1,volume=1)],decision_ms=1)
 def test_context_selection_uses_computed_declared_availability(self):
  value=analyze_trade_profile(self.trades(),decision_ms=10)
  self.assertIsNone(build_entry_context(decision_ms=2,metadata={},profiles=(value,))['profile'])
  selected=build_entry_context(decision_ms=3,metadata={},profiles=(value,))['profile']
  self.assertEqual(selected['poc'],100)
  self.assertEqual(selected['available_at_ms'],3)
 def test_projection_never_grants_authority(self):
  value=analyze_trade_profile(self.trades(),decision_ms=10)
  self.assertIs(value.execution_authority,False)
  self.assertIs(value.trading_authorized,False)
  self.assertEqual(value.source_authentication,'NOT_EVALUATED')
  self.assertEqual(value.availability_basis,'CALLER_DECLARED')
 def test_malformed_future_row_is_preflighted_before_selection(self):
  rows=self.trades()+[dict(event_ms=4,available_at_ms=11,price=float('nan'),volume=1)]
  with self.assertRaises(ValueError):analyze_trade_profile(rows,decision_ms=10)

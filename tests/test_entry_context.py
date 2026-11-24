
"""Canonical context projection roles; no simulation, storage or source grant."""
import dataclasses,importlib.util,unittest
from decimal import Decimal,localcontext
class EntryContextTests(unittest.TestCase):
 def api(self):
  self.assertIsNotNone(importlib.util.find_spec('terminan.entry_context'),'canonical entry-context API missing')
  from terminan import entry_context
  return entry_context
 def volatility(self,event,available,*,regime=None):
  from terminan.volatility import VolatilityMetrics,VolatilityRegime
  return VolatilityMetrics(event,available,.01,.01,.01,.02,1.,1.,.5,regime or VolatilityRegime.NORMAL,'v1')
 def profile(self,available,poc=100):
  m=self.api()
  return m.ProfileSummary(poc,102,98,available,m.ProfileKind.TRADE_DISTRIBUTION,4)
 def test_entry_context_uses_latest_snapshot_available_at_entry(self):
  """Original latest-known volatility AND profile cutoff, four assertions."""
  from terminan.volatility import VolatilityMetrics,VolatilityRegime
  m=self.api()
  vols=[
   VolatilityMetrics(0,60,.01,.01,.01,.02,1,1,.5,VolatilityRegime.NORMAL,'v1'),
   VolatilityMetrics(60,120,.02,.02,.02,.03,2,2,.9,VolatilityRegime.EXTREME,'v1'),
  ]
  profiles=[
   m.ProfileSummary(100,102,98,60,m.ProfileKind.TRADE_DISTRIBUTION,4),
   m.ProfileSummary(110,112,108,180,m.ProfileKind.TRADE_DISTRIBUTION,4),
  ]
  value=m.build_entry_context(decision_ms=120,metadata={},volatility=vols,profiles=profiles)
  self.assertEqual(value['volatility']['regime'],'EXTREME')
  self.assertEqual(value['volatility']['version'],'v1')
  self.assertEqual(value['profile']['poc'],100)
  self.assertEqual(value['profile']['kind'],'TRADE_DISTRIBUTION')
 def test_future_context_is_never_attached(self):
  """Original future exclusion AND unrelated metadata preservation."""
  from terminan.volatility import VolatilityMetrics,VolatilityRegime
  m=self.api()
  volatility=[VolatilityMetrics(60,180,.02,.02,.02,.03,2,2,.9,VolatilityRegime.EXTREME,'v1')]
  value=m.build_entry_context(decision_ms=120,metadata={'coverage':'COMPLETE_HISTORY'},volatility=volatility)
  self.assertIsNone(value['volatility'])
  self.assertEqual(value['metadata']['coverage'],'COMPLETE_HISTORY')
 def test_delayed_old_event_uses_explicit_availability_and_latest_order_not_input_position(self):
  m=self.api();old=self.volatility(0,180);new=self.volatility(60,120)
  value=m.build_entry_context(decision_ms=150,metadata={},volatility=[old,new])
  self.assertEqual(value['volatility']['event_start_ms'],60)
  value=m.build_entry_context(decision_ms=180,metadata={},volatility=[old,new])
  self.assertEqual(value['volatility']['event_start_ms'],0)
  self.assertEqual(value['volatility']['available_at_ms'],180)
 def test_frozen_summary_requires_explicit_clock_and_kind_no_legacy_alias(self):
  m=self.api();p=self.profile(60)
  with self.assertRaises(dataclasses.FrozenInstanceError):p.available_at_ms=10
  for bad in (None,True,-1,2**53,60.,'60'):
   with self.assertRaises(ValueError):m.ProfileSummary(100,102,98,bad,m.ProfileKind.TRADE_DISTRIBUTION,4)
  for bad in ('TRADE_POC','TRADE_DISTRIBUTION',None):
   with self.assertRaises(ValueError):m.ProfileSummary(100,102,98,60,bad,4)
  self.assertFalse(hasattr(m,'attach_entry_context'))
  self.assertFalse(hasattr(p,'known_at'))
 def test_summary_refuses_nonliteral_nonfinite_and_oversized_numbers(self):
  m=self.api()
  class I(int):pass
  class Equal(type):
   def __eq__(self,other):raise AssertionError('METACLASS_CALLBACK')
  class Bad(metaclass=Equal):pass
  for bad in (True,I(100),Bad(),Decimal('100'),float('nan'),float('inf'),-1.,2**53+1):
   with self.assertRaises(ValueError):m.ProfileSummary(bad,102,98,60,m.ProfileKind.TRADE_DISTRIBUTION,4)
 def test_all_inputs_preflight_bounded_and_invalid_future_refuses_whole_request(self):
  m=self.api()
  class BadList(list):
   def __iter__(self):raise AssertionError('ITERATED')
  for bad in (BadList(),[None]*513):
   with self.assertRaises(ValueError):m.build_entry_context(decision_ms=120,metadata={},volatility=bad)
  bad=self.volatility(60,180);object.__setattr__(bad,'atr_fraction',float('nan'))
  with self.assertRaises(ValueError):m.build_entry_context(decision_ms=120,metadata={},volatility=[self.volatility(0,60),bad])
 def test_profile_revalidated_at_projection_not_trusted_frozen_constructor(self):
  m=self.api();p=self.profile(60);object.__setattr__(p,'available_at_ms',None)
  with self.assertRaises(ValueError):m.build_entry_context(decision_ms=120,metadata={},profiles=[p])
 def test_metadata_is_bounded_literal_detached_and_cannot_grant_authority(self):
  m=self.api();meta={'tags':['a'],'coverage':'COMPLETE_HISTORY','execution_authority':True}
  value=m.build_entry_context(decision_ms=120,metadata=meta,profiles=[self.profile(60)])
  value['metadata']['tags'].append('b');self.assertEqual(meta['tags'],['a'])
  self.assertIs(value['execution_authority'],False);self.assertIs(value['trading_authorized'],False)
  self.assertEqual(value['source_authentication'],'NOT_EVALUATED')
  for bad in ({'x':'a'*1537},{str(i):i for i in range(33)},{'x':object()},{'x':1.2},{'x':2**53}):
   with self.assertRaises(ValueError):m.build_entry_context(decision_ms=120,metadata=bad)
 def test_no_arithmetic_or_old_shape_in_projection_and_decimal_context_unchanged(self):
  m=self.api()
  with localcontext() as context:
   context.prec=2
   for signal in context.traps:context.traps[signal]=True
   context.clear_flags();before=dict(context.flags)
   value=m.build_entry_context(decision_ms=120,metadata={},volatility=[self.volatility(0,60)],profiles=[self.profile(60)])
   self.assertEqual(context.flags,before)
  self.assertEqual(value['profile']['availability_basis'],'CALLER_DECLARED')
  self.assertEqual(value['volatility']['availability_basis'],'CALLER_DECLARED_PREFIX_MAX')
  for old in ('known_at','atr_pct','realized_vol','parkinson_vol','volume_expansion'):
   self.assertNotIn(old,value['volatility'])
 def test_clock_and_ambiguous_identity_refuse_before_projection(self):
  m=self.api()
  for bad in (True,-1,None,'120',120.,2**53):
   with self.assertRaises(ValueError):m.build_entry_context(decision_ms=bad,metadata={})
  first=self.volatility(0,60);second=dataclasses.replace(first,version='different')
  with self.assertRaises(ValueError):m.build_entry_context(decision_ms=120,metadata={},volatility=[first,second])
 def test_exact_same_duplicate_is_harmless_and_input_is_unchanged(self):
  m=self.api();v=self.volatility(0,60);rows=[v,v]
  a=m.build_entry_context(decision_ms=120,metadata={},volatility=rows)
  b=m.build_entry_context(decision_ms=120,metadata={},volatility=[v])
  self.assertEqual(a,b);self.assertEqual(rows,[v,v])

 def test_escaped_metadata_budget_refuses_before_encoder(self):
  from unittest.mock import patch
  m=self.api()
  for size in (256,1536):
   text='\x01'*size;metadata={'a':[text]*200,'b':[text]*200}
   with patch.object(m.json,'dumps',side_effect=AssertionError('ENCODER_CALLED_BEFORE_BUDGET')):
    with self.assertRaises(ValueError):m.build_entry_context(decision_ms=120,metadata=metadata)
 def test_metadata_exact_64k_and_one_byte_over_boundary(self):
  from unittest.mock import patch
  m=self.api();metadata={'a':['x'*1536]*42,'b':'x'*884}
  self.assertEqual(len(m.json.dumps(metadata,separators=(',',':'),ensure_ascii=True)),65536)
  self.assertEqual(m.build_entry_context(decision_ms=120,metadata=metadata)['metadata'],metadata)
  oversized={'a':['x'*1536]*42,'b':'x'*885}
  with patch.object(m.json,'dumps',side_effect=AssertionError('OVERSIZE_ENCODER_CALLED')):
   with self.assertRaises(ValueError):m.build_entry_context(decision_ms=120,metadata=oversized)
 def test_ascii_escape_size_matches_encoder_and_preserves_valid_unicode_metadata(self):
  import terminan.bounded_json as codec
  self.assertTrue(hasattr(codec,'ascii_json_string_size'),'pre-encoder ASCII budget helper missing')
  m=self.api()
  for text in ('abc','"','\\','\b\f\n\r\t','\x00\x01','é','😀','\ud800','\x7f','/'):
   encoded=m.json.dumps(text,ensure_ascii=True,separators=(',',':'))
   self.assertEqual(codec.ascii_json_string_size(text,max_bytes=65536),len(encoded))
   self.assertEqual(m.build_entry_context(decision_ms=120,metadata={'tag':text})['metadata']['tag'],text)
   with self.assertRaises(ValueError):codec.ascii_json_string_size(text,max_bytes=len(encoded)-1)
 def test_market_metric_lossless_domain_is_math_owned_not_metadata_clock_budget(self):
  m=self.api()
  for value in (2**53,2**54,2**1023):
   summary=m.ProfileSummary(value,value,value,60,m.ProfileKind.TRADE_DISTRIBUTION,0)
   self.assertIs(type(summary.poc),int)
   self.assertEqual(summary.poc,value)
  for metadata in ({'x':2**53},{'x':2**54}):
   with self.assertRaises(ValueError):m.build_entry_context(decision_ms=60,metadata=metadata)
  with self.assertRaises(ValueError):m.ProfileSummary(100,102,98,2**53,m.ProfileKind.TRADE_DISTRIBUTION,4)

import unittest
class StrategyCatalogTests(unittest.TestCase):
 def catalog(self):
  from terminan.strategy_catalog import research_strategy_catalog
  return research_strategy_catalog()
 def test_eight_unique_named_definitions(self):
  rows=self.catalog();self.assertIs(type(rows),tuple);self.assertEqual(len(rows),8)
  self.assertEqual(len({x.id for x in rows}),8)
  for row in rows:self.assertRegex(row.id,r'^[a-z][a-z0-9_]+$');self.assertEqual(row.version,'2' if row.generator is not None else '1')
 def test_only_four_have_research_generators(self):
  from terminan.strategy_catalog import StrategyAvailability
  rows=self.catalog();available={x.id for x in rows if x.availability is StrategyAvailability.RESEARCH_GENERATOR}
  self.assertEqual(available,{'sweep_reclaim_v2','breakout_retest_v2','volatility_continuation_v2','profile_reclaim_v2'})
  for row in rows:self.assertEqual(row.generator is not None,row.availability is StrategyAvailability.RESEARCH_GENERATOR)
 def test_exact_canonical_callables_and_output_contracts(self):
  from terminan.strategy_entries import generate_sweep_reclaim_entries,generate_breakout_retest_entries,generate_profile_reclaim_entries
  from terminan.continuation_strategy import generate_continuation_entries
  from terminan.strategy_catalog import ResearchOutput
  expected={'sweep_reclaim_v2':generate_sweep_reclaim_entries,'breakout_retest_v2':generate_breakout_retest_entries,'profile_reclaim_v2':generate_profile_reclaim_entries,'volatility_continuation_v2':generate_continuation_entries}
  for row in self.catalog():
   self.assertIs(row.generator,expected.get(row.id))
   if row.generator is not None:self.assertIs(row.output,ResearchOutput.ENTRIES)
 def test_no_definition_is_execution_authority(self):
  for row in self.catalog():self.assertIs(row.execution_authority,False);self.assertIs(row.trading_authorized,False);self.assertEqual(row.source_authentication,'NOT_EVALUATED')
 def test_unsupported_specs_retain_distinct_research_requirements(self):
  rows={row.id:row for row in self.catalog()}
  self.assertEqual(rows['level_impulse'].required_features,('level','volatility','volume_expansion'))
  self.assertEqual(rows['level_impulse_delta'].confirmations,('volume_expansion','delta'))
  self.assertEqual(rows['failed_breakout'].direction,'reversal')
  self.assertEqual(rows['open_interest_delta_impulse'].confirmations,('open_interest','delta','volume_expansion'))
 def test_definitions_are_detached_and_frozen(self):
  from dataclasses import FrozenInstanceError
  a=self.catalog();b=self.catalog();self.assertIsNot(a[0],b[0])
  with self.assertRaises(FrozenInstanceError):a[0].id='changed'
  object.__setattr__(a[0],'id','changed');self.assertEqual(self.catalog()[0].id,b[0].id)
 def test_resolver_is_closed_and_has_no_dynamic_imports(self):
  from terminan.strategy_catalog import research_strategy
  self.assertEqual(research_strategy('sweep_reclaim_v2').id,'sweep_reclaim_v2')
  for value in ('SCALP_SWEEP_RECLAIM','strattester.research.scalp_entries:sweep_reclaim_entries','missing','',None,True,1):
   with self.assertRaises(ValueError):research_strategy(value)
 def test_resolver_rejects_foreign_string_without_callbacks(self):
  from terminan.strategy_catalog import research_strategy
  class Hostile(str):
   def __hash__(self):raise AssertionError('hash callback')
   def __eq__(self,other):raise AssertionError('eq callback')
  with self.assertRaises(ValueError):research_strategy(Hostile('sweep_reclaim_v2'))
 def test_catalog_discovery_never_calls_a_generator(self):
  import terminan.strategy_catalog as catalog
  old=catalog.generate_sweep_reclaim_entries
  def refused(*args,**kwargs):raise AssertionError('generator ran during discovery')
  catalog.generate_sweep_reclaim_entries=refused
  try:self.assertEqual(len(catalog.research_strategy_catalog()),8)
  finally:catalog.generate_sweep_reclaim_entries=old

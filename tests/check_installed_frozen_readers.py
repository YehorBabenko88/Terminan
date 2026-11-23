"""Installed frozen-reader, volatility, entry-context and profile and continuation regressions; no admission authority."""
import os,pathlib,runpy,sys,unittest,hashlib,importlib.util,stat
if not(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):raise RuntimeError('ISOLATED_NO_SITE_NO_WRITE_REQUIRED')
site=pathlib.Path(os.environ['TERMINAN_COHORT_PATH']).resolve(strict=True)
checkout=pathlib.Path(__file__).resolve().parents[1]
def owned(name):return name=='terminan' or name.startswith('terminan.') or name=='market_data' or name.startswith('market_data.') or name in ('market_math','market_compute_api','history_statistics')
if any(owned(name) for name in sys.modules):raise RuntimeError('PRELOADED_SDK_REJECTED')
if sys.pycache_prefix is None:raise RuntimeError('FRESH_EXTERNAL_CACHE_REQUIRED')
cache=pathlib.Path(sys.pycache_prefix)
if not cache.is_absolute() or '..' in cache.parts or cache.resolve().is_relative_to(site) or cache.resolve().is_relative_to(checkout):raise RuntimeError('FRESH_EXTERNAL_CACHE_REQUIRED')
for parent in reversed(cache.parents):
 info=parent.lstat()
 if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&1024:raise RuntimeError('ORDINARY_CACHE_PARENT_REQUIRED')
cache.mkdir();cache_identity=(cache.stat().st_dev,cache.stat().st_ino)
def unchanged_cache():
 info=cache.lstat()
 if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&1024 or (info.st_dev,info.st_ino)!=cache_identity or any(cache.iterdir()):raise RuntimeError('CACHE_CHANGED')
def bytes_snapshot():
 paths=list((site/'terminan').rglob('*'))+list((site/'market_data').rglob('*'))+[site/name for name in ('market_math.py','market_compute_api.py','history_statistics.py')]
 out={}
 for path in paths:
  info=path.lstat()
  if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&1024:raise RuntimeError('SDK_LINK_REJECTED')
  if stat.S_ISREG(info.st_mode):out[str(path.relative_to(site))]=hashlib.sha256(path.read_bytes()).hexdigest()
 return out
before=bytes_snapshot();unchanged_cache();sys.path.insert(0,str(site))
import terminan.data,terminan.migration.candle_snapshot,terminan.migration.research_results
case=runpy.run_path(str(pathlib.Path(__file__).with_name('test_frozen_readers.py')))['FrozenReaderTests']
suite=unittest.defaultTestLoader.loadTestsFromTestCase(case)
volatility=runpy.run_path(str(pathlib.Path(__file__).with_name('test_volatility.py')))
for name in ('VolatilityTransferTests','CanonicalVolatilityBoundaryTests'):
 suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(volatility[name]))
entry_context=runpy.run_path(str(pathlib.Path(__file__).with_name('test_entry_context.py')))
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(entry_context['EntryContextTests']))
profile_analysis=runpy.run_path(str(pathlib.Path(__file__).with_name('test_profile_analysis.py')))
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(profile_analysis['ProfileAnalysisTests']))
continuation=runpy.run_path(str(pathlib.Path(__file__).with_name('test_continuation_strategy.py')))
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(continuation['ContinuationStrategyTests']))
price_structure=runpy.run_path(str(pathlib.Path(__file__).with_name('test_price_structure.py')))
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(price_structure['PriceStructureTests']))
market_structure=runpy.run_path(str(pathlib.Path(__file__).with_name('test_market_structure.py')))
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(market_structure['MarketStructureTests']))
strategy_entries=runpy.run_path(str(pathlib.Path(__file__).with_name('test_strategy_entries.py')))
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(strategy_entries['StrategyEntryTests']))
strategy_catalog=runpy.run_path(str(pathlib.Path(__file__).with_name('test_strategy_catalog.py')))
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(strategy_catalog['StrategyCatalogTests']))
screening=runpy.run_path(str(pathlib.Path(__file__).with_name('test_strategy_screening.py')))
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(screening['ResearchScreeningTests']))
signal_literal=runpy.run_path(str(pathlib.Path(__file__).with_name('test_signal_literal_boundary.py')))
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(signal_literal['SignalLiteralBoundaryTests']))
sys.path.append(str(checkout/'tests'))
evaluation=runpy.run_path(str(pathlib.Path(__file__).with_name('test_research_evaluation.py')))
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(evaluation['ResearchEvaluationTests']))
evaluation_boundaries=runpy.run_path(str(pathlib.Path(__file__).with_name('test_research_evaluation_boundaries.py')))
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(evaluation_boundaries['EvaluationBoundaryTests']))
history_v12=runpy.run_path(str(pathlib.Path(__file__).with_name('test_history_protocol_v12.py')))
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(history_v12['HistoryV12Tests']))
rich_v2=runpy.run_path(str(pathlib.Path(__file__).with_name('test_rich_entry_transfer.py')))
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(rich_v2['RichEntryTransferTests']))
def _case_ids(value):
 for test in value:
  if isinstance(test,unittest.TestSuite):yield from _case_ids(test)
  else:yield test.id()
case_ids=tuple(_case_ids(suite))
if suite.countTestCases()!=276 or len(case_ids)!=276 or len(set(case_ids))!=276:raise RuntimeError('EXACT_UNIQUE_ROSTER_REQUIRED')
result=unittest.TextTestRunner(verbosity=2).run(suite)
for name,module in tuple(sys.modules.items()):
 if not owned(name):continue
 source=pathlib.Path(module.__file__).resolve(strict=True)
 if not source.is_relative_to(site) or source.suffix!='.py' or str(source.relative_to(site)) not in before:raise RuntimeError('INSTALLED_ORIGIN_REQUIRED')
 expected=pathlib.Path(importlib.util.cache_from_source(str(source)))
 if pathlib.Path(module.__cached__)!=expected or not expected.is_relative_to(cache):raise RuntimeError('CACHED_ORIGIN_REJECTED')
unchanged_cache()
if bytes_snapshot()!=before:raise RuntimeError('SDK_BYTES_CHANGED')
raise SystemExit(not(result.wasSuccessful() and result.testsRun==276 and not result.skipped and not result.expectedFailures and not result.unexpectedSuccesses))

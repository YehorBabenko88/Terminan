"""Actual installed frozen-reader regression suite; no source-package fallback."""
import os,pathlib,runpy,sys,unittest
if not sys.flags.isolated:raise RuntimeError('ISOLATED_REQUIRED')
site=pathlib.Path(os.environ['TERMINAN_COHORT_PATH']).resolve(strict=True)
sys.path.insert(0,str(site))
import terminan.data,terminan.migration.candle_snapshot,terminan.migration.research_results
for module in (terminan.data,terminan.migration.candle_snapshot,terminan.migration.research_results):
 if not pathlib.Path(module.__file__).resolve(strict=True).is_relative_to(site):raise RuntimeError('INSTALLED_ORIGIN_REQUIRED')
case=runpy.run_path(str(pathlib.Path(__file__).with_name('test_frozen_readers.py')))['FrozenReaderTests']
suite=unittest.defaultTestLoader.loadTestsFromTestCase(case)
if suite.countTestCases()!=8:raise RuntimeError('EXACT_ROSTER_REQUIRED')
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not(result.wasSuccessful() and result.testsRun==8 and not result.skipped and not result.expectedFailures and not result.unexpectedSuccesses))

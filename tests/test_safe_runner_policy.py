import os, runpy, sys, types, unittest
from pathlib import Path
from unittest.mock import patch

class SafeRunnerPolicyTests(unittest.TestCase):
    def test_explicit_asyncio_plugin_has_no_automatic_duplicate_registration(self):
        seen = []
        fake = types.ModuleType('pytest')
        def main(args):
            if os.environ.get('PYTEST_DISABLE_PLUGIN_AUTOLOAD') != '1':
                raise ValueError('Plugin already registered under a different name: asyncio')
            seen.append(args)
            return 0
        fake.main = main
        with patch.dict(sys.modules, {'pytest': fake}), patch.dict(os.environ):
            os.environ.pop('PYTEST_DISABLE_PLUGIN_AUTOLOAD', None)
            with self.assertRaises(SystemExit) as stopped:
                runpy.run_path(str(Path(__file__).with_name('run_safe_tests.py')), run_name='__main__')
        self.assertEqual(stopped.exception.code, 0)
        self.assertEqual(seen, [['-q', 'tests', '-p', 'pytest_asyncio.plugin']])

if __name__ == '__main__':
    unittest.main()

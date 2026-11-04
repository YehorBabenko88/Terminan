"""Keep process sampling from starving routed browser session requests."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class R4SamplerAsyncTests(unittest.TestCase):
    def test_sampler_keeps_driver_responsive_and_fails_closed(self):
        result = subprocess.run(['node', str(ROOT / 'tests/check_r4_sampler_async.cjs')],
                                cwd=ROOT, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()

"""Prevent PR/push collisions without removing either event's qualification."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ('cache-audit.yml', 'history-overlay.yml', 'math-lab.yml',
             'tests.yml', 'unified-runtime.yml', 'visual-qa.yml')


class WorkflowSchedulingTests(unittest.TestCase):
    def test_same_source_push_and_pull_request_have_independent_groups(self):
        sha = 'a' * 40
        for name in WORKFLOWS:
            text = (ROOT / '.github/workflows' / name).read_text()
            with self.subTest(workflow=name):
                group = re.search(r'^  group: (.+)$', text, re.M).group(1)
                def evaluate(event, source):
                    return group.replace('${{ github.event_name }}', event).replace(
                        '${{ github.event.pull_request.head.sha || github.sha }}', source)
                self.assertNotEqual(evaluate('push', sha), evaluate('pull_request', sha))
                self.assertEqual(evaluate('push', sha), evaluate('push', sha))
                self.assertNotEqual(evaluate('push', sha), evaluate('push', 'b' * 40))
                self.assertIn('cancel-in-progress: true', text)
                self.assertIn('on: [push, pull_request]', text)

    def test_cache_windows_corpus_has_a_larger_bounded_job_budget(self):
        text = (ROOT / '.github/workflows/cache-audit.yml').read_text()
        budget = re.search(r'^    timeout-minutes: (.+)$', text, re.M).group(1)
        self.assertEqual(budget, "${{ matrix.os == 'windows-latest' && 30 || 10 }}")
        self.assertIn('os: [ubuntu-latest, windows-latest]', text)
        self.assertIn('Invoke-CacheAudit.ps1 -ExpectedSha $sha', text)
        self.assertIn('python scripts/audit_cache.py --sha $sha', text)


if __name__ == '__main__':
    unittest.main()

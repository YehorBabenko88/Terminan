import unittest
from terminan.research_compare import compare_runs


class CoverageComparisonTests(unittest.TestCase):
    def record(self, coverage):
        return {"dataset": {"fingerprint": "same", "coverage": coverage},
                "strategy": "s", "version": "v1", "metrics": {}}

    def test_mismatched_coverage_blocks(self):
        result = compare_runs(self.record("2025"), self.record("2026"))
        self.assertEqual(result["state"], "BLOCKED")
        self.assertEqual(result["reason"], "COVERAGE_MISMATCH")
        self.assertEqual(result["coverage_comparison"], "MISMATCH")

    def test_missing_coverage_is_not_verified(self):
        result = compare_runs(self.record("UNSPECIFIED"), self.record("2026"))
        self.assertEqual(result["state"], "CONDITIONAL")
        self.assertEqual(result["coverage_comparison"], "UNVERIFIED")

    def test_matching_coverage_still_conditional(self):
        result = compare_runs(self.record("2026"), self.record("2026"))
        self.assertEqual(result["coverage_comparison"], "RECORDED_MATCH")
        self.assertEqual(result["state"], "CONDITIONAL")
        self.assertEqual(result["trading_authority"], "NONE")


if __name__ == "__main__":
    unittest.main()

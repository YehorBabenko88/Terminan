import unittest
from terminan.research_compare import compare_runs


class ResearchCompareTests(unittest.TestCase):
    def run_record(self, fingerprint=None, strategy="s", version="v1"):
        return {"dataset": {"fingerprint": fingerprint}, "strategy": strategy, "version": version}

    def test_missing_fingerprint_blocks(self):
        result = compare_runs(self.run_record(), self.run_record("abc"))
        self.assertEqual(result["state"], "BLOCKED")
        self.assertEqual(result["reason"], "DATASET_IDENTITY_MISSING")

    def test_different_fingerprints_block(self):
        result = compare_runs(self.run_record("a"), self.run_record("b"))
        self.assertEqual(result["reason"], "DATASET_MISMATCH")

    def test_identical_fingerprint_still_not_approved(self):
        result = compare_runs(self.run_record("abc"), self.run_record("abc", version="v2"))
        self.assertEqual(result["state"], "CONDITIONAL")
        self.assertFalse(result["same_strategy_version"])
        self.assertEqual(result["execution_assumptions"], "UNVERIFIED")
        self.assertEqual(result["statistical_significance"], "NOT_EVALUATED")
        self.assertEqual(result["trading_authority"], "NONE")


if __name__ == "__main__":
    unittest.main()

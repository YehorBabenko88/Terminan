import unittest
from terminan.research_compare import compare_runs


class ExecutionAssumptionComparisonTests(unittest.TestCase):
    def run_record(self, **settings):
        return {"dataset": {"fingerprint": "same"}, "strategy": "s",
                "version": "v1", "metrics": settings}

    def test_fee_mismatch_blocks(self):
        result = compare_runs(self.run_record(fee_rate=0.001),
                              self.run_record(fee_rate=0.002))
        self.assertEqual(result["state"], "BLOCKED")
        self.assertEqual(result["reason"], "EXECUTION_ASSUMPTIONS_MISMATCH")
        self.assertEqual(result["assumption_details"]["fee_rate"], "MISMATCH")

    def test_slippage_mismatch_blocks(self):
        result = compare_runs(self.run_record(slippage_bps=2),
                              self.run_record(slippage_bps=3))
        self.assertEqual(result["state"], "BLOCKED")

    def test_missing_settings_never_claim_verified(self):
        result = compare_runs(self.run_record(), self.run_record())
        self.assertEqual(result["state"], "CONDITIONAL")
        self.assertEqual(result["assumption_details"]["execution_model"], "UNVERIFIED")
        self.assertEqual(result["execution_assumptions"], "UNVERIFIED")

    def test_matching_recorded_settings_still_conditional(self):
        settings = dict(fee_rate=0.001, slippage_bps=2,
                        execution_model="limit", simulation_config_hash="abc")
        result = compare_runs(self.run_record(**settings), self.run_record(**settings))
        self.assertEqual(result["state"], "CONDITIONAL")
        self.assertTrue(all(value == "RECORDED_MATCH"
                            for value in result["assumption_details"].values()))
        self.assertEqual(result["trading_authority"], "NONE")


if __name__ == "__main__":
    unittest.main()

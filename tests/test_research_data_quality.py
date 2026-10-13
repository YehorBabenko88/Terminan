import unittest
from terminan.research_compare import compare_runs


class DataQualityGateTests(unittest.TestCase):
    def record(self, **metrics):
        return {"dataset": {"fingerprint": "same", "coverage": "2026"},
                "strategy": "s", "version": "v1", "metrics": metrics}

    def test_recorded_gap_blocks(self):
        result = compare_runs(self.record(data_gap_count=1), self.record(data_gap_count=0))
        self.assertEqual(result["state"], "BLOCKED")
        self.assertEqual(result["reason"], "DATA_QUALITY_DEFECT_RECORDED")
        self.assertEqual(result["data_quality"]["data_gap_count"], "DEFECT_RECORDED")

    def test_unknown_quality_not_passed(self):
        result = compare_runs(self.record(), self.record())
        self.assertEqual(result["state"], "CONDITIONAL")
        self.assertEqual(result["data_quality"]["missing_candles"], "UNVERIFIED")

    def test_zero_recorded_not_validated(self):
        metrics = dict(missing_candles=0, data_gap_count=0, invalid_candle_count=0)
        result = compare_runs(self.record(**metrics), self.record(**metrics))
        self.assertEqual(result["state"], "CONDITIONAL")
        self.assertEqual(result["data_quality"]["data_gap_count"], "ZERO_RECORDED_NOT_VALIDATED")
        self.assertEqual(result["trading_authority"], "NONE")

    def test_invalid_quality_values_not_trusted(self):
        result = compare_runs(self.record(data_gap_count=-1), self.record(data_gap_count=True))
        self.assertEqual(result["data_quality"]["data_gap_count"], "UNVERIFIED")


if __name__ == "__main__":
    unittest.main()

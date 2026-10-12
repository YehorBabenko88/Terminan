import unittest
from unittest.mock import patch
from terminan.source_views import strattester_research_view


class DatasetIdentityTests(unittest.TestCase):
    @patch("terminan.data.results_available", return_value=True)
    @patch("terminan.data.research")
    def test_fingerprint_and_coverage_exposed_without_promotion(self, read, _):
        read.return_value = [
            {"run_id": "a", "metrics": {"fingerprint": "abc", "coverage": "COMPLETE_HISTORY"}},
            {"run_id": "b", "metrics": {"net_pnl": 10}},
        ]
        result = strattester_research_view("BTCUSDT")["runs"]
        self.assertEqual(result[0]["dataset"]["fingerprint"], "abc")
        self.assertEqual(result[0]["dataset"]["coverage"], "COMPLETE_HISTORY")
        self.assertEqual(result[0]["dataset"]["comparability"], "IDENTIFIED")
        self.assertEqual(result[0]["validation"]["live_validation"], "NOT_VERIFIED")
        self.assertIsNone(result[1]["dataset"]["fingerprint"])
        self.assertEqual(result[1]["dataset"]["comparability"], "UNVERIFIED")
        self.assertEqual(result[1]["dataset"]["coverage"], "UNSPECIFIED")


if __name__ == "__main__":
    unittest.main()

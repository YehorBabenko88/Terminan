import unittest
from unittest.mock import patch
from terminan.source_views import strattester_comparison_view


class ResearchComparisonViewTests(unittest.TestCase):
    @patch("terminan.data.results_available", return_value=True)
    @patch("terminan.data.research")
    def test_same_dataset_only_conditional(self, read, _):
        read.return_value = [
            {"run_id": "a", "strategy": "s", "version": "v1", "metrics": {"fingerprint": "dataset"}},
            {"run_id": "b", "strategy": "s", "version": "v2", "metrics": {"fingerprint": "dataset"}},
        ]
        result = strattester_comparison_view("BTCUSDT", "a", "b")
        self.assertEqual(result["comparison"]["state"], "CONDITIONAL")
        self.assertEqual(result["comparison"]["trading_authority"], "NONE")

    @patch("terminan.data.results_available", return_value=True)
    @patch("terminan.data.research", return_value=[])
    def test_missing_runs_are_not_fabricated(self, *_):
        self.assertEqual(strattester_comparison_view("BTCUSDT", "a", "b")["state"], "RUN_NOT_FOUND")

    def test_duplicate_runs_rejected(self):
        with self.assertRaises(ValueError):
            strattester_comparison_view("BTCUSDT", "a", "a")


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import patch
from terminan.source_views import strattester_research_view


class ResearchValidationGatesTests(unittest.TestCase):
    @patch("terminan.data.results_available", return_value=True)
    @patch("terminan.data.research")
    def test_historical_result_does_not_grant_live_or_simulation_status(self, read, available):
        original = {"run_id": "r1", "metrics": {"net_pnl": 1000}, "fencing": {"state": "PRESENT_UNVERIFIED"}}
        read.return_value = [original]
        view = strattester_research_view("BTCUSDT")
        row = view["runs"][0]
        self.assertEqual(row["validation"]["live_validation"], "NOT_VERIFIED")
        self.assertEqual(row["validation"]["simulation_pass"], "NOT_VERIFIED")
        self.assertEqual(row["validation"]["trading_authority"], "NONE")
        self.assertEqual(row["validation"]["publication_authority"], "UNVERIFIED")
        self.assertNotIn("validation", original)

    @patch("terminan.data.results_available", return_value=True)
    @patch("terminan.data.research", return_value=[])
    def test_empty_research_has_no_fake_results(self, *_):
        view = strattester_research_view("BTCUSDT")
        self.assertEqual(view["state"], "EMPTY")
        self.assertEqual(view["runs"], [])


if __name__ == "__main__":
    unittest.main()

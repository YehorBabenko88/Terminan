import unittest
from unittest.mock import patch
from terminan.source_views import grid_market_view, strattester_research_view


class SourceViewTests(unittest.TestCase):
    @patch("terminan.data.grid_available", return_value=False)
    def test_grid_unconfigured_is_explicit(self, _):
        result = grid_market_view("BTCUSDT")
        self.assertEqual(result["state"], "NOT_CONFIGURED")
        self.assertEqual(result["l2"]["state"], "UNAVAILABLE")

    @patch("terminan.data.grid_available", return_value=True)
    @patch("terminan.data.grid_candles", return_value=[{"t": 1, "o": 1}])
    @patch("terminan.data.footprint", return_value=[{"t": 1, "price": 1}])
    def test_aggregates_never_become_l2(self, *mocks):
        result = grid_market_view("BTCUSDT")
        self.assertEqual(result["state"], "HISTORICAL_AGGREGATES")
        self.assertEqual(result["l2"]["state"], "UNAVAILABLE")
        self.assertEqual(len(result["footprint"]), 1)

    @patch("terminan.data.results_available", return_value=False)
    def test_results_unconfigured(self, _):
        self.assertEqual(strattester_research_view("BTCUSDT")["state"], "NOT_CONFIGURED")

    @patch("terminan.data.results_available", return_value=True)
    @patch("terminan.data.research", return_value=[{"run_id": "run-1"}])
    def test_research_provenance(self, *mocks):
        result = strattester_research_view("BTCUSDT")
        self.assertEqual(result["source"], "strattester")
        self.assertEqual(result["runs"][0]["run_id"], "run-1")

    def test_rejects_unbounded(self):
        with self.assertRaises(ValueError):
            grid_market_view("BTCUSDT", 100000)
        with self.assertRaises(ValueError):
            strattester_research_view("BTCUSDT", 100000)

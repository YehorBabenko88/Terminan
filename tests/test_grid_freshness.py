import unittest
from unittest.mock import patch
from terminan.source_views import grid_market_view


class GridFreshnessTests(unittest.TestCase):
    @patch("terminan.data.grid_available", return_value=True)
    @patch("terminan.data.grid_candles", return_value=[{"t": 100000, "o": 1}])
    @patch("terminan.data.footprint", return_value=[{"t": 100000, "price": 1}])
    def test_stale_minute_aggregates_never_become_l2(self, *_):
        result = grid_market_view("BTCUSDT", now_ms=500000)
        self.assertEqual(result["freshness"]["candles"]["state"], "STALE")
        self.assertEqual(result["freshness"]["footprint"]["latest_ms"], 100000)
        self.assertEqual(result["l2"]["state"], "UNAVAILABLE")

    @patch("terminan.data.grid_available", return_value=True)
    @patch("terminan.data.grid_candles", return_value=[{"t": 999999, "o": 1}])
    @patch("terminan.data.footprint", return_value=[])
    def test_future_timestamp_is_explicit(self, *_):
        result = grid_market_view("BTCUSDT", now_ms=100000)
        self.assertEqual(result["freshness"]["candles"]["state"], "FUTURE_TIMESTAMP")
        self.assertEqual(result["freshness"]["footprint"]["state"], "NO_DATA")

    def test_bad_limits_rejected(self):
        with self.assertRaises(ValueError):
            grid_market_view("BTCUSDT", candle_limit=True)
        with self.assertRaises(ValueError):
            grid_market_view("BTCUSDT", now_ms=-1)


if __name__ == "__main__":
    unittest.main()

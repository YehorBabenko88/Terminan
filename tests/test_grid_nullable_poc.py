import unittest
from unittest.mock import patch
from terminan.data import grid_candles


class NullableGridTests(unittest.TestCase):
    @patch("terminan.data.grid_query")
    def test_nullable_poc_does_not_hide_candle(self, query):
        query.return_value = [(1234, 1, 2, 0.5, 1.5, 10, 8, 2, 5, None)]
        result = grid_candles("BTCUSDT")
        self.assertEqual(result[0]["t"], 1234.0)
        self.assertIsNone(result[0]["poc"])
        self.assertEqual(result[0]["delta"], 2.0)


if __name__ == "__main__":
    unittest.main()

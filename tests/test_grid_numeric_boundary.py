"""Source adapter numeric boundaries: no external database connections."""
import unittest
from unittest.mock import patch
from terminan import data


class GridAdapterNumbers(unittest.TestCase):
    def test_candle_timestamp_is_integer_ms(self):
        row = (1000, 1, 2, 1, 2, 3, 4, 1, 5, 2)
        with patch.object(data, "grid_query", return_value=[row]):
            self.assertEqual(data.grid_candles("BTCUSDT")[0]["t"], 1000)

    def test_reject_nonfinite_and_partial(self):
        row = [1000, 1, 2, 1, 2, 3, 4, 1, 5, 2]
        for bad in (float("nan"), float("inf"), None, True):
            with self.subTest(value=str(bad)):
                broken = row.copy()
                broken[2] = bad
                with patch.object(data, "grid_query", return_value=[broken]):
                    with self.assertRaises(ValueError):
                        data.grid_candles("BTCUSDT")

    def test_reject_fractional_timestamp(self):
        with patch.object(data, "grid_query", return_value=[(1000.5, 1, 2, 3, 4, 5)]):
            with self.assertRaises(ValueError):
                data.footprint("BTCUSDT")

    def test_footprint_is_not_l2(self):
        with patch.object(data, "grid_query", return_value=[(1000, 1, 2, 3, 4, 5)]):
            self.assertEqual(data.footprint("BTCUSDT")[0]["t"], 1000)


if __name__ == "__main__":
    unittest.main()

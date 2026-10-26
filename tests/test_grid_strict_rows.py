"""Additional strict Grid adapter source regression tests; no PostgreSQL required."""
import unittest
from decimal import Decimal
from unittest.mock import patch
from terminan import data


class StrictGridRows(unittest.TestCase):
    def test_exact_milliseconds(self):
        self.assertEqual(data._grid_number(Decimal("1700000000001"), timestamp=True), 1700000000001)
        self.assertEqual(data._grid_number("1700000000001", timestamp=True), 1700000000001)

    def test_precision_and_fraction_rejection(self):
        for value in (Decimal("1700000000001.01"), "9007199254740993", "NaN",
                      "Infinity", "", True, None, -1):
            with self.subTest(value=str(value)):
                with self.assertRaises(ValueError):
                    data._grid_number(value, timestamp=True)

    def test_grid_row_arity(self):
        for row in ((1000, 1, 2), (1000, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10), None):
            with self.subTest(row=str(row)):
                with patch.object(data, "grid_query", return_value=[row]):
                    with self.assertRaises(ValueError):
                        data.grid_candles("BTCUSDT")

    def test_footprint_arity(self):
        with patch.object(data, "grid_query", return_value=[(1000, 1, 2)]):
            with self.assertRaises(ValueError):
                data.footprint("BTCUSDT")


if __name__ == "__main__":
    unittest.main()

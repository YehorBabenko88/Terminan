import unittest

from terminan.contracts import TradeEvent


BASE = dict(run_id="r", strategy_id="s", symbol="BTCUSDT", trade_id="t",
            entry_ms=100, exit_ms=200, entry_price=10, exit_price=12,
            side="long", quantity=2, pnl=4)


class NumericTradeContractTests(unittest.TestCase):
    def test_nonfinite_and_unrepresentable_trade_numbers_are_rejected(self):
        for field in ("entry_price", "exit_price", "quantity", "pnl"):
            for value in (float("nan"), float("inf"), float("-inf"), 10**400,
                          True, "12"):
                with self.subTest(field=field, value=str(value)):
                    with self.assertRaises(ValueError):
                        TradeEvent.parse({**BASE, field: value})

    def test_timestamps_are_nonnegative_bounded_integer_milliseconds(self):
        for field in ("entry_ms", "exit_ms"):
            for value in (True, 100.5, "200", float("nan"), float("inf"),
                          2**63, -1):
                with self.subTest(field=field, value=str(value)):
                    with self.assertRaises(ValueError):
                        TradeEvent.parse({**BASE, field: value})

    def test_closed_trade_requires_positive_exit_price(self):
        for value in (0, -1):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    TradeEvent.parse({**BASE, "exit_price": value})

    def test_open_trade_and_finite_loss_remain_valid(self):
        self.assertEqual(TradeEvent.parse({**BASE, "pnl": -4}).pnl, -4)
        trade = TradeEvent.parse({**BASE, "exit_ms": None,
                                  "exit_price": None, "pnl": None})
        self.assertIsNone(trade.exit_ms)

    def test_required_numbers_cannot_be_null_on_an_open_trade(self):
        for field in ('entry_ms', 'entry_price', 'quantity'):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    TradeEvent.parse({**BASE, 'exit_ms': None,
                                      'exit_price': None, 'pnl': None, field: None})


if __name__ == "__main__":
    unittest.main()

"""Meta b1a4d6a book summary -> sole Terminan Math-backed parity proof.

Meta source: src/meta_analyse/book_summary.py @
b1a4d6a41054f0040a88dc80b585380fb6b4f323.
Source algorithm uses (ask - bid) / tick_size for spread_ticks.
This test oracle is inert; no second runtime numeric kernel is created.
"""
from decimal import Decimal, localcontext
from types import SimpleNamespace
import unittest

from terminan.analytics.book_summary import summarize_book
from market_math import book_summary_metrics, tick_distance


def book(bids, asks, valid=True):
    return SimpleNamespace(symbol="BTCUSDT", bids=bids, asks=asks, valid=valid)


class MetaBookSpreadParityTests(unittest.TestCase):
    def test_actual_tick_units_match_meta_for_multiple_precisions_and_sides(self):
        tick_sizes = ("0.001", "0.01", "0.1", "0.25", "1", "10")
        for tick_string in tick_sizes:
            tick = Decimal(tick_string)
            for spread_ticks in (1, 2, 5, 13, 100):
                with self.subTest(tick=tick_string, spread=spread_ticks):
                    bid = Decimal("1000")
                    ask = bid + tick * spread_ticks
                    bids = {bid: Decimal("2.5"), bid - tick: Decimal("1.25")}
                    asks = {ask: Decimal("1.75"), ask + tick: Decimal("3")}
                    result = summarize_book(book(bids, asks), tick)
                    self.assertTrue(result.valid)
                    self.assertEqual(result.best_bid, bid)
                    self.assertEqual(result.best_ask, ask)
                    # Frozen Meta formula, not the raw-price-spread mistake.
                    with localcontext() as context:
                        context.prec = 28
                        expected = (ask - bid) / tick
                    self.assertEqual(result.spread_ticks, expected)
                    self.assertEqual(result.bid_notional,
                                     sum((p * q for p, q in bids.items()), Decimal(0)))
                    self.assertEqual(result.ask_notional,
                                     sum((p * q for p, q in asks.items()), Decimal(0)))
                    self.assertEqual(result.largest_nearby, ())

    def test_math_consumer_preserves_price_spread_contract_separately(self):
        bids = {Decimal("100"): Decimal("2")}
        asks = {Decimal("100.5"): Decimal("3")}
        tick = Decimal("0.1")
        best_bid, best_ask, price_spread, _, _ = book_summary_metrics(bids, asks, tick)
        self.assertEqual(price_spread, Decimal("0.5"))
        self.assertEqual(tick_distance(best_ask, best_bid, tick), Decimal("5"))
        self.assertEqual(summarize_book(book(bids, asks), tick).spread_ticks, Decimal("5"))

    def test_meta_refusal_behavior_preserved_for_invalid_books(self):
        tick = Decimal("0.1")
        for item in (
            book({}, {Decimal("101"): Decimal("1")}),
            book({Decimal("100"): Decimal("1")}, {}),
            book({Decimal("101"): Decimal("1")}, {Decimal("100"): Decimal("1")}),
            book({Decimal("100"): Decimal("1")}, {Decimal("101"): Decimal("1")}, False),
        ):
            with self.subTest(item=item):
                result = summarize_book(item, tick)
                self.assertFalse(result.valid)
                self.assertIsNone(result.spread_ticks)
                self.assertEqual(result.bid_notional, Decimal(0))
                self.assertEqual(result.ask_notional, Decimal(0))
        for tick in (Decimal(0), Decimal("-0.1")):
            with self.assertRaises(ValueError):
                summarize_book(book({Decimal("100"): Decimal(1)},
                                    {Decimal("101"): Decimal(1)}), tick)

    def test_no_local_spread_division_or_second_math_kernel(self):
        import inspect
        import terminan.analytics.book_summary as target
        source = inspect.getsource(target.summarize_book)
        self.assertIn("tick_distance(ask,bid,tick_size)", source)
        self.assertNotIn("/tick_size", source)


class MetaBookFlowBridgePropagationTests(unittest.TestCase):
    def test_corrected_spread_ticks_is_presented_without_new_math(self):
        import asyncio
        from terminan.analytics.flow_bridge import FlowBridge
        tick = Decimal("0.1")
        summary = summarize_book(book(
            {Decimal("100"): Decimal("2")},
            {Decimal("100.5"): Decimal("3")}), tick)
        flow = FlowBridge()
        tape = SimpleNamespace(trades_per_second=2, trusted=True)
        asyncio.run(flow.update("BTCUSDT",
                                {"poc": "100", "delta": "1", "trusted": True}, tape))
        flow.trade_observed("BTCUSDT")
        flow.book_observed("BTCUSDT", summary)
        snapshot = flow.snapshot()
        self.assertEqual(len(snapshot), 1)
        self.assertEqual(snapshot[0].quality, "PROVISIONAL")
        self.assertEqual(snapshot[0].spread, "5")
        self.assertNotEqual(snapshot[0].imbalance, "—")
        flow.invalidate(["BTCUSDT"])
        invalid = flow.snapshot()[0]
        self.assertEqual(invalid.quality, "UNVERIFIED")
        self.assertEqual(invalid.spread, "—")
        self.assertEqual(invalid.imbalance, "—")

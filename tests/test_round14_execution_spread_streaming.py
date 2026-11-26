"""D ROUND 14: historical execution matrix, quoted spread, 100k streaming.

The historical Strattester execution.py source is frozen in tests/fixtures
and is never imported into application execution paths. Only the existing
Terminan PaperEngine and Math SDK perform canonical paper/finance arithmetic.
Tests deliberately do not claim executable order-book liquidity or real fills.
"""
import importlib
import sys
import unittest
from decimal import Decimal, localcontext
from pathlib import Path
from types import SimpleNamespace

from terminan.analytics.book_summary import summarize_book
from terminan.analytics.orderflow_aggregation import aggregate_by_price, aggregate_by_time
from terminan.analytics.orderflow_metrics import Trade
from terminan.paper import PaperEngine
from terminan.research_signals import ResearchBar, ResearchSignal


_ROOT = Path(__file__).resolve().parent / "fixtures"
_D = Decimal


def _old():
    root = str(_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    return importlib.import_module("d_round13_strattester.execution")


def _summary(bid, ask, tick="0.01"):
    book = SimpleNamespace(
        symbol="BTCUSDT", valid=True,
        bids={_D(str(bid)): _D("4")},
        asks={_D(str(ask)): _D("4")})
    return summarize_book(book, _D(tick))


def _synthetic_case(side, outcome, entry_quote, exit_quote):
    """Declared OHLC only: extreme is isolated, no uncertain intrabar order."""
    start = 120000
    entry = float(entry_quote)
    exit_value = float(exit_quote)
    if side == "long":
        stop, target = entry - 5, entry + 5
        if outcome == "target":
            rows = [(start, entry, entry + 1, entry - 1, entry),
                    (start + 60000, exit_value, exit_value + 1,
                     exit_value - 1, exit_value)]
            # exit gap above target is priced at target by both simulators
            assert exit_value >= target
            reason = "TP_GAP"
        else:
            rows = [(start, entry, entry + 1, entry - 1, entry),
                    (start + 60000, exit_value, exit_value + 1,
                     exit_value - 1, exit_value)]
            assert exit_value <= stop
            reason = "SL_GAP"
    else:
        stop, target = entry + 5, entry - 5
        if outcome == "target":
            rows = [(start, entry, entry + 1, entry - 1, entry),
                    (start + 60000, exit_value, exit_value + 1,
                     exit_value - 1, exit_value)]
            assert exit_value <= target
            reason = "TP_GAP"
        else:
            rows = [(start, entry, entry + 1, entry - 1, entry),
                    (start + 60000, exit_value, exit_value + 1,
                     exit_value - 1, exit_value)]
            assert exit_value >= stop
            reason = "SL_GAP"
    return stop, target, rows, reason


class HistoricalFeeSpreadSlippageRound14(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy = _old()

    def test_long_short_gap_fee_slippage_original_against_canonical_engine(self):
        # 2 directions x 2 outcomes x 2 fee rates x 3 slippage policies.
        count = 0
        for side in ("long", "short"):
            for outcome in ("target", "stop"):
                for fee in ("0", "0.00055"):
                    for slippage in ("0", "2", "7.5"):
                        with self.subTest(side=side, outcome=outcome,
                                          fee=fee, slippage=slippage):
                            entry = 100
                            exit_value = (
                                107 if side == "long" and outcome == "target"
                                else 93 if side == "long" else
                                93 if outcome == "target" else 107)
                            stop, target, bars, expected_reason = _synthetic_case(
                                side, outcome, entry, exit_value)
                            policy = self.legacy.ExecutionPolicy(
                                bar_ms=60000, fee_rate=float(fee),
                                slippage_bps=float(slippage),
                                ambiguous_policy="SL_FIRST", position_usd=100)
                            old = self.legacy.simulate_trade(
                                self.legacy.Signal(120000, side, "market", None,
                                                   stop, target),
                                [dict(t=t, open=o, high=h, low=l, close=c,
                                      volume=100) for t,o,h,l,c in bars],
                                policy)
                            engine = PaperEngine(notional=_D("100"),
                                                 fee_rate=_D(fee),
                                                 slippage_bps=_D(slippage))
                            self.assertFalse(engine.enabled)
                            engine.enabled = True  # local-only and in-memory
                            result = engine.execute_signal(
                                ResearchSignal("BTCUSDT", 120000, side,
                                               "market", None, _D(str(stop)),
                                               _D(str(target))),
                                tuple(ResearchBar(t, _D(str(o)), _D(str(h)),
                                                  _D(str(l)), _D(str(c)))
                                      for t,o,h,l,c in bars),
                                bar_ms=60000, as_of_ms=240000,
                                ambiguity_policy="SL_FIRST")
                            self.assertEqual(old.exit_reason, expected_reason)
                            self.assertEqual(result.fill.reason,
                                             "target_gap" if outcome == "target"
                                             else "stop_gap")
                            self.assertEqual(old.entry_time, result.entry_ms)
                            self.assertEqual(old.exit_time, result.exit_ms)
                            self.assertAlmostEqual(float(result.fill.entry),
                                                   old.entry_price, places=10)
                            self.assertAlmostEqual(float(result.fill.exit),
                                                   old.exit_price, places=10)
                            for field, old_value in (
                                ("gross", old.gross_pnl),
                                ("fees", old.fees),
                                ("net", old.net_pnl)):
                                self.assertAlmostEqual(
                                    float(getattr(result.fill, field)),
                                    old_value, places=8)
                            self.assertFalse(engine.positions)
                            count += 1
        self.assertEqual(count, 24)

    def test_explicit_spread_quoted_two_side_books_and_no_implicit_fill(self):
        # The existing Math-backed book owner calculates spread; this must not
        # be automatically subtracted again inside OHLC PaperEngine. Fee and
        # adverse slippage are distinct from an independently quoted spread.
        for tick, units in (("0.001", 1), ("0.01", 3), ("0.1", 5)):
            bid = _D("100")
            ask = bid + _D(tick) * units
            book = _summary(bid, ask, tick)
            with self.subTest(tick=tick, ticks=units):
                self.assertTrue(book.valid)
                self.assertEqual(book.best_ask - book.best_bid,
                                 _D(tick) * units)
                self.assertEqual(book.spread_ticks, _D(units))
                self.assertEqual(book.bid_notional, bid * _D("4"))
                self.assertEqual(book.ask_notional, ask * _D("4"))
                self.assertFalse(PaperEngine().enabled)
                # A last-traded OHLC print does not certify either current
                # executable side or top-of-book order volume/fill ordering.

    def test_spread_nonzero_not_silently_applied_to_midpoint_ohlc_engine(self):
        spread = _summary("99.95", "100.05", "0.01")
        self.assertEqual(spread.spread_ticks, _D("10"))
        engine = PaperEngine(notional="100", fee_rate="0", slippage_bps="0")
        engine.enabled = True
        signal = ResearchSignal("BTCUSDT", 120000, "long", "market",
                                None, _D("95"), _D("105"))
        result = engine.execute_signal(
            signal, (ResearchBar(120000, _D("100"), _D("101"),
                                _D("99"), _D("100")),),
            bar_ms=60000, as_of_ms=180000)
        self.assertEqual((result.fill.entry, result.fill.exit),
                         (_D("100"), _D("100")))
        self.assertEqual((result.fill.fees, result.fill.net),
                         (_D("0"), _D("0")))
        # A quote-derived execution model would need a separately approved
        # spread-aware policy. Do not introduce it or double-charge spread.

    def test_100k_single_pass_late_event_precise_decimal_carry(self):
        class Once:
            def __init__(self):
                self.iterations = 0
            def __iter__(self):
                self.iterations += 1
                if self.iterations != 1:
                    raise AssertionError("TRADES_ITERATED_TWICE")
                for i in range(100000):
                    side = ("buy", "sell", "unknown", "buy")[i % 4]
                    yield Trade(i * 100, _D("100.19"),
                                _D("0.000000000000000001"), side)
                # Chronologically late extra event; independent oracle accounts
                # for final correction, never drop or double apply.
                yield Trade(0, _D("100.19"),
                            _D("0.000000000000000003"), "sell")
        source = Once()
        with localcontext() as context:
            context.prec = 40
            start = _D("1.000000000000000001")
            values = aggregate_by_time(source, 60000, initial_delta=start)
        self.assertEqual(source.iterations, 1)
        self.assertEqual(sum(row.trade_count for _, row in values), 100001)
        self.assertEqual(len(values), 167)
        self.assertEqual(sum((v.buy_volume for _, v in values), _D(0)),
                         _D("0.000000000000050000"))
        self.assertEqual(sum((v.sell_volume for _, v in values), _D(0)),
                         _D("0.000000000000025003"))
        self.assertEqual(sum((v.unknown_volume for _, v in values), _D(0)),
                         _D("0.000000000000025000"))
        self.assertEqual(values[-1][1].cumulative_delta,
                         start + _D("0.000000000000024997"))
        self.assertEqual(values[0][1].trade_count, 601)


if __name__ == "__main__":
    unittest.main()

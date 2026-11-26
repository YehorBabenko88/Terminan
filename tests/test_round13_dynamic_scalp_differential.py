"""Round 13 dynamic historical-vs-canonical scalp and paper parity.

Historical fixture modules are IDENTICAL to Strattester blobs pinned at
37ff7e9d12a4d2dccd788fc493c28557dbe8bcea; never used as an application
plugin. No exchange, runtime host, native DB, paper admission or live trading.
"""
import hashlib
import importlib
import sys
import unittest
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from terminan.market_structure import (
    OHLCObservation, MarketStructureEvent, MarketStructureKind,
    MarketStructureReference, MarketTimeframe,
)
from terminan.strategy_entries import (
    generate_sweep_reclaim_entries, generate_breakout_retest_entries,
    generate_profile_reclaim_entries, SignedFlowObservation,
)
from terminan.continuation_strategy import (
    CandleBodyObservation, generate_continuation_entries,
)
from terminan.volatility import VolatilityMetrics, VolatilityRegime
from terminan.entry_context import ProfileSummary, ProfileKind
from terminan.analytics.orderflow_metrics import Trade
from terminan.analytics.orderflow_aggregation import aggregate_by_time
from terminan.paper import PaperEngine
from terminan.research_signals import ResearchBar


_ARCHIVE = Path(__file__).resolve().parent / "fixtures" / "d_round13_strattester"
_SOURCE_HASH = "533904ce3b28f5d9d69f5bfc72efda168f6674ee"
_EXEC_HASH = "da3d4f66d8debcd770392ab36c4e123f310fc2db"


def _git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _old():
    parent = str(_ARCHIVE.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    return (importlib.import_module("d_round13_strattester.scalp_entries"),
            importlib.import_module("d_round13_strattester.execution"))


def _bar(start, opening, high, low, closing):
    return OHLCObservation(start, start + 60000, start + 60000,
                           opening, high, low, closing)


def _old_bar(start, opening, high, low, closing):
    return {"t":start, "open":opening, "high":high, "low":low,
            "close":closing, "volume":100}


def _event(start, known, kind, level):
    return MarketStructureEvent(
        start, start + 60000, known, known, kind, MarketTimeframe.M1,
        level, level, level, MarketStructureReference(0, 60000, 60000),
        MarketStructureReference(start, start + 60000, known))


def _old_event(start, known, kind, level):
    return SimpleNamespace(event_time=start, known_at=known, kind=kind,
                           value={"level":level, "swing_time":0})


def _vol(event, known, *, atr=.01, ratio=1.5, percentile=.7):
    return VolatilityMetrics(event, known, atr, .01, .01, .02,
                             ratio, ratio, percentile, VolatilityRegime.HIGH,
                             "round13.v1")


def _old_vol(event, known, *, atr=.01, ratio=1.5, percentile=.7):
    return SimpleNamespace(event_time=event, known_at=known, atr_pct=atr,
                           volume_expansion=ratio, percentile=percentile,
                           regime=SimpleNamespace(value="HIGH"))


class HistoricalExecutableParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy, cls.legacy_execution = _old()

    def test_exact_archived_original_git_blobs(self):
        self.assertEqual(_git_blob((_ARCHIVE / "scalp_entries.py").read_bytes()),
                         _SOURCE_HASH)
        self.assertEqual(_git_blob((_ARCHIVE / "execution.py").read_bytes()),
                         _EXEC_HASH)

    def assert_matched_event(self, historical, modern):
        # Comparable decisions/signals only, not source-authentication claims.
        self.assertEqual((historical.decision_time, historical.direction,
                          historical.reference),
                         (modern.decision_ms, modern.side.value, modern.reference))
        self.assertEqual(Decimal(str(historical.signal.stop_loss)),
                         modern.signal.stop)
        self.assertEqual(Decimal(str(historical.signal.take_profit)),
                         modern.signal.target)
        self.assertEqual(modern.signal.entry_kind, "market")
        self.assertIsNone(modern.signal.entry_price)
        self.assertFalse(modern.execution_authority)
        self.assertFalse(modern.trading_authorized)
        self.assertEqual(modern.source_authentication, "NOT_EVALUATED")

    def test_sweep_original_function_dynamic_pair(self):
        rows = (_old_bar(60000, 99, 101, 98, 100),)
        event = _old_event(60000, 120000, "bullish_liquidity_sweep", 99)
        historical, = self.legacy.sweep_reclaim_entries(rows, (event,), bar_ms=60000)
        modern, = generate_sweep_reclaim_entries(
            "BTCUSDT", (_bar(60000, 99, 101, 98, 100),),
            (_event(60000, 120000, MarketStructureKind.BULLISH_LIQUIDITY_SWEEP, 99),),
            as_of_ms=120000, timeframe=MarketTimeframe.M1)
        self.assert_matched_event(historical, modern)

    def test_retest_original_function_dynamic_pair(self):
        rows = (_old_bar(60000, 99, 102, 99, 101),
                _old_bar(120000, 101, 102, 99.9, 101.2))
        event = _old_event(60000, 120000, "bullish_bos", 100)
        v = _old_vol(120000, 180000)
        historical, = self.legacy.breakout_retest_volume_entries(
            rows, (event,), (v,), bar_ms=60000, min_volume_expansion=1.2)
        modern, = generate_breakout_retest_entries(
            "BTCUSDT", (_bar(60000, 99, 102, 99, 101),
                        _bar(120000, 101, 102, 99.9, 101.2)),
            (_event(60000, 120000, MarketStructureKind.BULLISH_BOS, 100),),
            (_vol(120000, 180000),), as_of_ms=180000, timeframe=MarketTimeframe.M1,
            min_volume_ratio=1.2)
        self.assert_matched_event(historical, modern)

    def test_expansion_original_function_dynamic_pair(self):
        historical, = self.legacy.volatility_expansion_entries(
            (_old_bar(60000, 100, 104, 99, 103),),
            (_old_vol(60000, 120000),), bar_ms=60000)
        modern, = generate_continuation_entries(
            "BTCUSDT", (CandleBodyObservation(60000, 120000, 120000, 100, 103),),
            (_vol(60000, 120000),), as_of_ms=120000)
        self.assert_matched_event(historical, modern)

    def test_profile_original_function_dynamic_pair_and_missing_flow(self):
        rows = (_old_bar(0, 99, 99.5, 98.5, 99),
                _old_bar(60000, 99, 101, 98.8, 100.5))
        p = SimpleNamespace(poc=100, known_at=120000,
                            mode=SimpleNamespace(value="TRADE_POC"))
        historical, = self.legacy.poc_reclaim_entries(rows, (p,), bar_ms=60000)
        new_profile = ProfileSummary(100, 101, 99, 120000,
                                     ProfileKind.TRADE_DISTRIBUTION, 2)
        modern, = generate_profile_reclaim_entries(
            "BTCUSDT", (_bar(0, 99, 99.5, 98.5, 99),
                        _bar(60000, 99, 101, 98.8, 100.5)),
            (new_profile,), as_of_ms=120000, timeframe=MarketTimeframe.M1)
        self.assert_matched_event(historical, modern)
        # Documented intentional metadata difference: old absence becomes 0;
        # canonical provenance explicitly preserves unavailable versus measured 0.
        self.assertEqual(historical.metadata["delta"], 0.0)
        self.assertIsNone(modern.metadata["delta"])
        self.assertIsNone(modern.evidence.flow)
        old_blocked = self.legacy.poc_reclaim_entries(
            rows, (p,), ({"t":60000, "known_at":120000, "delta":0},),
            bar_ms=60000)
        new_blocked = generate_profile_reclaim_entries(
            "BTCUSDT", (_bar(0, 99, 99.5, 98.5, 99),
                        _bar(60000, 99, 101, 98.8, 100.5)),
            (new_profile,), (SignedFlowObservation(60000, 120000, 0),),
            as_of_ms=120000, timeframe=MarketTimeframe.M1)
        self.assertEqual(old_blocked, ())
        self.assertEqual(new_blocked, ())

    def test_intentional_delayed_candle_avoids_historical_lookahead(self):
        old_b = (_old_bar(60000, 99, 101, 98, 100),)
        historical, = self.legacy.sweep_reclaim_entries(
            old_b, (_old_event(60000, 120000, "bullish_liquidity_sweep", 99),),
            bar_ms=60000)
        new_bar = replace(_bar(60000, 99, 101, 98, 100),
                          available_at_ms=180000)
        new_event = _event(60000, 120000,
                           MarketStructureKind.BULLISH_LIQUIDITY_SWEEP, 99)
        before = generate_sweep_reclaim_entries(
            "BTCUSDT", (new_bar,), (new_event,), as_of_ms=120000,
            timeframe=MarketTimeframe.M1)
        after = generate_sweep_reclaim_entries(
            "BTCUSDT", (new_bar,), (new_event,), as_of_ms=180000,
            timeframe=MarketTimeframe.M1)
        self.assertEqual(historical.decision_time, 120000)
        self.assertEqual(before, ())
        self.assertEqual(after[0].decision_ms, 180000)

    def test_intentional_late_vol_revision_preserves_causal_prefix(self):
        historical = self.legacy.volatility_expansion_entries(
            (_old_bar(60000, 100, 104, 99, 103),),
            (_old_vol(60000, 120000),
             _old_vol(60000, 180000, ratio=.5)),
            bar_ms=60000)
        modern = generate_continuation_entries(
            "BTCUSDT", (CandleBodyObservation(60000, 120000, 120000, 100, 103),),
            (_vol(60000, 120000),
             _vol(60000, 180000, ratio=.5)), as_of_ms=180000)
        # Historical dict overwrites the earlier same-event snapshot; the
        # canonical algorithm retains the decision visible at 120000.
        self.assertEqual(historical, ())
        self.assertEqual(len(modern), 1)
        self.assertEqual(modern[0].decision_ms, 120000)

    def test_actual_historical_simulator_vs_single_paper_engine_fee_slippage(self):
        # One fully deterministic synthetic long with target hit, no spread model;
        # verifies common gross/fee/slippage math but NOT intrabar model parity.
        event = _old_event(60000, 120000, "bullish_liquidity_sweep", 99)
        historical_entry, = self.legacy.sweep_reclaim_entries(
            (_old_bar(60000, 99, 101, 98, 100),), (event,), bar_ms=60000)
        policy = self.legacy_execution.ExecutionPolicy(
            bar_ms=60000, fee_rate=.00055, slippage_bps=2.0,
            ambiguous_policy="SL_FIRST", position_usd=100)
        historical = self.legacy_execution.simulate_trade(
            historical_entry.signal,
            (_old_bar(120000, 100, 105, 99.9, 103),), policy)
        signal_entry, = generate_sweep_reclaim_entries(
            "BTCUSDT", (_bar(60000, 99, 101, 98, 100),),
            (_event(60000, 120000, MarketStructureKind.BULLISH_LIQUIDITY_SWEEP, 99),),
            as_of_ms=120000, timeframe=MarketTimeframe.M1)
        engine = PaperEngine(notional=Decimal("100"), fee_rate=Decimal(".00055"),
                             slippage_bps=Decimal("2"))
        self.assertFalse(engine.enabled)
        engine.enabled = True  # explicit in-memory offline test only
        result = engine.execute_signal(
            signal_entry.signal,
            (ResearchBar(120000, Decimal("100"), Decimal("105"),
                         Decimal("99.9"), Decimal("103")),),
            bar_ms=60000, as_of_ms=180000, ambiguity_policy="SL_FIRST")
        self.assertEqual(historical.exit_reason, "TP")
        self.assertEqual(result.fill.reason, "target")
        self.assertAlmostEqual(float(result.fill.gross), historical.gross_pnl,
                               places=8)
        self.assertAlmostEqual(float(result.fill.fees), historical.fees,
                               places=8)
        self.assertAlmostEqual(float(result.fill.net), historical.net_pnl,
                               places=8)
        # No bid/ask spread was supplied; this is NOT spread parity or
        # proof of real exchange execution, fill order or liquidity.

    def test_100k_stream_decimal_independent_conservation_oracle(self):
        # Math remains sole accumulator; independent simple arithmetic oracle
        # checks buy/sell/unknown and initial cumulative delta across 100k rows.
        n = 100000
        def source():
            for i in range(n):
                side = ("buy", "sell", "unknown", "buy")[i % 4]
                yield Trade(i * 100, Decimal("100.19"),
                            Decimal(".0001"), side)
        rows = aggregate_by_time(source(), 60000,
                                 initial_delta=Decimal(".125"))
        self.assertEqual(sum(x.trade_count for _, x in rows), n)
        self.assertEqual(sum((x.buy_volume for _, x in rows), Decimal(0)),
                         Decimal("5"))
        self.assertEqual(sum((x.sell_volume for _, x in rows), Decimal(0)),
                         Decimal("2.5"))
        self.assertEqual(sum((x.unknown_volume for _, x in rows), Decimal(0)),
                         Decimal("2.5"))
        self.assertEqual(rows[-1][1].cumulative_delta, Decimal("2.625"))
        self.assertEqual(len(rows), 167)


if __name__ == "__main__":
    unittest.main()

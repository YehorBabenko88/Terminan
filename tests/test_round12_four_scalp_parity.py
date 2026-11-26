"""ROUND 12: causal parity of four historical scalp patterns.

Tests use exact literal source semantics of strattester/research/scalp_entries.py
at Git blob 533904ce3b28f5d9d69f5bfc72efda168f6674ee and the
Terminan/Math typed API. This is not exchange, OS, PG18 or execution admission.
"""
import math
import unittest
from decimal import Decimal
from dataclasses import replace

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
from terminan.paper import PaperEngine
from terminan.strategy_catalog import research_strategy_catalog
from market_math import research_bracket_prices, research_expansion_side


def _vol(event, known, *, atr=.01, ratio=1.5, percentile=.7):
    return VolatilityMetrics(event, known, atr, .01, .01, .02,
                             ratio, ratio, percentile, VolatilityRegime.HIGH,
                             'round12-parity.v1')


def _bar(start, o, h, l, c):
    return OHLCObservation(start, start + 60000, start + 60000, o, h, l, c)


def _event(kind, start, known, level):
    return MarketStructureEvent(
        start, start + 60000, known, known, kind, MarketTimeframe.M1,
        level, level, level,
        MarketStructureReference(0, 60000, 60000),
        MarketStructureReference(start, start + 60000, known))


def _old_risk(side, entry, atr):
    """Exactly the historical Strattester _risk binary64 geometry."""
    d = max(float(entry) * max(float(atr), .0005) * .75,
            float(entry) * .0005)
    if side == 'long':
        return entry - d, entry + d * 1.5
    return entry + d, entry - d * 1.5


def _common(old, new):
    """Compare only invariant event geometry; never erase provenance policy."""
    decision, side, level, entry_price, atr = old
    assert new.decision_ms == decision
    assert new.side.value == side
    assert new.reference == level
    assert new.evidence.entry_price == entry_price
    stop, target = _old_risk(side, entry_price, atr)
    assert (new.signal.stop, new.signal.target) == (
        Decimal(str(stop)), Decimal(str(target)))
    assert (new.signal.stop, new.signal.target) == (
        research_bracket_prices(entry_price, atr, side).as_decimal())
    assert new.execution_authority is False
    assert new.trading_authorized is False
    assert new.source_authentication == 'NOT_EVALUATED'


class FourScalpParityRound12(unittest.TestCase):
    def test_catalog_four_generator_four_spec_and_no_execution(self):
        rows = research_strategy_catalog()
        self.assertEqual((len(rows), sum(x.generator is not None for x in rows)),
                         (8, 4))
        for row in rows:
            self.assertIs(row.execution_authority, False)
            self.assertIs(row.trading_authorized, False)

    def test_sweep_literal_old_vector_and_future_event_gate(self):
        bar = _bar(60000, 99, 101, 98, 100)
        event = _event(MarketStructureKind.BULLISH_LIQUIDITY_SWEEP,
                       60000, 120000, 99)
        fn = lambda cutoff: generate_sweep_reclaim_entries(
            'BTCUSDT', (bar,), (event,), as_of_ms=cutoff,
            timeframe=MarketTimeframe.M1)
        self.assertEqual(fn(119999), ())
        row, = fn(120000)
        _common((120000, 'long', 99, 100, .002), row)
        delayed = replace(event, available_at_ms=180000,
                          source_available_at_ms=180000,
                          trigger_reference=MarketStructureReference(
                              60000, 120000, 180000))
        self.assertEqual(generate_sweep_reclaim_entries(
            'BTCUSDT', (bar,), (delayed,), as_of_ms=179999,
            timeframe=MarketTimeframe.M1), ())
        d, = generate_sweep_reclaim_entries(
            'BTCUSDT', (bar,), (delayed,), as_of_ms=180000,
            timeframe=MarketTimeframe.M1)
        self.assertEqual(d.decision_ms, 180000)

    def test_breakout_original_vector_uses_next_bar_and_math(self):
        bars = (_bar(60000, 99, 102, 99, 101),
                _bar(120000, 101, 102, 99.9, 101.2))
        event = _event(MarketStructureKind.BULLISH_BOS, 60000, 120000, 100)
        vol = _vol(120000, 180000)
        fn = lambda bb, cutoff: generate_breakout_retest_entries(
            'BTCUSDT', bb, (event,), (vol,), as_of_ms=cutoff,
            timeframe=MarketTimeframe.M1)
        self.assertEqual(fn(bars[:1], 180000), ())
        self.assertEqual(fn(bars, 179999), ())
        row, = fn(bars, 180000)
        _common((180000, 'long', 100, 101.2, .01), row)
        self.assertEqual(row.evidence.volume_ratio, 1.5)
        self.assertIsNone(row.signal.entry_price)

    def test_volatility_expansion_old_vector_and_causal_revision(self):
        body = CandleBodyObservation(60000, 120000, 120000, 100, 103)
        vol = _vol(60000, 120000)
        fn = lambda cutoff, vv=(vol,): generate_continuation_entries(
            'BTCUSDT', (body,), vv, as_of_ms=cutoff)
        self.assertEqual(fn(119999), ())
        row, = fn(120000)
        _common((120000, 'long', 103, 103, .01), row)
        self.assertEqual(research_expansion_side(100, 103, .01), 'long')
        later = replace(vol, available_at_ms=180000, volume_ratio=0)
        self.assertEqual(fn(240000, (vol, later)), (row,))

    def test_poc_original_vector_preserves_missing_flow_none(self):
        bars = (_bar(0, 99, 99.5, 98.5, 99),
                _bar(60000, 99, 101, 98.8, 100.5))
        profile = ProfileSummary(100, 101, 99, 120000,
                                 ProfileKind.TRADE_DISTRIBUTION, 2)
        fn = lambda cutoff, pp=(profile,), flow=(): generate_profile_reclaim_entries(
            'BTCUSDT', bars, pp, flow, as_of_ms=cutoff,
            timeframe=MarketTimeframe.M1)
        self.assertEqual(fn(119999), ())
        row, = fn(120000)
        _common((120000, 'long', 100, 100.5, .002), row)
        self.assertIsNone(row.evidence.flow)
        self.assertIsNone(row.metadata['delta'])
        self.assertEqual(fn(120000, flow=(SignedFlowObservation(
            60000, 120000, 0),)), ())
        self.assertEqual(fn(120000, flow=(SignedFlowObservation(
            60000, 120000, -1),)), ())
        positive, = fn(120000, flow=(SignedFlowObservation(
            60000, 120000, 1),))
        self.assertEqual(positive.evidence.flow.delta, 1)
        self.assertEqual(fn(120000, pp=(replace(
            profile, available_at_ms=120001),)), ())

    def test_documented_historical_causal_divergence_at_delayed_bar(self):
        # Old _known_bar used t+bar_ms even if a bar arrived late.
        # Canonical declared available_at_ms is later and refuses look-ahead.
        bar = replace(_bar(60000, 99, 101, 98, 100),
                      available_at_ms=180000)
        event = _event(MarketStructureKind.BULLISH_LIQUIDITY_SWEEP,
                       60000, 120000, 99)
        self.assertEqual(generate_sweep_reclaim_entries(
            'BTCUSDT', (bar,), (event,), as_of_ms=120000,
            timeframe=MarketTimeframe.M1), ())
        row, = generate_sweep_reclaim_entries(
            'BTCUSDT', (bar,), (event,), as_of_ms=180000,
            timeframe=MarketTimeframe.M1)
        self.assertEqual(row.decision_ms, 180000)

    def test_math_zero_body_threshold_is_historical_boundary_not_permission(self):
        # Source Strattester _risk and Math do not authorize orders.
        self.assertEqual(research_expansion_side(100, 100, 0), 'short')
        self.assertIsNone(research_expansion_side(100, 100.1, .01))
        engine = PaperEngine()
        self.assertIs(engine.enabled, False)


if __name__ == '__main__':
    unittest.main()

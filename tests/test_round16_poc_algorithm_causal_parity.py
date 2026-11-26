"""ROUND 16: dynamic historical POC numerical parity and causal composition.

The only executed historical source is an exact, inert Strattester test fixture.
Production composes the existing Math value-area kernel and Terminan reclaim
generator; all 20 migrated historical strategy specifications stay SPEC_ONLY.
"""
import hashlib
import importlib
import sys
import unittest
from decimal import Decimal
from pathlib import Path

from terminan.historical_poc_research import research_historical_poc
from terminan.historical_research_specifications import historical_research_specification
from terminan.market_structure import OHLCObservation, MarketTimeframe
from terminan.entry_context import ProfileKind
from terminan.strategy_entries import SignedFlowObservation, EntrySide
from terminan.paper import PaperEngine


_SOURCE = Path(__file__).resolve().parent / "fixtures" / "d_round13_strattester"
_BLOB = "6d74dd706c720c3f801bb88ff886ca9be97235e2"
_BAR = 60000


def _bar(t, opening, closing, *, ready=None):
    hi = max(opening, closing) + 1
    lo = min(opening, closing) - 1
    return OHLCObservation(t, t + _BAR, t + _BAR if ready is None else ready,
                           opening, hi, lo, closing)


def _history():
    parent = str(_SOURCE.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    return importlib.import_module("d_round13_strattester.volume_profile")


def _study(direction="long", *, source="TRADE", flow=()):
    if direction == "long":
        bars = (_bar(0, 99, 99), _bar(_BAR, 99, 101))
    else:
        bars = (_bar(0, 101, 101), _bar(_BAR, 101, 99))
    if source == "TRADE":
        rows = (
            dict(event_ms=0, available_at_ms=0, price=100, volume=3),
            dict(event_ms=1, available_at_ms=1, price=101, volume=1),
            dict(event_ms=2, available_at_ms=2, price=99, volume=1),
        )
    else:
        rows = (
            dict(event_start_ms=0, event_end_ms=1, available_at_ms=1,
                 high=101, low=99, close=100, volume=3),
            dict(event_start_ms=1, event_end_ms=2, available_at_ms=2,
                 high=102, low=100, close=101, volume=1),
            dict(event_start_ms=2, event_end_ms=3, available_at_ms=3,
                 high=100, low=98, close=99, volume=1),
        )
    return bars, rows, research_historical_poc(
        "BTCUSDT", bars, rows, source_kind=source, as_of_ms=120000,
        timeframe=MarketTimeframe.M1, flow=flow,
    )


class HistoricalPocRound16Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = _history()

    def test_source_is_unmodified_historical_git_blob(self):
        src = (_SOURCE / "volume_profile.py").read_bytes()
        self.assertEqual(
            hashlib.sha1(b"blob " + str(len(src)).encode("ascii") +
                         b"\0" + src).hexdigest(), _BLOB
        )

    def test_original_trade_profile_math_and_canonical_long_short(self):
        for direction in ("long", "short"):
            with self.subTest(direction=direction):
                bars, source, modern = _study(direction)
                old = self.old.trade_profile(
                    tuple({"t": r["event_ms"], "price": r["price"],
                           "volume": r["volume"]} for r in source),
                    known_at=120000,
                )
                self.assertEqual(
                    (modern.profile.poc, modern.profile.value_area_high,
                     modern.profile.value_area_low,
                     modern.profile.value_area_width),
                    (old.poc, old.vah, old.val, old.value_area_width),
                )
                self.assertEqual(modern.profile.kind, ProfileKind.TRADE_DISTRIBUTION)
                self.assertEqual(len(modern.entries), 1)
                result, = modern.entries
                self.assertEqual(result.side, EntrySide.LONG if direction == "long"
                                 else EntrySide.SHORT)
                self.assertEqual(result.decision_ms, 120000)
                self.assertEqual(result.reference, old.poc)
                self.assertIsNone(result.evidence.flow)
                self.assertFalse(result.trading_authorized)
                self.assertFalse(PaperEngine().enabled)

    def test_original_proxy_math_but_no_trade_poc_upgrade(self):
        bars, source, modern = _study("long", source="CANDLE_PROXY")
        old = self.old.proxy_profile(
            tuple({"t": r["event_start_ms"],
                   "high": r["high"], "low": r["low"],
                   "close": r["close"], "volume": r["volume"]}
                  for r in source), known_at=120000,
        )
        self.assertEqual(
            (modern.profile.poc, modern.profile.value_area_high,
             modern.profile.value_area_low, modern.profile.value_area_width),
            (old.poc, old.vah, old.val, old.value_area_width),
        )
        self.assertEqual(modern.profile.kind, ProfileKind.CANDLE_PROXY)
        self.assertEqual(modern.profile.available_at_ms, 3)
        self.assertEqual(len(modern.entries), 1)
        self.assertEqual(modern.entries[0].evidence.profile_kind, ProfileKind.CANDLE_PROXY)

    def test_declared_delayed_trade_never_leaks_into_past(self):
        bars = (_bar(0, 99, 99), _bar(_BAR, 99, 101))
        past = (dict(event_ms=0, available_at_ms=0, price=100, volume=2),)
        delayed = dict(event_ms=1, available_at_ms=180000, price=150, volume=99)
        original = research_historical_poc(
            "BTCUSDT", bars, past, source_kind="TRADE",
            as_of_ms=120000, timeframe=MarketTimeframe.M1,
        )
        current = research_historical_poc(
            "BTCUSDT", bars, past + (delayed,), source_kind="TRADE",
            as_of_ms=120000, timeframe=MarketTimeframe.M1,
        )
        self.assertEqual(original, current)
        # Original Strattester includes the numerically earlier late delivery:
        # its only timestamp is event time. Canonical explicitly refuses
        # future availability until it is actually declared available.
        old = self.old.trade_profile(
            ({"t":0,"price":100,"volume":2},
             {"t":1,"price":150,"volume":99}), known_at=120000)
        self.assertEqual(old.poc, 150)
        self.assertEqual(current.profile.poc, 100)

    def test_missing_flow_and_observed_zero_are_not_equal(self):
        _, _, omitted = _study("long")
        zero_flow = (SignedFlowObservation(0, 120000, 0),)
        _, _, rejected = _study("long", flow=zero_flow)
        self.assertEqual(len(omitted.entries), 1)
        self.assertIsNone(omitted.entries[0].evidence.flow)
        self.assertEqual(rejected.entries, ())

    def test_invalid_later_row_rejected_and_no_implicit_proxy_fallback(self):
        bars, rows, _ = _study()
        with self.assertRaises(ValueError):
            research_historical_poc(
                "BTCUSDT", bars, rows +
                (dict(event_ms=1, available_at_ms=200000,
                      price=float("nan"), volume=1),),
                source_kind="TRADE", as_of_ms=120000,
                timeframe=MarketTimeframe.M1,
            )
        with self.assertRaises(ValueError):
            research_historical_poc(
                "BTCUSDT", bars, rows, source_kind="NOT_AVAILABLE",
                as_of_ms=120000, timeframe=MarketTimeframe.M1,
            )
        with self.assertRaises(ValueError):
            research_historical_poc(
                "BTCUSDT", bars, rows, source_kind="CANDLE_PROXY",
                as_of_ms=120000, timeframe=MarketTimeframe.M1,
            )
        with self.assertRaises(ValueError):
            research_historical_poc(
                "BTCUSDT", bars, (), source_kind="TRADE",
                as_of_ms=120000, timeframe=MarketTimeframe.M1,
            )

    def test_historical_spec_kept_spec_only_not_second_registry(self):
        definition = historical_research_specification("POC_MEAN_REVERSION")
        self.assertEqual(definition.execution_status, "SPEC_ONLY")
        self.assertIsNone(definition.signal_generator)
        self.assertFalse(definition.execution_authority)
        bars, rows, entry = _study()
        self.assertFalse(entry.execution_authority)
        self.assertFalse(entry.trading_authorized)
        self.assertEqual(entry.historical_strategy_availability, "SPEC_ONLY")
        self.assertEqual(entry.profile_source, "TRADE")
        self.assertTrue(all(not e.execution_authority for e in entry.entries))


if __name__ == "__main__":
    unittest.main()

"""Pinned original Meta PaperEngine vs canonical Terminan parity.

Run only with exact source checkouts:
  upstream/meta @ 9d0fb5c79a5da13b23f8daa066035b09f676a6fc
  upstream/math @ 98d6783522aac7155cbb4635e5b29239746d88e0
This is offline source parity, NOT live exchange qualification.
"""
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from pathlib import Path
import os
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
META_SHA = "9d0fb5c79a5da13b23f8daa066035b09f676a6fc"
MATH_SHA = "98d6783522aac7155cbb4635e5b29239746d88e0"
META_ROOT = ROOT / "upstream" / "meta"
MATH_ROOT = ROOT / "upstream" / "math"


def pinned_head(path, expected):
    value = subprocess.check_output(
        ["git", "-C", str(path), "rev-parse", "HEAD"], text=True
    ).strip()
    if value != expected:
        raise RuntimeError("SOURCE_PIN_MISMATCH")
    return value


pinned_head(META_ROOT, META_SHA)
pinned_head(MATH_ROOT, MATH_SHA)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(META_ROOT / "src"))

from meta_analyse.core import (  # noqa: E402
    PaperEngine as OriginalEngine, Trade as OriginalTrade, new_minute,
)
from terminan.paper import (  # noqa: E402
    ClosedMinute, ExecutionTrade, PaperEngine,
)
from market_compute_api import compute_batch  # noqa: E402
from terminan.paper import apply_sizing, ruin_stats, trade_net_pnl  # noqa: E402
import importlib.util  # noqa: E402

# Frozen historic Math file is loaded as a source-authentic parity oracle only.
_sizing_file = MATH_ROOT / 'python' / 'history_sizing.py'
_sizing_blob = subprocess.check_output(
    ['git', '-C', str(MATH_ROOT), 'hash-object', str(_sizing_file)], text=True,
).strip()
if _sizing_blob != '322289e3f9c5017c9b67babda68920c36ff5228e':
    raise RuntimeError('HISTORIC_TRADE_SIZING_BLOB_MISMATCH')
_sizing_spec = importlib.util.spec_from_file_location('pinned_historic_sizing', _sizing_file)
_original_sizing = importlib.util.module_from_spec(_sizing_spec)
_sizing_spec.loader.exec_module(_original_sizing)

T = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)
SYMBOL = "BTCUSDT"


def original_event(offset, value, symbol=SYMBOL):
    return OriginalTrade(symbol, T + timedelta(seconds=offset), D(value),
                         D("1"), "Buy")


def terminan_event(offset, value, symbol=SYMBOL):
    return ExecutionTrade(symbol, T + timedelta(seconds=offset), D(value))


def equivalent_state(first, second):
    return {
        "reference": first.reference,
        "positions": {k: asdict(v) for k, v in first.positions.items()},
        "fills": [asdict(v) for v in first.fills],
    } == {
        "reference": second.reference,
        "positions": {k: asdict(v) for k, v in second.positions.items()},
        "fills": [asdict(v) for v in second.fills],
    }


class PinnedSourcePaperParity(unittest.TestCase):
    def make_pair(self, *, complete=True):
        original, new = OriginalEngine(), PaperEngine()
        original.enabled = new.enabled = True
        candle = new_minute(original_event(0, "100"), D("1"),
                            complete=complete)
        original.on_closed_minute(SYMBOL, candle)
        new.on_closed_minute(
            SYMBOL, ClosedMinute(candle.start, candle.poc, candle.complete))
        self.assertTrue(equivalent_state(original, new))
        return original, new

    def assert_next(self, original, new, seconds, price):
        old_fill = original.on_trade(original_event(seconds, price))
        new_fill = new.on_trade(terminan_event(seconds, price))
        self.assertEqual(
            asdict(old_fill) if old_fill else None,
            asdict(new_fill) if new_fill else None,
        )
        self.assertTrue(equivalent_state(original, new))

    def test_same_short_target_and_fees(self):
        old, new = self.make_pair()
        self.assert_next(old, new, 61, "102")
        self.assert_next(old, new, 62, "100")

    def test_same_long_stop_gap_and_fees(self):
        old, new = self.make_pair()
        self.assert_next(old, new, 60, "98")
        self.assert_next(old, new, 62, "95")

    def test_same_no_next_minute_entry(self):
        old, new = self.make_pair()
        self.assert_next(old, new, 121, "103")
        self.assertEqual(new.positions, {})

    def test_same_unclosed_minute_refusal(self):
        old, new = self.make_pair(complete=False)
        self.assert_next(old, new, 61, "103")
        self.assertEqual(new.reference, {})

    def test_actual_installed_math_sdk_poc_used_by_terminan(self):
        source = {"snapshot_sha256": "a" * 64, "as_of_ms": 1,
                  "units": {"price": "quote/base", "volume": "base"}}
        request = {"schema": "math.market.compute.v1",
                   "execution_authority": False, "source": source,
                   "operations": [{
                       "operation": "volume_profile_poc",
                       "input": {"profile": [
                           {"price": "100", "volume": "1"}],
                           "close": "100"},
                   }]}
        output = compute_batch(request)
        self.assertEqual(output["provenance"], "CALLER_SUPPLIED_UNATTESTED")
        old = OriginalEngine()
        new = PaperEngine()
        old.enabled = new.enabled = True
        old.on_closed_minute(
            SYMBOL, new_minute(original_event(0, "100"), D("1")))
        new.on_math_closed_minute(SYMBOL, T, request)
        self.assertTrue(equivalent_state(old, new))
        self.assert_next(old, new, 61, "102")
        self.assert_next(old, new, 62, "100")



class PinnedTradeSizingOwnershipParity(unittest.TestCase):
    """Identical inputs against the exact historical Math trade-policy source."""

    def setUp(self):
        self.rows = [
            {"signal_id": "a", "pnl": -3.2, "fees": .13, "slippage": .07, "mfe": 6., "mae": -5.},
            {"signal_id": "b", "pnl": -1., "fees": .1, "slippage": 0., "mfe": 1., "mae": -2.},
            {"signal_id": "c", "pnl": 4., "fees": .2, "slippage": .1, "mfe": 10., "mae": -3.},
            {"signal_id": "d", "pnl": 2.5, "fees": 0., "slippage": 0., "mfe": 7., "mae": -1.},
        ]

    def test_all_sizing_modes_exact_historic_output(self):
        for mode in ("FIXED", "MARTINGALE", "ANTI_MARTINGALE"):
            for cap in (1., 4.):
                with self.subTest(mode=mode, cap=cap):
                    options = dict(mode=mode, base_size=1., multiplier=2.,
                                   max_steps=3, max_size=cap)
                    self.assertEqual(
                        apply_sizing(self.rows, **options),
                        _original_sizing.apply_sizing(self.rows, **options),
                    )

    def test_historic_ruin_ledger_parity(self):
        for starting_equity in (10., 100., 1000.):
            with self.subTest(starting_equity=starting_equity):
                options = dict(starting_equity=starting_equity, ruin_fraction=.5)
                self.assertEqual(
                    ruin_stats(self.rows, **options),
                    _original_sizing.ruin_stats(self.rows, **options),
                )

    def test_net_accounting_is_owned_by_terminan(self):
        for row in self.rows:
            self.assertEqual(
                trade_net_pnl(row),
                float(row.get("pnl", 0)) - float(row.get("fees", 0))
                - float(row.get("slippage", 0)),
            )

if __name__ == "__main__":
    unittest.main(verbosity=2)

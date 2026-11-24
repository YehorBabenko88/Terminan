"""Test the pinned installed MarketData → Terminan → Math cohort without a live DB."""

from decimal import Decimal, localcontext
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


if not sys.flags.isolated:
    raise RuntimeError("Run this installed-wheel check with python -I")

WHEEL_ROOT = Path(os.environ["TERMINAN_COHORT_PATH"]).resolve(strict=True)
sys.path.insert(0, str(WHEEL_ROOT))

import market_compute_api
import market_math
from market_data import history_snapshot
from market_data.provenance import digest
from terminan import levels


DAY = 86_400_000
IDENTITY = {"venue": "bybit", "market_type": "linear", "symbol": "BTCUSDT"}
GOLDEN = {
    "1h": "87a6c51f33daf5a6f5c393981db755253455f33ce9b4c7ff749671dfe9875e32",
    "4h": "f132f9066cb05eae6315f928ed6c90641432c0ace53a4b2d25bc9ea60da60746",
    "1d": "bddca3daf42b8feda7b851ec55398ff41a0af8e1dc85b17ab2eca2a7e5de5e62",
    "1w": "1615da03307712f09c17edf280588eed35a7d713a79a83a61dada77e4af15ea2"
}


def rollup(timeframe, minutes):
    start = 4 * DAY if timeframe == "1w" else 0
    end = start + 2 * minutes * 60_000
    units = {"price": "quote/base", "volume": "base"}
    source = {"identity": "fixture", "epoch": "s18", "source_revision": "1"}
    rows = []
    for index in range(2 * minutes):
        closed = start + (index + 1) * 60_000
        rows.append(dict(event_start_ms=closed - 60_000, event_end_ms=closed,
                         open=100, close=100, high=110 if index < minutes else 108,
                         low=90, volume=1, available_at_ms=closed, watermark_ms=closed))
    catalog, pages_by_id = {}, {}
    for index in range(0, len(rows), 1680):
        chunk = rows[index:index + 1680]
        request = dict(IDENTITY, start_ms=chunk[0]["event_start_ms"],
                       end_ms=chunk[-1]["event_end_ms"], as_of_ms=end, units=units)
        page = dict(request=request, trust=dict(source, evidence_class="HISTORICAL"))
        pin = digest(page)
        catalog[pin] = page
        pages_by_id[pin] = dict(rows=chunk, source=source, request=request,
                               dataset_id=str(index), dataset_fingerprint=pin)
    selection = dict(IDENTITY, schema="market_data.history.selection.v4", timeframe=timeframe,
                     snapshot_ids=list(catalog), start_ms=start, end_ms=end)

    def read_fixture(connection, page, catalog, *, continuing=False):
        return pages_by_id[page["snapshot_id"]]

    pages = history_snapshot.plan_multipin(selection, catalog)
    with patch.object(history_snapshot, "select_snapshot", side_effect=read_fixture):
        return history_snapshot.read_multipin_rollup(None, selection, pages, catalog)


def scan(snapshot, pin, timeframe, minutes):
    start = 4 * DAY if timeframe == "1w" else 0
    end = start + 2 * minutes * 60_000
    return levels.levels_from_market_data_series(
        snapshot, trusted_fingerprint=pin, symbol=IDENTITY["symbol"],
        market_type=IDENTITY["market_type"], timeframe=timeframe,
        start_ms=start, end_ms=end, as_of_ms=end,
    )


def rehash(snapshot):
    return dict(snapshot, dataset_fingerprint=digest(
        {key: value for key, value in snapshot.items() if key != "dataset_fingerprint"}
    ))


class InstalledMarketDataLevelsTests(unittest.TestCase):
    def test_packages_resolve_from_installed_wheel_root(self):
        for module in (levels, history_snapshot, market_compute_api, market_math):
            self.assertTrue(Path(module.__file__).resolve().is_relative_to(WHEEL_ROOT))

    def test_exact_sequences_produce_levels_with_independent_fixture_pins(self):
        for timeframe, minutes in (("1h", 60), ("4h", 240), ("1d", 1440), ("1w", 10080)):
            with self.subTest(timeframe=timeframe):
                snapshot = rollup(timeframe, minutes)
                pin = GOLDEN[timeframe]
                self.assertEqual(snapshot["dataset_fingerprint"], pin)
                self.assertEqual(len(snapshot["rows"]), 2)
                if timeframe == "1w":
                    self.assertEqual(len(snapshot["parents"]), 12)
                result = scan(snapshot, pin, timeframe, minutes)
                self.assertEqual({item["price"] for item in result}, {110, 108, 90})

    def test_reject_unpinned_and_lookahead_or_broken_sequences_before_math(self):
        snapshot = rollup("1h", 60)
        first, second = snapshot["rows"]
        with patch.object(levels, "untouched_levels") as compute:
            for pin in (None, "a" * 64):
                with self.assertRaises(ValueError):
                    scan(snapshot, pin, "1h", 60)
            for rows in ([first], [second, first], [first, first],
                         [first, dict(second, available_at_ms=snapshot["as_of_ms"] + 1)],
                         [first, dict(second, watermark_ms=second["event_end_ms"] - 1)]):
                damaged = rehash(dict(snapshot, rows=rows))
                with self.assertRaises(ValueError):
                    scan(damaged, damaged["dataset_fingerprint"], "1h", 60)
            for invalid in (dict(snapshot, evidence_class="SYNTHETIC"),
                            dict(snapshot, source={"identity": "fixture"}),
                            dict(snapshot, as_of_ms=snapshot["as_of_ms"] + 1)):
                damaged = rehash(invalid)
                with self.assertRaises(ValueError):
                    scan(damaged, damaged["dataset_fingerprint"], "1h", 60)
            compute.assert_not_called()

    def test_installed_math_rounds_tick_boundaries_independently_of_context(self):
        for precision in (3, 5, 6, 28):
            with self.subTest(precision=precision), localcontext() as context:
                context.prec = precision
                for price, expected in (("100.005", "100.01"), ("12345.675", "12345.68")):
                    self.assertEqual(market_math.price_bucket(
                        Decimal(price), Decimal("0.01")), Decimal(expected))


if __name__ == "__main__":
    unittest.main()

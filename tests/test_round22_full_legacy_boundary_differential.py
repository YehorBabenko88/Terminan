"""ROUND22 native regression: run the full ORIGINAL 28-variant legacy suite.

Execute only the SHA-pinned historical AST, confined to tests. The source
Aggregator adds levels at the 1h boundary *before* processing that same
minute. This noncausal backtest timing is not a production ResearchSignal.
"""
import ast
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha1
import heapq
import math
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import unittest

from terminan.legacy_level_base_research import propose_legacy_level_base
from terminan.research_signals import ResearchBar


_ARCHIVE = Path(__file__).resolve().parent / "fixtures" / "d_round13_strattester" / "legacy_grid.py"
_BLOB = "87a7ea0fa5b66b2faeb2e8be45efa183cbc16ccd"
_NAMES = frozenset((
    "BacktestConfig", "MinuteCandle", "LevelSeed", "Level",
    "EngineTrade", "_AggBar", "BacktestEngine", "MultiTimeframeAggregator",
    "legacy_variants", "_trade_row", "run_legacy_suite",
))


def _original_full_suite():
    raw = _ARCHIVE.read_bytes()
    actual = sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
    if actual != _BLOB:
        raise AssertionError("ORIGINAL_STRATTESTER_BLOB_MISMATCH")
    nodes = ast.parse(raw.decode("utf-8"), filename=str(_ARCHIVE)).body
    selected = [
        n for n in nodes if isinstance(n, (ast.ClassDef, ast.FunctionDef))
        and n.name in _NAMES
    ]
    if len(selected) != len(_NAMES) or {n.name for n in selected} != _NAMES:
        raise AssertionError("ORIGINAL_STRATTESTER_AST_SET_MISMATCH")
    env = dict(dataclass=dataclass, heapq=heapq, math=math,
               datetime=datetime, timezone=timezone,
               Optional=Optional, Dict=Dict, List=List, Tuple=Tuple)
    exec(compile(ast.Module(body=selected, type_ignores=[]),
                 str(_ARCHIVE), "exec"), env)
    return env


def _boundary_rows(original, side):
    c = original["MinuteCandle"]
    if side == "HIGH":
        rows = [c(i * 60000, 99.9, 100, 99.9, 99.9) for i in range(60)]
        first = (3600000, 99.5, 100, 99, 99.7)
        second = (3660000, 99.7, 102, 99.6, 101)
    else:
        rows = [c(i * 60000, 100.1, 100.1, 100, 100.1) for i in range(60)]
        first = (3600000, 100.5, 101, 100, 100.4)
        second = (3660000, 100.4, 101, 98, 99)
    rows.extend((c(*first), c(*second)))
    return rows, first


class OriginalLegacyBoundaryRound22(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = _original_full_suite()

    def test_full_original_all_28_variants_execute_at_hour_boundary(self):
        original = self.original
        names = set(original["legacy_variants"]())
        self.assertEqual(len(names), 28)
        self.assertEqual(len([x for x in names if x.startswith("LOW_")]), 13)
        self.assertEqual(len([x for x in names if x.startswith("HIGH_")]), 13)
        # LOW_LONG/HIGH_SHORT are reversal variants; exact 28 source names.
        self.assertTrue({"BASE", "LOW_BASE", "HIGH_BASE",
                         "REVERSAL_BASE", "HIGH_SHORT", "LOW_LONG"} <= names)
        for side, expected_count, expected_entry in (
            ("HIGH", 16, 99.5), ("LOW", 15, 100.5),
        ):
            with self.subTest(side=side):
                rows, _ = _boundary_rows(original, side)
                result = original["run_legacy_suite"](rows)
                self.assertEqual(set(result), names)
                self.assertTrue(all(out["candles_processed"] == 62
                                    for out in result.values()))
                self.assertEqual(sum(len(out["trades"]) for out in result.values()),
                                 expected_count)
                target = result[f"{side}_BASE"]
                seed, = (level for level in target["levels"]
                         if level["timeframe"] == "1H")
                self.assertEqual((seed["price"], seed["available_at"],
                                  seed["entries"]),
                                 (100.0, 3600000, 1))
                trade, = (row for row in target["trades"]
                          if row["timeframe"] == "1H")
                self.assertEqual(trade["direction"],
                                 "LONG" if side == "HIGH" else "SHORT")
                self.assertEqual(trade["entry_time"], 3600000)
                self.assertAlmostEqual(trade["entry_price"], expected_entry)
                self.assertEqual((trade["exit_time"], trade["exit_reason"]),
                                 (3660000, "TP"))
                self.assertAlmostEqual(trade["gross_pnl"], 1.5, places=9)
                self.assertAlmostEqual(trade["fees"],
                                       0.110825 if side == "HIGH" else 0.109175,
                                       places=9)

    def test_same_minute_original_entry_rejected_by_causal_projector(self):
        original = self.original
        for side, entry in (("HIGH", 99.5), ("LOW", 100.5)):
            with self.subTest(side=side):
                rows, first = _boundary_rows(original, side)
                result = original["run_legacy_suite"](
                    rows, variant_names=(f"{side}_BASE",))
                actual, = result[f"{side}_BASE"]["trades"]
                self.assertEqual(actual["entry_time"], 3600000)
                research_bar = ResearchBar(
                    first[0], *(Decimal(str(x)) for x in first[1:]))
                with self.assertRaisesRegex(ValueError,
                                            "LEGACY_LEVEL_EXACT_NEXT_BAR_REQUIRED"):
                    propose_legacy_level_base(
                        "BTCUSDT", f"{side}_BASE", Decimal("100"), 3600000,
                        research_bar, bar_ms=60000, as_of_ms=3720000)

    def test_original_28_family_policies_are_not_production_grants(self):
        result = self.original["legacy_variants"]()
        self.assertEqual(result["HIGH_FIRST_TOUCH"].max_entries_per_level, 1)
        self.assertEqual(result["LOW_FIRST_TOUCH"].max_entries_per_level, 1)
        self.assertEqual(result["HIGH_AGE_24H"].max_level_age_ms, 86400000)
        self.assertEqual(result["LOW_AGE_30D"].max_level_age_ms, 2592000000)
        self.assertEqual(result["HIGH_SHORT"].high_direction, "SHORT")
        self.assertEqual(result["LOW_LONG"].low_direction, "LONG")
        self.assertEqual(result["HIGH_SL075"].stop_loss, 0.0075)
        self.assertEqual(result["LOW_TP25"].take_profit, 0.025)
        self.assertEqual(result["HIGH_ENTRY_010"].entry_distance, 0.001)
        self.assertEqual(result["LOW_ENTRY_040"].entry_distance, 0.004)
        # The legacy source remains test-only. No runtime registry or
        # execution authorization is created by these AST tests.


if __name__ == "__main__":
    unittest.main()

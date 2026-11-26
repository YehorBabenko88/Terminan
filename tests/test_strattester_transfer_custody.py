"""Frozen Strattester scalp-hypothesis custody for the Terminan owner.

This is a test-only, explicit mapping. It never imports Strattester, loads a
plugin, calls an exchange, or grants paper/real execution.
Source: strattester/main@37ff7e9d12a4d2dccd788fc493c28557dbe8bcea
  strattester/strategies/builtin/research_scalp.py
The labels below mirror all eight original hypothesis identities. The canonical
Terminan IDs are intentionally different; no executable legacy aliases exist.
"""
import ast
import unittest
from pathlib import Path

SOURCE_SHA = "37ff7e9d12a4d2dccd788fc493c28557dbe8bcea"

# Legacy name, canonical ID, legacy execution state, required setup.
TRANSFER = (
    ("SCALP_LEVEL_IMPULSE", "level_impulse", False, "level_impulse"),
    ("SCALP_LEVEL_IMPULSE_DELTA", "level_impulse_delta", False, "level_impulse"),
    ("SCALP_SWEEP_RECLAIM", "sweep_reclaim_v2", True, "liquidity_sweep"),
    ("SCALP_FAILED_BREAKOUT", "failed_breakout", False, "failed_breakout"),
    ("SCALP_BREAKOUT_RETEST_VOLUME", "breakout_retest_v2", True, "breakout_retest"),
    ("SCALP_VOL_EXPANSION_CONTINUATION", "volatility_continuation_v2", True, "compression_expansion"),
    ("SCALP_POC_RECLAIM", "profile_reclaim_v2", True, "poc_reclaim"),
    ("SCALP_OI_DELTA_IMPULSE", "open_interest_delta_impulse", False, "impulse"),
)

class StrattesterTransferCustodyTests(unittest.TestCase):
    def test_all_eight_legacy_roles_have_exact_canonical_owner(self):
        from terminan.strategy_catalog import research_strategy_catalog, StrategyAvailability
        catalog = research_strategy_catalog()
        by_id = {item.id: item for item in catalog}
        self.assertEqual(len(by_id), len(catalog))
        self.assertEqual(set(by_id), {row[1] for row in TRANSFER})
        self.assertEqual(len({row[0] for row in TRANSFER}), 8)
        for legacy, canonical, implemented, setup in TRANSFER:
            with self.subTest(legacy=legacy):
                entry = by_id[canonical]
                self.assertEqual(entry.setup, setup)
                self.assertEqual(entry.generator is not None, implemented)
                self.assertIs(entry.availability, (
                    StrategyAvailability.RESEARCH_GENERATOR if implemented
                    else StrategyAvailability.SPECIFICATION_ONLY))
                self.assertIs(entry.execution_authority, False)
                self.assertIs(entry.trading_authorized, False)
                self.assertEqual(entry.source_authentication, "NOT_EVALUATED")

    def test_exact_four_callable_owners_without_dynamic_legacy_alias(self):
        from terminan.strategy_catalog import research_strategy
        from terminan.strategy_entries import (
            generate_sweep_reclaim_entries, generate_breakout_retest_entries,
            generate_profile_reclaim_entries,
        )
        from terminan.continuation_strategy import generate_continuation_entries
        owners = {
            "sweep_reclaim_v2": generate_sweep_reclaim_entries,
            "breakout_retest_v2": generate_breakout_retest_entries,
            "profile_reclaim_v2": generate_profile_reclaim_entries,
            "volatility_continuation_v2": generate_continuation_entries,
        }
        for legacy, canonical, implemented, _ in TRANSFER:
            with self.subTest(legacy=legacy):
                self.assertIs(research_strategy(canonical).generator, owners.get(canonical))
                with self.assertRaises(ValueError):
                    research_strategy(legacy)
        self.assertEqual(sum(row[2] for row in TRANSFER), 4)

    def test_discovery_is_not_an_execution_or_external_loader(self):
        # A static guard deliberately examines the checked-in canonical
        # implementation instead of executing foreign source code.
        root = Path(__file__).resolve().parents[1] / "terminan"
        source = (root / "strategy_catalog.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [item.name for item in node.names] if isinstance(node, ast.Import) else [node.module or ""]
                self.assertFalse(any("strattester" in name or "meta_analyse" in name for name in names))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(node.func.id, ("eval", "exec", "__import__"))
        from terminan.strategy_catalog import research_strategy_catalog
        self.assertEqual(len(research_strategy_catalog()), 8)

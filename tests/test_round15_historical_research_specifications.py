"""ROUND 15: actual historical STRATTESTER spec discovery/custody parity.

Archive modules are exact copies of source blobs; import in this isolated test
only, never via the application. Runtime exposes only immutable, spec-only
Terminan descriptors; it does not import legacy modules or create trade grants.
"""
import hashlib
import importlib
import sys
import unittest
from collections import Counter
from pathlib import Path

from terminan.strategy_catalog import (
    historical_strategy_specifications, research_strategy_catalog,
)
from terminan.historical_research_specifications import (
    historical_research_family, historical_research_specification,
)


_ARCHIVE = Path(__file__).resolve().parent / "fixtures" / "d_round13_strattester"
_SOURCE = {
    "research_common.py": "27665b18590ef56d31e680d43d0bac9b318a8e03",
    "research_levels.py": "ba5a60c867fc0fc6f715a966b1a6ccfbb2ed19d5",
    "research_poc.py": "e1ceb266f1c342504e21a87bad0b267127f63e90",
    "research_volatility.py": "f28ef49806456f6e79481559b1a70c74f08d41d8",
    "research_smc.py": "ddaa04c19a3e4aa703fdb8fafc6ef8034d199ac2",
}
_ORIGINAL_FUNCTIONS = (
    ("research_levels", "level_hypotheses"),
    ("research_poc", "poc_hypotheses"),
    ("research_volatility", "volatility_hypotheses"),
    ("research_smc", "smc_hypotheses"),
)


def _git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii")
                        + b"\0" + raw).hexdigest()


def _original():
    root = str(_ARCHIVE.parent)
    if root not in sys.path:
        sys.path.insert(0, root)
    records = []
    for filename, function in _ORIGINAL_FUNCTIONS:
        module = importlib.import_module("d_round13_strattester." + filename)
        records.extend(getattr(module, function)())
    return tuple(records)


class HistoricalResearchSpecificationsRound15(unittest.TestCase):
    def test_frozen_archive_exact_git_blob_identity(self):
        for filename, blob in _SOURCE.items():
            with self.subTest(filename=filename):
                self.assertEqual(_git_blob((_ARCHIVE / filename).read_bytes()),
                                 blob)

    def test_twenty_historical_specs_equal_actual_original_functions(self):
        original = _original()
        modern = historical_strategy_specifications()
        self.assertEqual(len(original), 20)
        self.assertEqual(len(modern), 20)
        self.assertEqual(len(set(row.name for row in modern)), 20)
        self.assertEqual(
            Counter(row.family for row in modern),
            Counter(levels=5, poc=4, volatility=3, smc=6, orderflow=2))
        self.assertEqual(
            tuple((x.name, x.family, dict(x.params), x.control,
                   x.execution_status, x.signal_generator) for x in modern),
            tuple((x.name, x.family, dict(x.params), x.control,
                   x.execution_status, x.signal_generator) for x in original))
        for current in modern:
            with self.subTest(name=current.name):
                self.assertTrue(current.source_path.startswith(
                    "strattester/strategies/builtin/"))
                self.assertEqual(current.source_git_blob,
                                 _SOURCE[current.source_path.rsplit("/", 1)[-1]])
                self.assertEqual(current.source_commit,
                                 "37ff7e9d12a4d2dccd788fc493c28557dbe8bcea")
                self.assertEqual(current.execution_status, "SPEC_ONLY")
                self.assertIsNone(current.signal_generator)
                self.assertIs(current.source_authentication, "NOT_EVALUATED")
                self.assertIs(current.execution_authority, False)
                self.assertIs(current.trading_authorized, False)

    def test_no_legacy_migration_changes_eight_canonical_scalp_entries(self):
        existing = research_strategy_catalog()
        self.assertEqual(len(existing), 8)
        self.assertEqual(sum(row.generator is not None for row in existing), 4)
        self.assertFalse(set(row.id for row in existing)
                         & set(row.name for row in historical_strategy_specifications()))
        self.assertEqual(
            {x.name for x in historical_strategy_specifications() if x.control},
            {"LEVEL_BASE", "SMC_CONTROL_MOMENTUM"})

    def test_immutable_metadata_detached_across_calls(self):
        first = historical_research_specification("ORDERFLOW_ABSORPTION_PROXY")
        second = historical_research_specification("ORDERFLOW_ABSORPTION_PROXY")
        self.assertIsNot(first, second)
        self.assertIsNot(first.params, second.params)
        self.assertEqual(first.params["entry_parts"], (0.5, 0.5))
        self.assertEqual(first.params["tp_parts"], (0.6, 0.4))
        self.assertEqual(first.params["requires"],
                         ("public_trade_aggregates", "level",
                          "cvd", "aggression_decay"))
        with self.assertRaises(TypeError):
            first.params["entry_parts"] = (1.0,)
        with self.assertRaises((AttributeError, TypeError)):
            first.execution_authority = True

    def test_name_and_family_lookup_closed_and_never_executable(self):
        for name in ("LEVEL_BASE", "SMC_OB_FVG", "POC_MIGRATION",
                     "VOL_EXHAUSTION", "ORDERFLOW_SWEEP_REVERSAL"):
            obj = historical_research_specification(name)
            self.assertEqual(obj.name, name)
            self.assertFalse(obj.execution_authority)
        self.assertEqual(len(historical_research_family("smc")), 6)
        self.assertEqual(len(historical_research_family("orderflow")), 2)
        for name in (None, True, 0, "SCALP_SWEEP_RECLAIM",
                     "__import__('os')", "not known"):
            with self.assertRaises(ValueError):
                historical_research_specification(name)
        for family in ("scalp", "unknown", "SMC", 0, True):
            with self.assertRaises(ValueError):
                historical_research_family(family)


if __name__ == "__main__":
    unittest.main()

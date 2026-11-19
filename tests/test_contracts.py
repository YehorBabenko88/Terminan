"""Terminan contract and pinned Strattester metadata migration regression tests.

Legacy source: strattester@37ff7e9d12a4d2dccd788fc493c28557dbe8bcea
"""
import ast
import hashlib
import inspect
import json
from pathlib import Path
import unittest
from enum import Enum

from terminan.contracts import (
    DataRequirement, HypothesisSpec, StrategyDefinition, StrategyRegistry,
    TradeEvent, aggregate_footprint, align_trades, executable_hypotheses,
    poc_close_events, strategy_fingerprint,
)

class ContractTests(unittest.TestCase):
    def test_trade_validation(self):
        base=dict(run_id='r',strategy_id='s',symbol='BTCUSDT',trade_id='t',entry_ms=100,exit_ms=200,entry_price=10,exit_price=12,side='long',quantity=2,pnl=4)
        t=TradeEvent.parse(base)
        self.assertEqual(align_trades([t],150,160),[t])
        with self.assertRaises(ValueError):TradeEvent.parse({**base,'exit_ms':99})
        with self.assertRaises(ValueError):TradeEvent.parse({**base,'side':'other'})
    def test_poc_tie_and_close(self):
        rows=[dict(t=100,price=11,volume=5),dict(t=100,price=10,volume=5),dict(t=200,price=9,volume=8)]
        buckets=aggregate_footprint(rows)
        self.assertEqual(buckets[0]['poc'],10)
        events=poc_close_events(buckets,[dict(t=100,c=11),dict(t=200,c=9)])
        self.assertEqual([e['relation'] for e in events],['above','at'])
    def test_no_negative_volume(self):
        with self.assertRaises(ValueError):aggregate_footprint([dict(t=1,price=2,volume=-1)])

class StrategyMigrationTests(unittest.TestCase):
    """Preserve Strattester registry/spec behavior without starting a worker."""

    @staticmethod
    def definition(version='1'):
        class NoOp:
            pass
        return StrategyDefinition(
            'example', version, (DataRequirement('candles', ('1m',)),), NoOp,
        )

    def test_duplicate_registration_and_fingerprint_stability(self):
        registry = StrategyRegistry()
        registry.register(self.definition())
        with self.assertRaises(ValueError):
            registry.register(self.definition())
        initial = strategy_fingerprint(registry.discover()[0])
        registry.set_enabled('example', '1', False)
        self.assertEqual(initial, strategy_fingerprint(registry.discover()[0]))
        self.assertFalse(registry.discover()[0].enabled)
        self.assertNotEqual(initial, strategy_fingerprint(self.definition('2')))

    def test_invalid_dataset_fails_closed(self):
        with self.assertRaises(ValueError):
            DataRequirement('future_unknown_data')
        self.assertEqual(DataRequirement('open_interest').dataset, 'open_interest')

    def test_spec_only_never_becomes_executable(self):
        planned = HypothesisSpec('poc', 'poc', {'setup': 'retest'})
        executable = HypothesisSpec(
            'explicit', 'levels', {}, execution_status='EXECUTABLE',
            signal_generator='reviewed-v1',
        )
        self.assertEqual(executable_hypotheses([planned, executable]), (executable,))
        with self.assertRaises(ValueError):
            HypothesisSpec('unsafe', 'levels', {}, execution_status='EXECUTABLE')


class LegacyDatasetKind(str, Enum):
    CANDLES = "candles"

class Candidate:
    def run(self, candles, checkpoint=None):
        return []

def definition(version="1"):
    return StrategyDefinition(
        "sample", version, (DataRequirement("candles", ("1m",)),), Candidate
    )

def original_fingerprint(definition):
    # Direct independent copy of the original fingerprint's serialization.
    try:
        source = inspect.getsource(definition.implementation)
    except (OSError, TypeError):
        source = (
            f"{definition.implementation.__module__}."
            f"{definition.implementation.__qualname__}"
        )
    payload = {
        "id": definition.id,
        "version": definition.version,
        "requirements": [
            (r.dataset, r.timeframes, r.required) for r in definition.requirements
        ],
        "impl": (
            f"{definition.implementation.__module__}."
            f"{definition.implementation.__qualname__}"
        ),
        "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "feature_versions": definition.feature_versions,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

class StrategyLegacyParityTests(unittest.TestCase):
    def test_duplicate_rejected_and_order(self):
        reg = StrategyRegistry()
        reg.register(definition("1"))
        reg.register(definition("2"))
        self.assertEqual([d.version for d in reg.discover()], ["1", "2"])
        with self.assertRaises(ValueError):
            reg.register(definition("1"))

    def test_enable_preserves_fingerprint(self):
        reg = StrategyRegistry()
        reg.register(definition())
        before = strategy_fingerprint(reg.discover()[0])
        reg.set_enabled("sample", "1", False)
        self.assertFalse(reg.discover()[0].enabled)
        self.assertEqual(before, strategy_fingerprint(reg.discover()[0]))
        with self.assertRaises(KeyError):
            reg.set_enabled("unknown", "1", True)

    def test_legacy_fingerprint_wire_parity(self):
        a = definition()
        self.assertEqual(strategy_fingerprint(a), original_fingerprint(a))
        self.assertNotEqual(strategy_fingerprint(a), strategy_fingerprint(definition("2")))
        self.assertEqual(DataRequirement(LegacyDatasetKind.CANDLES).dataset, "candles")

    def test_invalid_inputs_fail_closed(self):
        with self.assertRaises(ValueError):
            DataRequirement("secret_exchange_provider")
        with self.assertRaises(ValueError):
            DataRequirement("candles", ["1m"])
        with self.assertRaises(ValueError):
            StrategyDefinition("", "1", (), Candidate)
        with self.assertRaises(ValueError):
            StrategyDefinition("a", "1", (), lambda: None)
        with self.assertRaises(ValueError):
            StrategyDefinition("a", "1", (), Candidate, enabled=1)
        with self.assertRaises(TypeError):
            StrategyRegistry().register({"id": "a"})

    def test_registration_never_executes_strategy(self):
        class Dangerous:
            def __init__(self):
                raise AssertionError("strategy instantiated")
        reg = StrategyRegistry()
        reg.register(StrategyDefinition("inert", "1", (), Dangerous))
        self.assertEqual(len(reg.discover()), 1)



class SingleRegistryImportContractTests(unittest.TestCase):
    """Prevent future PR #87/#88 conflicts without adding another registry."""

    @staticmethod
    def _sources():
        root = Path(__file__).resolve().parents[1] / "terminan"
        return {
            path: ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for path in root.rglob("*.py")
        }

    def test_one_canonical_registry_definition(self):
        sources = self._sources()
        definitions = [
            (path.name, node.name)
            for path, tree in sources.items()
            for node in ast.walk(tree)
            if isinstance(node, (ast.ClassDef, ast.FunctionDef))
            and node.name in ("StrategyRegistry", "StrategyDefinition",
                              "DataRequirement", "strategy_fingerprint")
        ]
        for name in ("StrategyRegistry", "StrategyDefinition",
                     "DataRequirement", "strategy_fingerprint"):
            self.assertEqual(
                [filename for filename, found in definitions if found == name],
                ["contracts.py"],
                f"duplicate or missing canonical strategy symbol {name}",
            )
        self.assertNotIn("strategies.py", [path.name for path in sources])

    def test_no_old_strategy_module_imports(self):
        for path, tree in self._sources().items():
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertNotEqual(alias.name, "terminan.strategies",
                                            str(path))
                if isinstance(node, ast.ImportFrom):
                    self.assertNotEqual(node.module, "terminan.strategies",
                                        str(path))
                    if node.level and node.module == "strategies":
                        self.fail(f"obsolete relative strategies import: {path}")
                if isinstance(node, ast.ImportFrom) and node.module == "terminan":
                    self.assertNotIn(
                        "strategies", [alias.name for alias in node.names],
                        str(path),
                    )

    def test_public_registry_identity_same_contract_module(self):
        import terminan.contracts as api
        self.assertIs(StrategyRegistry, api.StrategyRegistry)
        self.assertIs(StrategyDefinition, api.StrategyDefinition)
        self.assertIs(DataRequirement, api.DataRequirement)
        self.assertIs(strategy_fingerprint, api.strategy_fingerprint)

class SingleStrategyRegistryImportContractTests(unittest.TestCase):
    """Fail closed if a second registry or stale import reappears."""

    def test_strategy_types_have_one_canonical_definition(self):
        import ast
        from pathlib import Path

        package = Path(__file__).resolve().parents[1] / "terminan"
        owned = {
            "DataRequirement",
            "StrategyDefinition",
            "StrategyRegistry",
            "HypothesisSpec",
        }
        declarations = {name: [] for name in owned}
        for path in sorted(package.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in tree.body:
                if isinstance(node, ast.ClassDef) and node.name in owned:
                    declarations[node.name].append(path.name)
        self.assertEqual(
            declarations,
            {name: ["contracts.py"] for name in owned},
            "Only terminan.contracts may define strategy registry contracts",
        )

    def test_no_stale_strategy_registry_imports(self):
        import ast
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        for folder in ("terminan", "tests"):
            for path in sorted((root / folder).rglob("*.py")):
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        old = node.module == "terminan.strategies" or (
                            node.level == 1 and node.module == "strategies"
                            and folder == "terminan"
                        )
                        self.assertFalse(old, f"Stale strategy import in {path}")
                    elif isinstance(node, ast.Import):
                        self.assertFalse(
                            any(alias.name == "terminan.strategies" for alias in node.names),
                            f"Stale strategy import in {path}",
                        )

    def test_runtime_types_resolve_to_canonical_module(self):
        from terminan.contracts import (
            DataRequirement, HypothesisSpec, StrategyDefinition, StrategyRegistry,
        )

        for symbol in (DataRequirement, HypothesisSpec, StrategyDefinition, StrategyRegistry):
            self.assertEqual(symbol.__module__, "terminan.contracts")


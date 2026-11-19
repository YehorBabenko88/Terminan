"""Terminan contract and pinned Strattester metadata migration regression tests.

Legacy source: strattester@37ff7e9d12a4d2dccd788fc493c28557dbe8bcea
"""
import ast
from dataclasses import asdict
from decimal import localcontext
import hashlib
import inspect
import json
from math import copysign
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

    def test_trade_admission_rejects_nonfinite_and_wrong_types(self):
        row = dict(run_id='r', strategy_id='s', symbol='BTCUSDT', trade_id='t',
                   entry_ms=100, exit_ms=200, entry_price=10, exit_price=12,
                   side='long', quantity=2, pnl=-4)
        self.assertEqual(json.loads(json.dumps(asdict(TradeEvent.parse(row)),
                                               allow_nan=False)), row)
        for field in ('entry_price', 'exit_price', 'quantity', 'pnl'):
            for invalid in (float('nan'), float('inf'), float('-inf'), True, '12', 10**1000):
                with self.subTest(field=field, invalid=type(invalid)):
                    with self.assertRaises(ValueError):
                        TradeEvent.parse(dict(row, **{field: invalid}))
        for field, invalid in (('entry_ms', True), ('entry_ms', -1), ('exit_ms', 200.0),
                               ('exit_price', 0), ('symbol', 'BTC / USDT'),
                               ('exit_price', None)):
            with self.subTest(field=field, invalid=invalid):
                with self.assertRaises(ValueError):
                    TradeEvent(**dict(row, **{field: invalid}))
        self.assertIsNone(TradeEvent.parse(dict(row, exit_ms=None, exit_price=None)).exit_ms)

    def test_legacy_poc_admission_rejects_nonfinite_observations(self):
        for invalid in (float('nan'), float('inf'), float('-inf'), 'NaN', 'Infinity'):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    aggregate_footprint([dict(t=1, price=invalid, volume=1)])
                with self.assertRaises(ValueError):
                    aggregate_footprint([dict(t=1, price=1, volume=invalid)])
                with self.assertRaises(ValueError):
                    poc_close_events([dict(t=1, poc=1)], [dict(t=1, c=invalid)])
                with self.assertRaises(ValueError):
                    poc_close_events([dict(t=1, poc=invalid)], [dict(t=1, c=1)])
    def test_poc_tie_and_close(self):
        rows=[dict(t=100,price=11,volume=5),dict(t=100,price=10,volume=5),dict(t=200,price=9,volume=8)]
        buckets=aggregate_footprint(rows)
        self.assertEqual(buckets[0]['poc'],10)
        events=poc_close_events(buckets,[dict(t=100,c=11),dict(t=200,c=9)])
        self.assertEqual([e['relation'] for e in events],['above','at'])
    def test_no_negative_volume(self):
        with self.assertRaises(ValueError):aggregate_footprint([dict(t=1,price=2,volume=-1)])

    def test_poc_math_sdk_preserves_duplicate_price_policy(self):
        rows = [dict(t=100, price=10, volume=4), dict(t=100, price=10, volume=4),
                dict(t=100, price=11, volume=6)]
        self.assertEqual(aggregate_footprint(rows),
                         [dict(t=100, levels=rows, poc=11.0, poc_volume=6.0)])

    def test_poc_ranking_does_not_round_with_callers_decimal_context(self):
        rows = [dict(t=100, price=10, volume=1001), dict(t=100, price=20, volume=1002)]
        with localcontext() as context:
            context.prec = 2
            self.assertEqual(aggregate_footprint(rows)[0]['poc'], 20.0)

    def test_poc_retains_first_volume_encoding_on_equal_rows(self):
        rows = [dict(t=100, price=10, volume=-0.0), dict(t=100, price=10, volume=0)]
        self.assertEqual(copysign(1, aggregate_footprint(rows)[0]['poc_volume']), -1.0)

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


class FourModuleBoundaryTests(unittest.TestCase):
    """Terminan is a consumer; Bybit/PG bootstrap control belongs elsewhere."""

    def test_no_independent_bybit_transport_or_postgres_provisioning(self):
        root = Path(__file__).resolve().parents[1] / "terminan"
        forbidden_modules = (
            "pybit", "bybit", "websockets", "websocket",
            "ccxt", "asyncpg",
        )
        forbidden_calls = {
            "initdb", "pg_ctl", "createdb", "create_database",
            "create_cluster", "launch_bybit",
        }
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    names = ([alias.name for alias in node.names]
                             if isinstance(node, ast.Import) else
                             [node.module or ""])
                    for name in names:
                        self.assertFalse(
                            any(name == bad or name.startswith(bad + ".")
                                for bad in forbidden_modules),
                            f"forbidden provider import {name} in {path}",
                        )
                if isinstance(node, ast.Call):
                    called = node.func
                    function = (called.id if isinstance(called, ast.Name)
                                else called.attr if isinstance(called, ast.Attribute)
                                else "")
                    self.assertNotIn(function, forbidden_calls, str(path))

    def test_pg_legacy_adapter_is_explicitly_read_only(self):
        from terminan import data
        source = inspect.getsource(data.grid_query)
        self.assertIn("default_transaction_read_only=on", source)
        self.assertIn("statement_timeout=3000", source)
        self.assertNotIn("autocommit=True", source)

    def test_math_sdk_is_optional_and_no_strategy_code_lives_in_math(self):
        from terminan.paper import PaperEngine
        self.assertEqual(PaperEngine.__module__, "terminan.paper")
        self.assertFalse(PaperEngine().enabled)
        from terminan import paper
        source = inspect.getsource(paper)
        self.assertIn("from market_compute_api import compute_batch", source)
        self.assertNotIn("def volume_profile_poc(", source)
        self.assertNotIn("class Bybit", source)

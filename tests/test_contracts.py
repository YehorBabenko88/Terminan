import unittest
from terminan.contracts import TradeEvent, align_trades, aggregate_footprint, poc_close_events

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
        from terminan.contracts import StrategyDefinition, DataRequirement
        class NoOp:
            pass
        return StrategyDefinition(
            'example', version, (DataRequirement('candles', ('1m',)),), NoOp,
        )

    def test_duplicate_registration_and_fingerprint_stability(self):
        from terminan.contracts import StrategyRegistry, strategy_fingerprint
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
        from terminan.contracts import DataRequirement
        with self.assertRaises(ValueError):
            DataRequirement('future_unknown_data')
        self.assertEqual(DataRequirement('open_interest').dataset, 'open_interest')

    def test_spec_only_never_becomes_executable(self):
        from terminan.contracts import HypothesisSpec, executable_hypotheses
        planned = HypothesisSpec('poc', 'poc', {'setup': 'retest'})
        executable = HypothesisSpec(
            'explicit', 'levels', {}, execution_status='EXECUTABLE',
            signal_generator='reviewed-v1',
        )
        self.assertEqual(executable_hypotheses([planned, executable]), (executable,))
        with self.assertRaises(ValueError):
            HypothesisSpec('unsafe', 'levels', {}, execution_status='EXECUTABLE')




"""Strattester-to-Terminan strategy registry migration regressions.

Legacy source: strattester@37ff7e9d12a4d2dccd788fc493c28557dbe8bcea
(strategies/base.py, registry.py, marketdata/datasets.py).
"""
import hashlib
import inspect
import json
import unittest
from enum import Enum

from terminan.contracts import (
    DataRequirement, StrategyDefinition, StrategyRegistry, strategy_fingerprint,
)

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


"""Strattester-to-Terminan strategy registry migration regressions.

Legacy source: strattester@37ff7e9d12a4d2dccd788fc493c28557dbe8bcea
(strategies/base.py, registry.py, marketdata/datasets.py).
"""
import hashlib
import inspect
import json
import unittest
from enum import Enum

from terminan.strategies import (
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

class StrategyMigrationTests(unittest.TestCase):
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

if __name__ == "__main__":
    unittest.main()

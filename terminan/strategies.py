"""Strategy definition and registry migrated from Strattester (no execution or orders).

Preserves Strattester's strategy_fingerprint wire payload for compatible
definitions. Canonical data remains Grid's; domain calculations remain Math's.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import inspect
import json
from typing import Protocol

_DATASETS = frozenset({
    "candles", "mark_price", "index_price", "premium_index", "open_interest",
    "funding", "long_short_ratio", "public_trades", "public_trade_aggregates",
    "orderbook_l2", "liquidations",
})

@dataclass(frozen=True)
class DataRequirement:
    dataset: str
    timeframes: tuple[str, ...] = ()
    required: bool = True

    def __post_init__(self) -> None:
        value = self.dataset.value if isinstance(self.dataset, Enum) else self.dataset
        if not isinstance(value, str) or value not in _DATASETS:
            raise ValueError("unsupported dataset")
        object.__setattr__(self, "dataset", value)
        if not isinstance(self.timeframes, tuple) or any(
            not isinstance(tf, str) or not tf for tf in self.timeframes
        ):
            raise ValueError("invalid timeframes")
        if type(self.required) is not bool:
            raise ValueError("required must be boolean")

@dataclass(frozen=True)
class StrategyDefinition:
    id: str
    version: str
    requirements: tuple[DataRequirement, ...]
    implementation: type
    enabled: bool = True
    feature_versions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("strategy id required")
        if not isinstance(self.version, str) or not self.version.strip():
            raise ValueError("strategy version required")
        if not isinstance(self.requirements, tuple) or any(
            not isinstance(item, DataRequirement) for item in self.requirements
        ):
            raise ValueError("invalid strategy data requirements")
        if not isinstance(self.implementation, type):
            raise ValueError("implementation must be a class")
        if type(self.enabled) is not bool:
            raise ValueError("enabled must be boolean")
        if not isinstance(self.feature_versions, tuple) or any(
            not isinstance(v, str) or not v for v in self.feature_versions
        ):
            raise ValueError("invalid feature versions")

def strategy_fingerprint(definition: StrategyDefinition) -> str:
    """Preserve original Strattester fingerprint payload and hash algorithm."""
    try:
        source = inspect.getsource(definition.implementation)
    except (OSError, TypeError):
        source = f"{definition.implementation.__module__}.{definition.implementation.__qualname__}"
    payload = {
        "id": definition.id,
        "version": definition.version,
        "requirements": [
            (r.dataset, r.timeframes, r.required) for r in definition.requirements
        ],
        "impl": f"{definition.implementation.__module__}.{definition.implementation.__qualname__}",
        "source_sha256": sha256(source.encode()).hexdigest(),
        "feature_versions": definition.feature_versions,
    }
    return sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

class Strategy(Protocol):
    id: str
    version: str
    requirements: tuple[DataRequirement, ...]
    def run(self, candles, checkpoint=None): ...

class StrategyRegistry:
    """Catalog only; does not instantiate, execute, persist or submit orders."""
    def __init__(self) -> None:
        self._items: dict[tuple[str, str], StrategyDefinition] = {}

    def register(self, definition: StrategyDefinition) -> None:
        if not isinstance(definition, StrategyDefinition):
            raise TypeError("strategy definition required")
        key = (definition.id, definition.version)
        if key in self._items:
            raise ValueError(f"duplicate strategy {key}")
        self._items[key] = definition

    def discover(self) -> list[StrategyDefinition]:
        return list(self._items.values())

    def set_enabled(self, strategy_id: str, version: str, enabled: bool) -> None:
        if type(enabled) is not bool:
            raise ValueError("enabled must be boolean")
        old = self._items[(strategy_id, version)]
        self._items[(strategy_id, version)] = StrategyDefinition(
            old.id, old.version, old.requirements, old.implementation,
            enabled, old.feature_versions,
        )

"""MetaScalp compatibility and conservative ownership-parity regressions.

Original source: meta_analyse@b49505da42a274f7232fabe5d847c91f7218a0ce
  src/meta_analyse/level_sync.py / level_publish.py / crossing_quality.py
The source oracle below repeats the old published expressions but no Meta
package, Qt desktop or Bybit client is imported or executed.
"""
import hashlib
import unittest
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from terminan.metascalp_levels import (
    PREFIX, crossed_owned_ids, owned_id, parse_rows, publication_decision,
    signature,
)

@dataclass(frozen=True)
class Level:
    timeframe: str
    kind: str
    source_start: datetime
    price: Decimal

@dataclass(frozen=True)
class Report:
    levels: tuple
    verified: bool
    reason: str = "unverified"

class MetaScalpMigrationTests(unittest.TestCase):
    def setUp(self):
        self.level = Level("H1", "high",
                           datetime(2026, 11, 19, tzinfo=timezone.utc),
                           Decimal("73100.25"))

    def test_source_signature_unchanged_for_owned_levels(self):
        raw = (f"BTCUSDT|{self.level.timeframe}|{self.level.kind}|"
               f"{self.level.source_start.isoformat()}|{self.level.price}")
        self.assertEqual(signature("BTCUSDT", self.level),
                         hashlib.sha256(raw.encode()).hexdigest()[:24])
        self.assertEqual(len(signature("BTCUSDT", self.level)), 24)

    def test_preserve_legacy_owner_and_parse_wrappers(self):
        note = PREFIX + signature("BTCUSDT", self.level)
        self.assertEqual(owned_id({"Note": note, "Id": "42"}), 42)
        self.assertIsNone(owned_id({"Note": "user:manual", "Id": 99}))
        self.assertIsNone(owned_id({"Note": "", "Id": 88}))
        self.assertEqual(parse_rows({"data": [{"id": 1}]}), [{"id": 1}])
        with self.assertRaises(ValueError):
            parse_rows({"unrecognized": [{"id": 1}]})

    def test_publication_gates_match_meta_source_order(self):
        report = Report((self.level,), True, "verified")
        self.assertEqual(
            publication_decision(report, connection_verified=False,
                                 instrument_verified=True).reason,
            "terminal connection not verified",
        )
        self.assertEqual(
            publication_decision(report, connection_verified=True,
                                 instrument_verified=False).reason,
            "instrument mapping not verified",
        )
        self.assertFalse(publication_decision(Report((), False, "gap"),
                                             connection_verified=True,
                                             instrument_verified=True).allowed)
        result = publication_decision(report, connection_verified=True,
                                      instrument_verified=True)
        self.assertTrue(result.allowed)
        self.assertEqual(result.count, 1)
        self.assertFalse(publication_decision(
            Report((Level("H1", "low", self.level.source_start, Decimal("0")),),
                   True),
            connection_verified=True, instrument_verified=True).allowed)
        self.assertFalse(publication_decision(
            Report((self.level, self.level), True),
            connection_verified=True, instrument_verified=True,
            max_levels=1).allowed)

    def test_no_unverified_crossing_or_other_user_levels(self):
        rows = [
            {"id": 1, "note": "manual", "price": "100"},
            {"id": 2, "note": PREFIX + "valid", "price": "100"},
            {"id": 3, "note": PREFIX + "valid2", "price": "101"},
        ]
        for kw in (
            {"contiguous": False, "source": "exchange_execution"},
            {"contiguous": True, "source": "unknown"},
            {"contiguous": True, "source": "orderbook_snapshot"},
        ):
            self.assertEqual(crossed_owned_ids(rows, "99", "102", **kw), ())
        self.assertEqual(
            crossed_owned_ids(rows, "99", "100.5", contiguous=True,
                              source="exchange_execution"),
            (2,),
        )

    def test_reject_invalid_or_nonfinite_crossing_price(self):
        owned = [{"id": 1, "note": PREFIX + "x", "price": "NaN"}]
        with self.assertRaises(ValueError):
            crossed_owned_ids(owned, "99", "102", contiguous=True,
                              source="exchange_execution")
        self.assertEqual(
            crossed_owned_ids(owned, "-1", "102", contiguous=True,
                              source="exchange_execution"),
            (),
        )

    def test_no_terminal_write_or_network_function(self):
        import ast
        import inspect
        import terminan.metascalp_levels as module
        tree = ast.parse(inspect.getsource(module))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names.update(
                    alias.name for alias in node.names
                )
        self.assertFalse(any("httpx" in n or "socket" in n or "psycopg" in n
                             for n in names))
        self.assertFalse(hasattr(module, "LevelSync"))

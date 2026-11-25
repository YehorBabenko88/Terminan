"""Differential proof: Meta's original PaperEngine vs the canonical Terminan engine.

The Meta engine is loaded from a FROZEN byte copy
(tests/fixtures/meta_paper_engine_b1a4d6a.py, provenance in its docstring:
meta_analyse@b1a4d6a41054f0040a88dc80b585380fb6b4f323 src/meta_analyse/core.py).
Both engines receive the identical synthetic event sequence (closed minutes with
an externally supplied POC, then trades) and every return value plus the full
observable state (reference, positions, fills) must be identical after every
event, for many seeded random sequences and engine policies.

Documented differences (Terminan is stricter / fail-closed; Meta accepted input
that cannot occur from a valid ordered feed). They are asserted explicitly below
so that any change on either side is visible:
  D1 out-of-order trade time       Meta: accepted silently; Terminan: ValueError
  D2 out-of-order closed minute     Meta: overwrites reference; Terminan: ValueError
  D3 minute start not on a minute   Meta: stores, never enters; Terminan: ValueError
  D4 non-positive POC               Meta: stores, never enters; Terminan: ValueError
  D5 stop_pct >= 1 (stop <= 0 long) Meta: opens a position with stop <= 0;
                                    Terminan: ValueError('positive paper stop required')
  D6 ambient decimal context        Meta: uses the caller's thread context;
                                    Terminan: fixed 28-digit HALF_EVEN (= Meta under
                                    the default context, the only runtime context)
No Meta behaviour on valid ordered input differs, so nothing needs porting.
"""
import ast
import decimal
import hashlib
import importlib.util
import random
import sys
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from pathlib import Path

from terminan.paper import ClosedMinute, ExecutionTrade, PaperEngine

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "meta_paper_engine_b1a4d6a.py"
T0 = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)
SYMBOLS = ("BTCUSDT", "ETHUSDT")


def _load_meta():
    spec = importlib.util.spec_from_file_location("meta_paper_reference_b1a4d6a", FIXTURE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve annotations via sys.modules
    spec.loader.exec_module(module)
    return module


META = _load_meta()


class _MetaMinute:
    """Only the attributes Meta's PaperEngine reads from its Minute object."""

    def __init__(self, start, poc, complete):
        self.start, self.poc, self.complete = start, poc, complete


class _MetaTrade:
    """Only the attributes Meta's PaperEngine reads from its Trade object."""

    def __init__(self, symbol, time, price):
        self.symbol, self.time, self.price = symbol, time, price


FILL_FIELDS = ("symbol", "side", "entry", "exit", "reason", "gross", "fees", "net", "exit_time")
POSITION_FIELDS = ("symbol", "side", "entry", "target", "stop", "size", "entry_time", "entry_fee")


def _fill(value):
    return None if value is None else tuple(getattr(value, name) for name in FILL_FIELDS)


def _state(engine):
    return (
        dict(engine.reference),
        {k: tuple(getattr(v, n) for n in POSITION_FIELDS) for k, v in engine.positions.items()},
        [_fill(f) for f in engine.fills],
        engine.enabled,
    )


POLICIES = {
    "notional": ("100", "37.5", "1000", "0.01"),
    "threshold": ("0", "0.001", "0.015", "0.05"),
    "stop_pct": ("0", "0.005", "0.02", "0.5"),
    "fee_rate": ("0", "0.0006", "0.001"),
    "slippage_bps": ("0", "2", "15.5", "100"),
}


def _price(rng, poc, spread):
    move = D(rng.randint(-spread, spread)) / D(1000)
    value = (poc * (D(1) + move)).quantize(D("0.01"))
    return value if value > 0 else D("0.01")


def _events(rng):
    """Globally time-ordered synthetic feed.

    Minute k closes at k+1 (before trades stamped k+1); trades are spread over
    the following two minutes, so some are next-minute and some are stale.
    """
    rows = []
    pocs = {s: D(rng.choice(("100", "2500.5", "0.123", "64000"))) for s in SYMBOLS}
    for k in range(rng.randint(5, 40)):
        start = T0 + timedelta(minutes=k)
        for symbol in SYMBOLS:
            pocs[symbol] = _price(rng, pocs[symbol], 10)
            if rng.random() < 0.8:  # sometimes no closed minute -> no next-minute entry
                rows.append((start + timedelta(minutes=1), 0, len(rows),
                             ("minute", symbol, start, pocs[symbol], rng.random() < 0.85)))
            for _ in range(rng.randint(0, 6)):
                when = start + timedelta(minutes=1, seconds=rng.randint(0, 119),
                                         microseconds=rng.choice((0, 1, 999999)))
                rows.append((when, 1, len(rows),
                             ("trade", symbol, when, _price(rng, pocs[symbol], 40))))
        if rng.random() < 0.05:
            rows.append((start + timedelta(minutes=1), 0, len(rows), ("toggle",)))
    rows.sort(key=lambda row: row[:3])
    return [row[3] for row in rows]


def _engines(policy):
    meta = META.PaperEngine(**{k: D(v) for k, v in policy.items()})
    term = PaperEngine(**{k: D(v) for k, v in policy.items()})
    meta.enabled = term.enabled = True
    return meta, term


class FrozenFixtureProvenanceTests(unittest.TestCase):
    def test_fixture_segments_are_byte_identical_to_recorded_meta_source(self):
        source = FIXTURE.read_text(encoding="utf-8")
        lines = source.splitlines(keepends=True)
        seen = {}
        for node in ast.parse(source).body:
            if getattr(node, "name", None) in META.SEGMENT_SHA256:
                first = (node.decorator_list[0].lineno if node.decorator_list else node.lineno) - 1
                seen[node.name] = hashlib.sha256(
                    "".join(lines[first:node.end_lineno]).encode("utf-8")).hexdigest()
        self.assertEqual(seen, META.SEGMENT_SHA256)
        self.assertEqual(set(seen), {"floor_minute", "Position", "PaperFill", "PaperEngine"})


class MetaTerminanPaperDifferentialTests(unittest.TestCase):
    CASES = 1500

    def _run(self, seed, policy):
        rng = random.Random(seed)
        meta, term = _engines(policy)
        counts = {"fills": 0, "entries": 0}
        with decimal.localcontext(decimal.Context()):  # Meta's runtime default context
            for event in _events(rng):
                if event[0] == "minute":
                    _, symbol, start, poc, complete = event
                    a = meta.on_closed_minute(symbol, _MetaMinute(start, poc, complete))
                    b = term.on_closed_minute(symbol, ClosedMinute(start, poc, complete))
                    self.assertEqual(a, b)
                elif event[0] == "trade":
                    _, symbol, when, price = event
                    had = symbol in meta.positions
                    a = meta.on_trade(_MetaTrade(symbol, when, price))
                    b = term.on_trade(ExecutionTrade(symbol, when, price))
                    self.assertEqual(_fill(a), _fill(b), (seed, event))
                    counts["fills"] += a is not None
                    counts["entries"] += (not had) and symbol in meta.positions
                else:
                    meta.enabled = term.enabled = not meta.enabled
                self.assertEqual(_state(meta), _state(term), (seed, policy, event))
        return counts

    def test_default_policy_identical_outcomes(self):
        policy = {k: v[0] if k != "threshold" else "0.015" for k, v in POLICIES.items()}
        policy.update(stop_pct="0.005", fee_rate="0.0006", slippage_bps="2")
        total = {"fills": 0, "entries": 0}
        for seed in range(self.CASES // 3):
            for key, value in self._run(seed, policy).items():
                total[key] += value
        # The generator must actually exercise entries, targets and stops.
        self.assertGreater(total["entries"], 100)
        self.assertGreater(total["fills"], 100)

    def test_random_policies_identical_outcomes(self):
        reasons = set()
        sides = set()
        for seed in range(10_000, 10_000 + self.CASES):
            rng = random.Random(seed * 7919)
            policy = {k: rng.choice(v) for k, v in POLICIES.items()}
            self._run(seed, policy)
        # Re-run a deterministic sample to collect coverage of both outcomes/sides.
        for seed in range(50):
            rng = random.Random(seed)
            meta, term = _engines({k: v[1] for k, v in POLICIES.items()})
            for event in _events(rng):
                if event[0] == "minute":
                    meta.on_closed_minute(event[1], _MetaMinute(*event[2:]))
                elif event[0] == "trade":
                    fill = meta.on_trade(_MetaTrade(*event[1:]))
                    if fill:
                        reasons.add(fill.reason)
                        sides.add(fill.side)
        self.assertEqual(reasons, {"target", "stop"})
        self.assertEqual(sides, {"long", "short"})

    def test_hand_vectors_identical(self):
        """Boundary vectors: exact threshold, entry==POC, equal-time trades, disabled."""
        poc = D("100")
        vectors = [
            [("trade", 60, "101.5")],                 # exactly +threshold -> short
            [("trade", 60, "98.5")],                  # exactly -threshold -> long
            [("trade", 60, "101.49")],                # inside band -> nothing
            [("trade", 59, "90")],                    # same minute -> nothing
            [("trade", 120, "90")],                   # minute k+2 -> nothing
            [("trade", 60, "90"), ("trade", 60, "100")],   # equal timestamps, target
            [("trade", 60, "90"), ("trade", 61, "89.5")],  # stop below stop level
            [("trade", 60, "110"), ("trade", 61, "200")],  # short stop gap
        ]
        for vector in vectors:
            meta, term = _engines({"notional": "100", "threshold": "0.015", "stop_pct": "0.005",
                                   "fee_rate": "0.0006", "slippage_bps": "2"})
            meta.on_closed_minute("BTCUSDT", _MetaMinute(T0, poc, True))
            term.on_closed_minute("BTCUSDT", ClosedMinute(T0, poc, True))
            for _, seconds, price in vector:
                when = T0 + timedelta(seconds=seconds)
                a = meta.on_trade(_MetaTrade("BTCUSDT", when, D(price)))
                b = term.on_trade(ExecutionTrade("BTCUSDT", when, D(price)))
                self.assertEqual(_fill(a), _fill(b), vector)
                self.assertEqual(_state(meta), _state(term), vector)
        # Zero threshold and zero slippage: entry == POC is skipped by both.
        meta, term = _engines({"notional": "100", "threshold": "0", "stop_pct": "0.005",
                               "fee_rate": "0", "slippage_bps": "0"})
        meta.on_closed_minute("X", _MetaMinute(T0, poc, True))
        term.on_closed_minute("X", ClosedMinute(T0, poc, True))
        when = T0 + timedelta(seconds=60)
        self.assertIsNone(meta.on_trade(_MetaTrade("X", when, poc)))
        self.assertIsNone(term.on_trade(ExecutionTrade("X", when, poc)))
        self.assertEqual(_state(meta), _state(term))
        # Disabled engines ignore trades identically.
        meta, term = META.PaperEngine(), PaperEngine()
        self.assertEqual((meta.enabled, term.enabled), (False, False))
        self.assertIsNone(meta.on_trade(_MetaTrade("X", when, poc)))
        self.assertIsNone(term.on_trade(ExecutionTrade("X", when, poc)))


class DocumentedStrictnessDifferenceTests(unittest.TestCase):
    """Terminan refuses inputs Meta silently accepted (fail-closed, documented)."""

    def setUp(self):
        self.meta, self.term = _engines({"notional": "100", "threshold": "0.015",
                                         "stop_pct": "0.005", "fee_rate": "0.0006",
                                         "slippage_bps": "2"})

    def test_d1_out_of_order_trade(self):
        late, early = T0 + timedelta(seconds=30), T0 + timedelta(seconds=10)
        for engine, cls in ((self.meta, _MetaTrade), (self.term, ExecutionTrade)):
            engine.on_trade(cls("X", late, D("100")))
        self.assertIsNone(self.meta.on_trade(_MetaTrade("X", early, D("100"))))
        with self.assertRaises(ValueError):
            self.term.on_trade(ExecutionTrade("X", early, D("100")))

    def test_d2_out_of_order_closed_minute(self):
        later = T0 + timedelta(minutes=1)
        self.meta.on_closed_minute("X", _MetaMinute(later, D("100"), True))
        self.term.on_closed_minute("X", ClosedMinute(later, D("100"), True))
        self.meta.on_closed_minute("X", _MetaMinute(T0, D("100"), True))
        self.assertEqual(self.meta.reference["X"][0], T0)
        with self.assertRaises(ValueError):
            self.term.on_closed_minute("X", ClosedMinute(T0, D("100"), True))

    def test_d3_unaligned_minute_start_never_trades_in_meta(self):
        odd = T0 + timedelta(seconds=30)
        self.meta.on_closed_minute("X", _MetaMinute(odd, D("100"), True))
        for seconds in range(60, 180, 7):
            self.assertIsNone(self.meta.on_trade(_MetaTrade("X", T0 + timedelta(seconds=seconds), D("50"))))
        self.assertEqual(self.meta.positions, {})
        with self.assertRaises(ValueError):
            self.term.on_closed_minute("X", ClosedMinute(odd, D("100"), True))

    def test_d4_nonpositive_poc_never_trades_in_meta(self):
        for poc in (D("0"), D("-1")):
            self.meta.on_closed_minute("X", _MetaMinute(T0, poc, True))
            self.assertIsNone(self.meta.on_trade(_MetaTrade("X", T0 + timedelta(seconds=60), D("1"))))
            self.assertEqual(self.meta.positions, {})
            with self.assertRaises(ValueError):
                self.term.on_closed_minute("X", ClosedMinute(T0, poc, True))

    def test_d5_stop_pct_at_or_above_one(self):
        meta, term = _engines({"notional": "100", "threshold": "0.015", "stop_pct": "1",
                               "fee_rate": "0", "slippage_bps": "0"})
        meta.on_closed_minute("X", _MetaMinute(T0, D("100"), True))
        term.on_closed_minute("X", ClosedMinute(T0, D("100"), True))
        when = T0 + timedelta(seconds=60)
        meta.on_trade(_MetaTrade("X", when, D("90")))
        self.assertEqual(meta.positions["X"].stop, D("0"))
        with self.assertRaises(ValueError):
            term.on_trade(ExecutionTrade("X", when, D("90")))
        self.assertEqual(term.positions, {})

    def test_d6_meta_depends_on_ambient_decimal_context(self):
        def run(meta_context):
            meta, term = _engines({"notional": "100", "threshold": "0.015", "stop_pct": "0.005",
                                   "fee_rate": "0.0006", "slippage_bps": "2"})
            with decimal.localcontext(meta_context):
                meta.on_closed_minute("X", _MetaMinute(T0, D("100"), True))
                term.on_closed_minute("X", ClosedMinute(T0, D("100"), True))
                meta.on_trade(_MetaTrade("X", T0 + timedelta(seconds=60), D("97.13")))
                term.on_trade(ExecutionTrade("X", T0 + timedelta(seconds=60), D("97.13")))
                a = meta.on_trade(_MetaTrade("X", T0 + timedelta(seconds=61), D("100")))
                b = term.on_trade(ExecutionTrade("X", T0 + timedelta(seconds=61), D("100")))
            return _fill(a), _fill(b)
        a, b = run(decimal.Context())
        self.assertEqual(a, b)
        a10, b10 = run(decimal.Context(prec=10))
        self.assertEqual(b10, b)       # Terminan is context independent
        self.assertNotEqual(a10, a)    # Meta silently changes with the caller context


if __name__ == "__main__":
    unittest.main()

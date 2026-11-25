"""Ported Meta CrossingService (meta_analyse@b1a4d6a crossing_service.py).

The first three tests are Meta's tests/test_crossing_service.py vectors, with
the fake sync accepting Terminan's explicit continuity/source keywords. The
remaining tests drive the real Terminan LevelSync with a fake terminal and
compare deletions with Meta's original crossed() rule (owned levels with
min(previous,current) <= price <= max(previous,current)) on seeded walks.
"""
import asyncio
import random
import unittest
from decimal import Decimal as D
from types import SimpleNamespace

from terminan.analytics.crossing_service import CrossingService
from terminan.analytics.level_sync import LevelSync
from terminan.metascalp_levels import PREFIX


def trade(i, price, symbol="BTCUSDT"):
    return SimpleNamespace(symbol=symbol, id=str(i), timestamp_ms=i, price=D(price))


class Sync:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    async def crossed(self, c, s, p, n, *, contiguous, source):
        self.calls.append((c, s, p, n, contiguous, source))
        if self.fail:
            raise RuntimeError("terminal uncertain")
        return 1


class Terminal:
    def __init__(self, prices, foreign=()):
        self.rows = {}
        for i, price in enumerate(prices, start=1):
            self.rows[i] = {"id": i, "price": str(price), "note": PREFIX + f"{i:024x}"}
        for j, price in enumerate(foreign, start=len(self.rows) + 1):
            self.rows[j] = {"id": j, "price": str(price), "note": "user level"}
        self.removed = []

    async def levels(self, connection, ticker):
        return list(self.rows.values())

    async def add_level(self, *args):
        raise AssertionError("crossing never adds levels")

    async def remove_level(self, connection, level_id):
        self.removed.append(level_id)
        del self.rows[level_id]


def run(coro):
    return asyncio.run(coro)


class MetaVectorTests(unittest.TestCase):
    def test_contiguous_execution_calls_terminal_crossing(self):
        async def scenario():
            sync = Sync()
            service = CrossingService(sync, lambda s: 7)
            self.assertEqual(await service.execution(trade(1, "90"), contiguous=True), 0)
            self.assertEqual(await service.execution(trade(2, "110"), contiguous=True), 1)
            self.assertEqual(sync.calls, [(7, "BTCUSDT", D("90"), D("110"), True, "exchange_execution")])
        run(scenario())

    def test_gap_prevents_bridging_prices(self):
        async def scenario():
            sync = Sync()
            service = CrossingService(sync, lambda s: 7)
            await service.execution(trade(1, "90"), contiguous=True)
            service.gap("BTCUSDT")
            await service.execution(trade(2, "110"), contiguous=True)
            self.assertEqual(sync.calls, [])
        run(scenario())

    def test_unverified_execution_clears_anchor(self):
        async def scenario():
            sync = Sync()
            service = CrossingService(sync, lambda s: 7)
            await service.execution(trade(1, "90"), contiguous=True)
            await service.execution(trade(2, "110"), contiguous=False)
            await service.execution(trade(3, "120"), contiguous=True)
            self.assertEqual(sync.calls, [])
        run(scenario())

    def test_unknown_connection_and_terminal_failure_fail_closed(self):
        async def scenario():
            sync = Sync()
            service = CrossingService(sync, lambda s: None)
            await service.execution(trade(1, "90"), contiguous=True)
            self.assertEqual(await service.execution(trade(2, "110"), contiguous=True), 0)
            self.assertEqual(sync.calls, [])
            failing = Sync(fail=True)
            service = CrossingService(failing, lambda s: 7)
            await service.execution(trade(1, "90"), contiguous=True)
            with self.assertRaises(RuntimeError):
                await service.execution(trade(2, "110"), contiguous=True)
            self.assertNotIn("BTCUSDT", service.last)  # next tick re-anchors
            self.assertEqual(await service.execution(trade(3, "111"), contiguous=True), 0)
        run(scenario())


class TerminanLevelSyncIntegrationTests(unittest.TestCase):
    def test_seeded_walks_match_meta_inclusive_crossing_rule(self):
        async def walk(seed):
            rng = random.Random(seed)
            levels = sorted({D(rng.randint(9000, 11000)) / 100 for _ in range(12)})
            foreign = [D(rng.randint(9000, 11000)) / 100 for _ in range(4)]
            terminal = Terminal(levels, foreign)
            service = CrossingService(LevelSync(terminal), lambda s: 7)
            expected_rows = {i: D(r["price"]) for i, r in terminal.rows.items()
                             if r["note"].startswith(PREFIX)}
            expected = []
            previous = None
            price = D(100)
            for step in range(60):
                price = max(D("1"), price + D(rng.randint(-150, 150)) / 100)
                contiguous = rng.random() > 0.1
                if rng.random() < 0.05:
                    service.gap("BTCUSDT")
                    previous = None
                await service.execution(trade(step, price), contiguous=contiguous)
                # Meta original rule, applied independently.
                if not contiguous:
                    previous = None
                    continue
                if previous is not None:
                    low, high = min(previous, price), max(previous, price)
                    hit = sorted(i for i, p in expected_rows.items() if low <= p <= high)
                    expected.extend(hit)
                    for i in hit:
                        del expected_rows[i]
                previous = price
            self.assertEqual(sorted(terminal.removed), sorted(expected), seed)
            self.assertEqual(terminal.removed, expected, seed)
            self.assertTrue(all(r["note"] == "user level" or r["id"] in expected_rows
                                for r in terminal.rows.values()))
            return len(expected)

        removed = sum(run(walk(seed)) for seed in range(200))
        self.assertGreater(removed, 200)


if __name__ == "__main__":
    unittest.main()

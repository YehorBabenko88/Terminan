"""Synthetic-only contract tests for the independent DOM engine."""
import unittest
from terminan.dom import BookEngine, BookStatus, Delta, Level, Snapshot, grouped, viewport, serializable


def b(p, q): return Level("bid", p, q)
def a(p, q): return Level("ask", p, q)


class TestDOM(unittest.TestCase):
    def setUp(self):
        self.e = BookEngine()

    def initial(self):
        self.e.snapshot(Snapshot("one", 10, (b(100, 3), b(99, 2), a(101, 4))))

    def test_delta_before_snapshot(self):
        self.assertFalse(self.e.delta(Delta("one", 1, 0, (b(100, 5),))))
        self.assertEqual(self.e.view.status, BookStatus.AWAITING_SNAPSHOT)

    def test_snapshot_order_and_best(self):
        self.initial()
        v = self.e.view
        self.assertEqual(v.bids, ((100, 3), (99, 2)))
        self.assertEqual(v.asks, ((101, 4),))
        self.assertEqual((v.best_bid, v.best_ask), (100, 101))

    def test_snapshot_replaces_old(self):
        self.initial()
        self.e.snapshot(Snapshot("one", 20, (a(105, 7),)))
        self.assertEqual(self.e.view.bids, ())
        self.assertEqual(self.e.view.asks, ((105, 7),))

    def test_delta_absolute_quantity(self):
        self.initial()
        self.assertTrue(self.e.delta(Delta("one", 11, 10, (b(100, 7),))))
        self.assertEqual(self.e.view.bids[0], (100, 7))

    def test_zero_removes_level(self):
        self.initial()
        self.e.delta(Delta("one", 11, 10, (b(100, 0), a(101, 0))))
        self.assertEqual(self.e.view.best_bid, 99)
        self.assertIsNone(self.e.view.best_ask)

    def test_missing_deletion_idempotent(self):
        self.initial()
        self.e.delta(Delta("one", 11, 10, (a(999, 0),)))
        self.assertEqual(self.e.view.asks, ((101, 4),))

    def test_duplicate_ignored(self):
        self.initial()
        self.e.delta(Delta("one", 11, 10, (b(100, 7),)))
        v = self.e.view
        self.assertFalse(self.e.delta(Delta("one", 11, 10, (b(100, 9),))))
        self.assertEqual(self.e.view, v)

    def test_gap_freezes_view(self):
        self.initial()
        self.assertFalse(self.e.delta(Delta("one", 13, 12, (b(100, 9),))))
        self.assertEqual(self.e.view.status, BookStatus.GAP)
        self.assertEqual(self.e.view.bids[0], (100, 3))
        self.assertFalse(self.e.delta(Delta("one", 11, 10, (b(100, 9),))))

    def test_epoch_change_requires_snapshot(self):
        self.initial()
        self.assertFalse(self.e.delta(Delta("two", 1, 0, (b(100, 9),))))
        self.assertEqual(self.e.view.status, BookStatus.GAP)
        self.e.snapshot(Snapshot("two", 1, (b(98, 8),)))
        self.assertEqual(self.e.view.status, BookStatus.LIVE)

    def test_invalid_batch_atomic(self):
        self.initial()
        previous = self.e.view
        with self.assertRaises(ValueError):
            self.e.delta(Delta("one", 11, 10, (b(100, 8), "invalid")))
        self.assertEqual(self.e.view, previous)

    def test_last_update_wins(self):
        self.initial()
        self.e.delta(Delta("one", 11, 10, (b(100, 2), b(100, 8))))
        self.assertEqual(self.e.view.best_bid, 100)
        self.assertEqual(self.e.view.bids[0][1], 8)

    def test_ordering_is_deterministic(self):
        self.e.snapshot(Snapshot("one", 1, (b(98, 1), b(100, 2), b(99, 3), a(103, 1), a(101, 2), a(102, 3))))
        self.assertEqual([p for p, _ in self.e.view.bids], [100, 99, 98])
        self.assertEqual([p for p, _ in self.e.view.asks], [101, 102, 103])

    def test_crossed_not_repaired(self):
        self.e.snapshot(Snapshot("one", 1, (b(105, 2), a(101, 3))))
        self.assertTrue(self.e.view.crossed)

    def test_grouping_before_viewport(self):
        self.e.snapshot(Snapshot("one", 1, (b(100, 2), b(104, 3), a(100, 4))))
        grouped_view = grouped(self.e.view, 5)
        self.assertEqual(grouped_view["bids"], ((100, 5),))
        self.assertEqual(grouped_view["asks"], ((100, 4),))
        self.assertEqual(viewport(self.e.view, 105, 2, 5), (
            {"price_ticks": 105, "bid_lots": 0, "ask_lots": 0},
            {"price_ticks": 100, "bid_lots": 5, "ask_lots": 4},
        ))

    def test_floor_division_anchor(self):
        self.e.snapshot(Snapshot("one", 1, (b(1, 2),)))
        self.assertEqual(grouped(self.e.view, 5, 2)["bids"], ((-3, 2),))

    def test_reject_invalid_grouping(self):
        with self.assertRaises(ValueError):
            grouped(self.e.view, 0)

    def test_invalid_level(self):
        with self.assertRaises(ValueError):
            b(1, -1)
        with self.assertRaises(ValueError):
            Level("buy", 1, 1)

    def test_connection_statuses(self):
        self.initial()
        self.e.stale()
        self.assertEqual(self.e.view.status, BookStatus.STALE)
        self.e.disconnected()
        self.assertEqual(self.e.view.status, BookStatus.DISCONNECTED)
        self.e.snapshot(Snapshot("two", 1, (a(101, 1),)))
        self.assertEqual(self.e.view.status, BookStatus.LIVE)

    def test_serializable(self):
        self.initial()
        result = serializable(self.e.view, 5)
        self.assertEqual(result["status"], "LIVE")
        self.assertEqual(result["best_bid"], 100)


if __name__ == "__main__":
    unittest.main()

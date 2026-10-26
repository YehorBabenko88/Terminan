"""Pinned offline DOM stress invariants; never represents a live exchange feed."""
import random
import unittest

from terminan.dom import BookEngine, BookStatus, Delta, Level, Snapshot, viewport


class OfflineDomStress(unittest.TestCase):
    def test_seeded_replay_gap_and_epoch_fencing(self):
        rng = random.Random(20261026)
        book = BookEngine()
        self.assertTrue(book.snapshot(Snapshot("synthetic-epoch-1", 10, (
            Level("bid", 99, 5), Level("ask", 101, 7)))))
        for seq in range(11, 2011):
            side = "bid" if rng.randrange(2) else "ask"
            price = rng.randrange(1, 100) if side == "bid" else rng.randrange(102, 202)
            qty = rng.randrange(0, 1000)
            self.assertTrue(book.delta(Delta("synthetic-epoch-1", seq, seq - 1,
                                             (Level(side, price, qty),))))
            view = book.view
            self.assertEqual(view.sequence, seq)
            self.assertFalse(view.crossed)
            self.assertEqual(tuple(sorted(view.bids, reverse=True)), view.bids)
            self.assertEqual(tuple(sorted(view.asks)), view.asks)
            self.assertLessEqual(len(viewport(view, 150, 40, 2)), 40)
        self.assertFalse(book.delta(Delta("synthetic-epoch-1", 2012, 2010, ())))
        self.assertEqual(book.view.status, BookStatus.GAP)
        self.assertFalse(book.snapshot(Snapshot("synthetic-epoch-1", 2010, ())))
        self.assertEqual(book.view.status, BookStatus.GAP)
        self.assertTrue(book.snapshot(Snapshot("synthetic-epoch-2", 1, ())))
        self.assertEqual(book.view.status, BookStatus.LIVE)
        self.assertEqual(book.view.epoch, "synthetic-epoch-2")

    def test_disconnected_cannot_recover_from_duplicate(self):
        book = BookEngine()
        self.assertTrue(book.snapshot(Snapshot("synthetic", 7, (Level("bid", 100, 3),))))
        book.disconnected()
        self.assertFalse(book.snapshot(Snapshot("synthetic", 7, ())))
        self.assertEqual(book.view.status, BookStatus.DISCONNECTED)
        self.assertTrue(book.snapshot(Snapshot("synthetic", 8, ())))
        self.assertEqual(book.view.bids, ())


if __name__ == "__main__":
    unittest.main()

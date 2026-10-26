"""Deterministic, offline-only fault injection for the DOM sequence contract.

These fixtures do not represent exchange connectivity or physical acceptance.
"""
import unittest

from terminan.dom import BookEngine, BookStatus, Delta, Level, Snapshot


class ReliabilityFaultInjection(unittest.TestCase):
    def setUp(self):
        self.book = BookEngine()
        self.assertTrue(self.book.snapshot(Snapshot("synthetic-epoch", 2010, (
            Level("bid", 100, 5), Level("ask", 102, 7)))))

    def test_linked_nonconsecutive_sequence_is_valid(self):
        """The engine uses previous_sequence as the continuity link."""
        self.assertTrue(self.book.delta(Delta("synthetic-epoch", 2012, 2010, ())))
        self.assertEqual(self.book.view.sequence, 2012)
        self.assertEqual(self.book.view.status, BookStatus.LIVE)

    def test_wrong_predecessor_is_gap_without_mutating_levels(self):
        before = (self.book.view.bids, self.book.view.asks)
        self.assertFalse(self.book.delta(Delta("synthetic-epoch", 2012, 2009,
                                               (Level("bid", 100, 999),))))
        self.assertEqual(self.book.view.status, BookStatus.GAP)
        self.assertEqual((self.book.view.bids, self.book.view.asks), before)
        self.assertFalse(self.book.delta(Delta("synthetic-epoch", 2013, 2012, ())))

    def test_duplicate_and_out_of_order_are_ignored(self):
        original = self.book.view
        for seq in (2010, 2009):
            self.assertFalse(self.book.delta(Delta("synthetic-epoch", seq, 2010, ())))
        self.assertEqual(self.book.view, original)

    def test_disconnect_stale_and_recovery_watermark(self):
        self.book.stale()
        self.assertEqual(self.book.view.status, BookStatus.STALE)
        self.assertFalse(self.book.delta(Delta("synthetic-epoch", 2011, 2010, ())))
        self.book.disconnected()
        self.assertEqual(self.book.view.status, BookStatus.DISCONNECTED)
        self.assertFalse(self.book.snapshot(Snapshot("synthetic-epoch", 2010, ())))
        self.assertTrue(self.book.snapshot(Snapshot("synthetic-epoch", 2011, ())))
        self.assertEqual(self.book.view.status, BookStatus.LIVE)

    def test_epoch_mismatch_fences_old_stream(self):
        self.assertFalse(self.book.delta(Delta("other-epoch", 2011, 2010, ())))
        self.assertEqual(self.book.view.status, BookStatus.GAP)
        self.assertTrue(self.book.snapshot(Snapshot("new-epoch", 1, ())))
        self.assertEqual(self.book.view.epoch, "new-epoch")

    def test_invalid_payload_rejected_without_state_change(self):
        original = self.book.view
        with self.assertRaises(ValueError):
            self.book.delta(Delta("synthetic-epoch", 2011, -1, ()))
        with self.assertRaises(ValueError):
            self.book.delta(Delta("synthetic-epoch", 2011, 2010, ("bad-level",)))
        self.assertEqual(self.book.view, original)


if __name__ == "__main__":
    unittest.main()

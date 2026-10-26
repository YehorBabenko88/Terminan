import unittest

from terminan.dom import BookEngine, BookStatus, Delta, Level, Snapshot


class SnapshotRecoveryAuditTests(unittest.TestCase):
    def test_old_or_duplicate_snapshot_cannot_recover_invalidated_book(self):
        for status in (BookStatus.GAP, BookStatus.STALE, BookStatus.DISCONNECTED):
            for sequence in (9, 10):
                with self.subTest(status=status, sequence=sequence):
                    book = BookEngine()
                    book.snapshot(Snapshot('one', 10, (Level('bid', 100, 3),)))
                    if status == BookStatus.GAP:
                        book.delta(Delta('one', 13, 12, ()))
                    elif status == BookStatus.STALE:
                        book.stale()
                    else:
                        book.disconnected()
                    before = book.view
                    self.assertFalse(book.snapshot(Snapshot('one', sequence, (Level('bid', 90, 9),))))
                    self.assertEqual(book.view, before)
                    self.assertTrue(book.snapshot(Snapshot('one', 14, (Level('bid', 101, 4),))))
                    self.assertEqual(book.view.status, BookStatus.LIVE)
                    self.assertEqual(book.view.bids, ((101, 4),))


if __name__ == '__main__':
    unittest.main()

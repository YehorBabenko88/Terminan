import unittest
from terminan.dom import Snapshot, Delta, Level, BookStatus
from terminan.dom_stream import FeedEnvelope, BoundedFeed, FrameGate


def s(symbol, seq, epoch="e"):
    return FeedEnvelope(symbol, Snapshot(epoch, seq, (Level("bid", 100, seq),)))


def d(symbol, seq, prev, epoch="e"):
    return FeedEnvelope(symbol, Delta(epoch, seq, prev, (Level("bid", 100, seq),)))


class StreamTests(unittest.TestCase):
    def test_fifo(self):
        f = BoundedFeed(4)
        self.assertTrue(f.publish(s("BTC", 1)))
        self.assertTrue(f.publish(d("BTC", 2, 1)))
        self.assertEqual(f.drain(), 2)
        self.assertEqual(f.engine("BTC").view.sequence, 2)

    def test_bounded(self):
        f = BoundedFeed(1)
        f.publish(s("BTC", 1))
        self.assertFalse(f.publish(d("BTC", 2, 1)))
        self.assertEqual(f.queued, 0)
        self.assertEqual(f.dropped, 2)
        self.assertEqual(f.engine("BTC").view.status, BookStatus.DISCONNECTED)

    def test_recovery_requires_snapshot(self):
        f = BoundedFeed(1)
        f.publish(s("BTC", 1))
        f.publish(d("BTC", 2, 1))
        f.publish(d("BTC", 3, 2))
        self.assertEqual(f.drain(), 0)
        f.publish(s("BTC", 10, "new"))
        self.assertEqual(f.drain(), 1)
        self.assertEqual(f.engine("BTC").view.status, BookStatus.LIVE)

    def test_two_symbols(self):
        f = BoundedFeed(4)
        f.publish(s("BTC", 1))
        f.publish(s("ETH", 2))
        self.assertEqual(f.drain(), 2)
        self.assertEqual(f.engine("ETH").view.sequence, 2)

    def test_drain_limit(self):
        f = BoundedFeed()
        f.publish(s("BTC", 1))
        f.publish(d("BTC", 2, 1))
        self.assertEqual(f.drain(1), 1)
        self.assertEqual(f.queued, 1)

    def test_invalid_envelope(self):
        with self.assertRaises(ValueError):
            FeedEnvelope("", Snapshot("e", 1, ()))
        with self.assertRaises(ValueError):
            BoundedFeed(0)

    def test_gate_coalesces(self):
        f = BoundedFeed()
        f.publish(s("BTC", 1))
        f.drain()
        view = f.engine("BTC").view
        gate = FrameGate(10)
        self.assertTrue(gate.ready("BTC", view, 0))
        self.assertFalse(gate.ready("BTC", view, 200_000_000))
        f.publish(d("BTC", 2, 1))
        f.drain()
        self.assertFalse(gate.ready("BTC", f.engine("BTC").view, 50_000_000))
        self.assertTrue(gate.ready("BTC", f.engine("BTC").view, 100_000_000))

    def test_gate_status_changes(self):
        f = BoundedFeed()
        f.publish(s("BTC", 1))
        f.drain()
        gate = FrameGate(30)
        self.assertTrue(gate.ready("BTC", f.engine("BTC").view, 0))
        f.engine("BTC").stale()
        self.assertTrue(gate.ready("BTC", f.engine("BTC").view, 40_000_000))


if __name__ == "__main__":
    unittest.main()

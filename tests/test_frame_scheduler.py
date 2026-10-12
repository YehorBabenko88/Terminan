import unittest
from terminan.dom import BookEngine, Snapshot, Level
from terminan.render_model import build_render_model
from terminan.frame_scheduler import LatestFrameMailbox


class FrameSchedulerTests(unittest.TestCase):
    def setUp(self):
        book = BookEngine()
        book.snapshot(Snapshot("epoch", 1, (Level("bid", 100, 1),)))
        self.model = build_render_model(book.view, top_tick=100, row_count=1)

    def test_replaces_pending_and_respects_deadline(self):
        mailbox = LatestFrameMailbox(fps=50)
        mailbox.reset("epoch")
        for _ in range(100):
            self.assertTrue(mailbox.offer(self.model))
        self.assertEqual(mailbox.replacements, 99)
        self.assertEqual(mailbox.take(0).reason, "READY")
        self.assertTrue(mailbox.offer(self.model))
        self.assertEqual(mailbox.take(0.019).reason, "FPS_LIMIT")
        self.assertEqual(mailbox.take(0.020).reason, "READY")

    def test_hidden_keeps_latest_pending(self):
        mailbox = LatestFrameMailbox()
        mailbox.reset("epoch")
        mailbox.offer(self.model)
        self.assertEqual(mailbox.take(0, visible=False).reason, "HIDDEN")
        self.assertEqual(mailbox.take(0).reason, "READY")

    def test_epoch_switch_discards_old_frames(self):
        mailbox = LatestFrameMailbox()
        mailbox.reset("other")
        self.assertFalse(mailbox.offer(self.model))
        self.assertEqual(mailbox.stale_drops, 1)
        mailbox.reset("epoch", surface_generation=1)
        self.assertFalse(mailbox.offer(self.model))

    def test_dispose_prevents_presentation(self):
        mailbox = LatestFrameMailbox()
        mailbox.reset("epoch")
        mailbox.offer(self.model)
        mailbox.dispose()
        self.assertEqual(mailbox.take(0).reason, "DISPOSED")
        self.assertFalse(mailbox.offer(self.model))


if __name__ == "__main__":
    unittest.main()

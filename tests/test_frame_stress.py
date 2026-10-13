import unittest
from dataclasses import replace
from terminan.dom import BookEngine, Snapshot, Level
from terminan.render_model import build_render_model
from terminan.frame_pipeline import DomFramePipeline


def frame(version, *, view=0, style=0, dpi=0, epoch="epoch", generation=0):
    book = BookEngine()
    book.snapshot(Snapshot(epoch, 1, (Level("bid", 100, 5),)))
    model = build_render_model(book.view, top_tick=100, row_count=1,
                               width_dip=8, height_dip=4,
                               view_version=view, style_version=style,
                               dpi_version=dpi, surface_generation=generation)
    return replace(model, key=replace(model.key, book_version=version))


class FrameStressTests(unittest.TestCase):
    def test_ten_thousand_updates_are_coalesced(self):
        p = DomFramePipeline(fps=60)
        p.reset("epoch")
        for i in range(10000):
            self.assertTrue(p.offer(frame(i + 1)))
        self.assertEqual(p.mailbox.replacements, 9999)
        self.assertTrue(p.pump(0).published)
        self.assertEqual(p.snapshot().key.book_version, 10000)
        self.assertEqual(p.renders, 1)
        self.assertIsNone(p.mailbox.pending)

    def test_equal_book_revision_rejects_old_view_and_style(self):
        p = DomFramePipeline()
        p.reset("epoch")
        self.assertTrue(p.offer(frame(5, view=2, style=3)))
        self.assertFalse(p.offer(frame(5, view=1, style=100)))
        self.assertTrue(p.pump(0).published)
        self.assertFalse(p.offer(frame(5, view=2, style=2)))
        self.assertTrue(p.offer(frame(5, view=2, style=4)))
        self.assertTrue(p.pump(1).published)
        self.assertEqual(p.snapshot().key.style_version, 4)

    def test_reset_invalidates_pending_and_published_frames(self):
        p = DomFramePipeline()
        p.reset("epoch")
        p.offer(frame(1))
        p.pump(0)
        p.offer(frame(2))
        p.reset("new", 1)
        self.assertIsNone(p.snapshot())
        self.assertIsNone(p.mailbox.pending)
        self.assertFalse(p.offer(frame(3)))
        self.assertTrue(p.offer(frame(1, epoch="new", generation=1)))
        self.assertTrue(p.pump(0).published)

    def test_hidden_stress_keeps_only_last_frame(self):
        p = DomFramePipeline()
        p.reset("epoch")
        for i in range(1000):
            p.offer(frame(i + 1))
            self.assertEqual(p.pump(i / 1000, visible=False).reason, "HIDDEN")
        self.assertEqual(p.renders, 0)
        self.assertTrue(p.pump(2).published)
        self.assertEqual(p.snapshot().key.book_version, 1000)


if __name__ == "__main__":
    unittest.main()

import unittest
from terminan.dom import BookEngine, Snapshot, Level
from terminan.render_model import build_render_model
from terminan.frame_pipeline import DomFramePipeline


def model(epoch, version, generation=0):
    book = BookEngine()
    book.snapshot(Snapshot(epoch, version, (Level("bid", 100, 2),)))
    return build_render_model(book.view, top_tick=100, row_count=1,
                              width_dip=8, height_dip=4,
                              surface_generation=generation)


class DomFramePipelineTests(unittest.TestCase):
    def test_publish_and_fps_coalescing(self):
        p = DomFramePipeline(fps=50)
        p.reset("a")
        self.assertTrue(p.offer(model("a", 1)))
        self.assertTrue(p.pump(0).published)
        first = p.snapshot()
        self.assertEqual(first.width, 8)
        self.assertTrue(p.offer(model("a", 2)))
        self.assertEqual(p.pump(.01).reason, "FPS_LIMIT")
        self.assertIs(p.snapshot(), first)
        self.assertTrue(p.pump(.02).published)
        self.assertEqual(p.renders, 2)
        self.assertEqual(p.snapshot().key.book_version, 2)

    def test_reset_drops_stale_epoch_and_surface(self):
        p = DomFramePipeline()
        p.reset("a")
        p.offer(model("a", 1))
        p.pump(0)
        p.reset("b", 1)
        self.assertIsNone(p.snapshot())
        self.assertFalse(p.offer(model("a", 2)))
        self.assertFalse(p.offer(model("b", 2, 0)))
        self.assertTrue(p.offer(model("b", 2, 1)))
        self.assertTrue(p.pump(0).published)

    def test_never_regress_book_version(self):
        p = DomFramePipeline()
        p.reset("a")
        p.offer(model("a", 2))
        self.assertFalse(p.offer(model("a", 1)))
        p.pump(0)
        self.assertFalse(p.offer(model("a", 1)))
        self.assertEqual(p.snapshot().key.book_version, 2)

    def test_hidden_does_not_render(self):
        p = DomFramePipeline()
        p.reset("a")
        p.offer(model("a", 1))
        self.assertEqual(p.pump(0, visible=False).reason, "HIDDEN")
        self.assertEqual(p.renders, 0)
        self.assertTrue(p.pump(0).published)

    def test_dispose_drops_frame(self):
        p = DomFramePipeline()
        p.reset("a")
        p.offer(model("a", 1))
        p.pump(0)
        p.dispose()
        self.assertIsNone(p.snapshot())
        self.assertFalse(p.offer(model("a", 2)))
        self.assertEqual(p.pump(1).reason, "DISPOSED")


if __name__ == "__main__":
    unittest.main()

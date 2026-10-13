import unittest
from dataclasses import replace
from terminan.dom import BookEngine, Snapshot, Level
from terminan.render_model import build_render_model
from terminan.frame_pipeline import DomFramePipeline


def make_model(epoch, version, generation):
    book = BookEngine()
    book.snapshot(Snapshot(epoch, 1, (Level("bid", 100, 3),)))
    m = build_render_model(book.view, top_tick=100, row_count=1,
                           width_dip=8, height_dip=4,
                           surface_generation=generation)
    return replace(m, key=replace(m.key, book_version=version))


class PipelineResetRegressionTests(unittest.TestCase):
    def test_reset_allows_lower_revision_for_new_epoch(self):
        p = DomFramePipeline()
        p.reset("old", 0)
        self.assertTrue(p.offer(make_model("old", 100, 0)))
        self.assertTrue(p.pump(0).published)
        p.reset("new", 1)
        self.assertTrue(p.offer(make_model("new", 1, 1)))
        self.assertTrue(p.pump(0).published)
        self.assertEqual(p.snapshot().key.book_version, 1)

    def test_surface_reset_allows_new_book_revision(self):
        p = DomFramePipeline()
        p.reset("same", 0)
        p.offer(make_model("same", 99, 0))
        p.pump(0)
        p.reset("same", 1)
        self.assertTrue(p.offer(make_model("same", 1, 1)))
        self.assertTrue(p.pump(0).published)


if __name__ == "__main__":
    unittest.main()

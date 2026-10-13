import unittest
from terminan.dom import BookEngine, Snapshot, Level
from terminan.render_model import build_render_model
from terminan.frame_scheduler import LatestFrameMailbox


class RenderInputHardeningTests(unittest.TestCase):
    def setUp(self):
        book = BookEngine()
        book.snapshot(Snapshot("epoch", 1, (Level("bid", 100, 2),)))
        self.view = book.view

    def test_non_numeric_hit_tests_return_none(self):
        model = build_render_model(self.view, top_tick=100, row_count=1)
        for bad in (None, "12", True, float("nan"), float("inf"), -1):
            self.assertIsNone(model.hit_test(bad))

    def test_large_finite_dimensions_fail_predictably(self):
        with self.assertRaisesRegex(ValueError, "overflow"):
            build_render_model(self.view, top_tick=100, row_count=1,
                               width_dip=1e308, scale_x=1e308)

    def test_surface_pixel_budget_rejects_large_buffers(self):
        with self.assertRaisesRegex(ValueError, "pixel budget"):
            build_render_model(self.view, top_tick=100, row_count=1,
                               width_dip=8000, height_dip=8000)

    def test_mailbox_invalid_monotonic_time(self):
        mailbox = LatestFrameMailbox()
        mailbox.reset("epoch")
        for bad in (None, "1", True, float("nan"), -1):
            with self.assertRaises(ValueError):
                mailbox.take(bad)


if __name__ == "__main__":
    unittest.main()

import unittest
from dataclasses import replace
from terminan.dom import BookEngine, Snapshot, Level
from terminan.render_model import build_render_model
from terminan.canvas_backend import FrameSwapchain, rasterize


class SwapchainRevisionTests(unittest.TestCase):
    def make_frame(self, book_version, *, view=0, style=0, dpi=0, epoch="a", generation=0):
        book = BookEngine()
        book.snapshot(Snapshot(epoch, 1, (Level("bid", 100, 1),)))
        model = build_render_model(book.view, top_tick=100, row_count=1,
                                   width_dip=4, height_dip=4,
                                   view_version=view, style_version=style,
                                   dpi_version=dpi, surface_generation=generation)
        return rasterize(replace(model, key=replace(model.key, book_version=book_version)))

    def test_stale_frame_does_not_replace_front(self):
        chain = FrameSwapchain()
        chain.reset("a", 0)
        newest = self.make_frame(5, view=2, style=4)
        self.assertTrue(chain.publish(newest))
        for old in (self.make_frame(4, view=999),
                    self.make_frame(5, view=1, style=999),
                    self.make_frame(5, view=2, style=3)):
            self.assertFalse(chain.publish(old))
            self.assertIs(chain.snapshot(), newest)
        self.assertEqual(chain.dropped, 3)

    def test_equal_book_new_style_publishes(self):
        chain = FrameSwapchain()
        chain.reset("a", 0)
        self.assertTrue(chain.publish(self.make_frame(5, style=1)))
        latest = self.make_frame(5, style=2)
        self.assertTrue(chain.publish(latest))
        self.assertIs(chain.snapshot(), latest)

    def test_surface_reset_drops_previous_front(self):
        chain = FrameSwapchain()
        chain.reset("a", 0)
        chain.publish(self.make_frame(5))
        chain.reset("a", 1)
        self.assertIsNone(chain.snapshot())
        self.assertFalse(chain.publish(self.make_frame(6)))
        self.assertTrue(chain.publish(self.make_frame(1, generation=1)))


if __name__ == "__main__":
    unittest.main()

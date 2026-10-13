import unittest
from terminan.dom import BookEngine, Snapshot, Level
from terminan.render_model import build_render_model
from terminan.canvas_backend import rasterize, FrameSwapchain


class CanvasBackendTests(unittest.TestCase):
    def setUp(self):
        engine = BookEngine()
        engine.snapshot(Snapshot("epoch1", 1, (
            Level("bid", 100, 5), Level("ask", 101, 10))))
        self.model = build_render_model(
            engine.view, top_tick=101, row_count=2,
            row_height_dip=2, width_dip=8, height_dip=4)

    def test_raster_is_bounded_immutable_and_distinct(self):
        frame = rasterize(self.model)
        self.assertEqual((frame.width, frame.height), (8, 4))
        self.assertEqual(len(frame.rgba), 128)
        self.assertIsInstance(frame.rgba, bytes)
        self.assertNotEqual(frame.rgba, bytes((15, 20, 29, 255)) * 32)
        self.assertEqual(frame, rasterize(self.model))

    def test_publish_and_reject_stale_surface(self):
        frame = rasterize(self.model)
        chain = FrameSwapchain()
        chain.reset("epoch1", 0)
        self.assertTrue(chain.publish(frame))
        self.assertIs(chain.snapshot(), frame)
        chain.reset("epoch1", 1)
        self.assertIsNone(chain.snapshot())
        self.assertFalse(chain.publish(frame))
        self.assertEqual(chain.dropped, 1)

    def test_dispose_releases_front(self):
        frame = rasterize(self.model)
        chain = FrameSwapchain()
        chain.reset("epoch1", 0)
        chain.publish(frame)
        chain.dispose()
        self.assertIsNone(chain.snapshot())
        self.assertFalse(chain.publish(frame))

    def test_bad_color_rejected(self):
        with self.assertRaises(ValueError):
            rasterize(self.model, bid_color=(1, 2, 3, 256))


if __name__ == "__main__":
    unittest.main()

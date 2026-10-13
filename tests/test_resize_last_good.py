import unittest
from dataclasses import replace
from terminan.dom import BookEngine, Snapshot, Level
from terminan.render_model import build_render_model
from terminan.frame_pipeline import DomFramePipeline


def make_model(epoch, generation, version=1):
    book = BookEngine()
    book.snapshot(Snapshot(epoch, 1, (Level("bid", 100, 3),)))
    m = build_render_model(book.view, top_tick=100, row_count=1,
                           width_dip=8, height_dip=4,
                           surface_generation=generation)
    return replace(m, key=replace(m.key, book_version=version))


class ResizeLastGoodTests(unittest.TestCase):
    def test_nonuniform_dpi_scales_horizontal_bar_and_vertical_row(self):
        from terminan.canvas_backend import rasterize
        book = BookEngine()
        book.snapshot(Snapshot("A", 1, (Level("bid", 100, 3),)))
        m = build_render_model(book.view, top_tick=100, row_count=1,
                               row_height_dip=2, width_dip=4, height_dip=4,
                               scale_x=1.5, scale_y=2.0)
        frame = rasterize(m)
        self.assertEqual((frame.width, frame.height), (6, 8))
        bid = bytes((28, 135, 105, 255))
        background = bytes((15, 20, 29, 255))
        for y in range(8):
            for x in range(6):
                pixel = frame.rgba[(y * 6 + x) * 4:(y * 6 + x + 1) * 4]
                self.assertEqual(pixel, bid if y < 4 and x < 3 else background)

    def test_dpi_175_and_200_clip_bottom_row(self):
        from terminan.canvas_backend import rasterize
        book = BookEngine()
        book.snapshot(Snapshot("A", 1, (Level("bid", 100, 3), Level("bid", 99, 3))))
        bid = bytes((28, 135, 105, 255))
        for scale in (1.75, 2.0):
            with self.subTest(scale=scale):
                m = build_render_model(book.view, top_tick=100, row_count=2,
                                       row_height_dip=2, width_dip=4, height_dip=3,
                                       scale_y=scale)
                frame = rasterize(m)
                self.assertEqual(frame.height, __import__("math").ceil(3 * scale))
                for y in range(frame.height):
                    self.assertEqual(frame.rgba[(y * frame.width) * 4:(y * frame.width + 1) * 4], bid)

    def test_fractional_dpi_adjacent_rows_have_no_pixel_gap(self):
        from terminan.canvas_backend import rasterize
        book = BookEngine()
        book.snapshot(Snapshot("A", 1, (Level("bid", 100, 3), Level("bid", 99, 3))))
        m = build_render_model(book.view, top_tick=100, row_count=2,
                               row_height_dip=1, width_dip=4, height_dip=4,
                               scale_y=1.25)
        frame = rasterize(m)
        bid = bytes((28, 135, 105, 255))
        # The second DIP row crosses the first physical pixel boundary.
        for y in range(2):
            self.assertEqual(frame.rgba[(y * frame.width) * 4:(y * frame.width + 1) * 4], bid)

    def test_fractional_dpi_scales_raster_rows(self):
        from terminan.canvas_backend import rasterize
        book = BookEngine()
        book.snapshot(Snapshot("A", 1, (Level("bid", 100, 3),)))
        m = build_render_model(book.view, top_tick=100, row_count=1,
                               row_height_dip=2, width_dip=4, height_dip=4,
                               scale_y=1.5)
        frame = rasterize(m)
        self.assertEqual(frame.height, 6)
        bid = bytes((28, 135, 105, 255))
        for y in range(3):
            self.assertEqual(frame.rgba[(y * frame.width) * 4:(y * frame.width + 1) * 4], bid)
        self.assertNotEqual(frame.rgba[(3 * frame.width) * 4:(3 * frame.width + 1) * 4], bid)

    def test_resize_retains_last_good_until_new_publish(self):
        p = DomFramePipeline()
        p.reset("A", 0)
        p.offer(make_model("A", 0, 50))
        self.assertTrue(p.pump(0).published)
        old = p.snapshot()
        p.reset("A", 1, retain_front=True)
        self.assertIs(p.snapshot(), old)
        self.assertFalse(p.offer(make_model("A", 0, 60)))
        self.assertIs(p.snapshot(), old)
        self.assertTrue(p.offer(make_model("A", 1, 1)))
        self.assertTrue(p.pump(0).published)
        self.assertIsNot(p.snapshot(), old)
        self.assertEqual(p.snapshot().key.surface_generation, 1)

    def test_instrument_switch_never_retains_old_instrument(self):
        p = DomFramePipeline()
        p.reset("A", 0)
        p.offer(make_model("A", 0))
        p.pump(0)
        p.reset("B", 1, retain_front=True)
        self.assertIsNone(p.snapshot())

    def test_resize_without_retention_clears_front(self):
        p = DomFramePipeline()
        p.reset("A", 0)
        p.offer(make_model("A", 0))
        p.pump(0)
        p.reset("A", 1)
        self.assertIsNone(p.snapshot())


if __name__ == "__main__":
    unittest.main()

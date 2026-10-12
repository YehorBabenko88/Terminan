import unittest
from terminan.dom import BookEngine, Snapshot, Level
from terminan.render_model import build_render_model


class RenderModelTests(unittest.TestCase):
    def setUp(self):
        self.book = BookEngine()
        self.book.snapshot(Snapshot("epoch1", 1, (
            Level("bid", 100, 2), Level("bid", 104, 3),
            Level("ask", 101, 4))))
        self.view = self.book.view

    def test_regular_grid_and_grouping(self):
        model = build_render_model(self.view, top_tick=105, row_count=3,
                                   group_ticks=5, row_height_dip=20)
        self.assertEqual([row.price_ticks for row in model.rows], [105, 100, 95])
        self.assertEqual(model.rows[1].bid_lots, 5)
        self.assertEqual(model.rows[1].ask_lots, 4)
        self.assertEqual(model.hit_test(20), 100)
        self.assertIsNone(model.hit_test(60))
        self.assertEqual(self.book.view, self.view)

    def test_independent_dpi_scales(self):
        model = build_render_model(self.view, top_tick=100, row_count=1,
                                   width_dip=101, height_dip=51,
                                   scale_x=1.25, scale_y=2,
                                   dpi_version=3, style_version=2)
        self.assertEqual((model.pixel_width, model.pixel_height), (127, 102))
        self.assertEqual(model.key.dpi_version, 3)
        self.assertEqual(model.key.style_version, 2)

    def test_rejects_invalid_dimensions_and_budget(self):
        for kwargs in ({"scale_x": 0}, {"width_dip": float("nan")},
                       {"width_dip": 16000, "height_dip": 16000}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                build_render_model(self.view, top_tick=100, row_count=1, **kwargs)

    def test_book_version_is_captured(self):
        model = build_render_model(self.view, top_tick=100, row_count=1)
        self.book.snapshot(Snapshot("epoch2", 1, (Level("bid", 90, 1),)))
        self.assertEqual(model.key.epoch, "epoch1")
        self.assertEqual(model.rows[0].bid_lots, 2)


if __name__ == "__main__":
    unittest.main()

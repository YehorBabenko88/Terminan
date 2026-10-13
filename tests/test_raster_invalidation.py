import unittest
from unittest.mock import patch
from terminan.dom import BookEngine, Snapshot, Level
from terminan.render_model import build_render_model
from terminan.frame_pipeline import DomFramePipeline
from terminan.canvas_backend import rasterize


def model(epoch, generation):
    book = BookEngine()
    book.snapshot(Snapshot(epoch, 1, (Level("bid", 100, 4),)))
    return build_render_model(book.view, top_tick=100, row_count=1,
                              width_dip=8, height_dip=4,
                              surface_generation=generation)


class RasterInvalidationTests(unittest.TestCase):
    def test_older_generation_reset_does_not_invalidate_pending_frame(self):
        pipeline = DomFramePipeline()
        pipeline.reset("old", 2)
        self.assertTrue(pipeline.offer(model("old", 2)))
        original_generation = pipeline.jobs.generation
        original_pending = pipeline.mailbox.pending
        with self.assertRaises(ValueError):
            pipeline.reset("old", 1)
        self.assertEqual(pipeline.jobs.generation, original_generation)
        self.assertIs(pipeline.mailbox.pending, original_pending)
        self.assertEqual(pipeline.swapchain.generation, 2)
        self.assertTrue(pipeline.pump(0).published)

    def test_invalid_reset_does_not_invalidate_render_jobs_or_pending_frame(self):
        pipeline = DomFramePipeline()
        pipeline.reset("old", 0)
        self.assertTrue(pipeline.offer(model("old", 0)))
        original_generation = pipeline.jobs.generation
        original_pending = pipeline.mailbox.pending
        for invalid in (-1, 1.5, True, "1"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    pipeline.reset("new", invalid)
                self.assertEqual(pipeline.jobs.generation, original_generation)
                self.assertIs(pipeline.mailbox.pending, original_pending)
                self.assertEqual(pipeline.swapchain.epoch, "old")
        self.assertTrue(pipeline.pump(0).published)

    def test_newer_frame_published_during_raster_blocks_old_revision(self):
        pipeline = DomFramePipeline()
        pipeline.reset("old", 0)
        pipeline.offer(model("old", 0))
        from dataclasses import replace
        newer = model("old", 0)
        newer = replace(newer, key=replace(newer.key, book_version=2))
        def racing_raster(m):
            result = rasterize(m)
            pipeline.offer(newer)
            with patch("terminan.frame_pipeline.rasterize", side_effect=rasterize):
                self.assertTrue(pipeline.pump(1).published)
            return result
        with patch("terminan.frame_pipeline.rasterize", side_effect=racing_raster):
            outcome = pipeline.pump(0)
        self.assertEqual(outcome.reason, "STALE_AFTER_RASTER")
        self.assertEqual(pipeline.snapshot().key.book_version, 2)

    def test_instrument_switch_and_new_publish_during_old_raster(self):
        pipeline = DomFramePipeline()
        pipeline.reset("old", 0)
        pipeline.offer(model("old", 0))
        def racing_raster(m):
            old_frame = rasterize(m)
            pipeline.reset("new", 0)
            pipeline.offer(model("new", 0))
            with patch("terminan.frame_pipeline.rasterize", side_effect=rasterize):
                self.assertTrue(pipeline.pump(1).published)
            return old_frame
        with patch("terminan.frame_pipeline.rasterize", side_effect=racing_raster):
            result = pipeline.pump(0)
        self.assertEqual(result.reason, "STALE_AFTER_RASTER")
        self.assertEqual(pipeline.snapshot().key.epoch, "new")

    def test_reset_during_raster_drops_old_frame(self):
        pipeline = DomFramePipeline()
        pipeline.reset("old", 0)
        pipeline.offer(model("old", 0))
        def racing_raster(m):
            result = rasterize(m)
            pipeline.reset("new", 1)
            return result
        with patch("terminan.frame_pipeline.rasterize", side_effect=racing_raster):
            result = pipeline.pump(0)
        self.assertEqual(result.reason, "STALE_AFTER_RASTER")
        self.assertIsNone(pipeline.snapshot())

    def test_dispose_during_raster_drops_frame(self):
        pipeline = DomFramePipeline()
        pipeline.reset("old", 0)
        pipeline.offer(model("old", 0))
        def racing_raster(m):
            result = rasterize(m)
            pipeline.dispose()
            return result
        with patch("terminan.frame_pipeline.rasterize", side_effect=racing_raster):
            result = pipeline.pump(0)
        self.assertEqual(result.reason, "STALE_AFTER_RASTER")
        self.assertIsNone(pipeline.snapshot())

    def test_newer_view_revision_published_during_raster_blocks_old_frame(self):
        from dataclasses import replace
        pipeline = DomFramePipeline()
        pipeline.reset("A", 0)
        pipeline.offer(model("A", 0))
        newer = model("A", 0)
        newer = replace(newer, key=replace(newer.key, view_version=1))
        def racing_raster(m):
            stale = rasterize(m)
            self.assertTrue(pipeline.offer(newer))
            with patch("terminan.frame_pipeline.rasterize", side_effect=rasterize):
                self.assertTrue(pipeline.pump(1).published)
            return stale
        with patch("terminan.frame_pipeline.rasterize", side_effect=racing_raster):
            result = pipeline.pump(0)
        self.assertEqual(result.reason, "STALE_AFTER_RASTER")
        self.assertEqual(pipeline.snapshot().key.view_version, 1)

    def test_resize_and_book_update_during_raster_rejects_old_frame(self):
        pipeline = DomFramePipeline()
        pipeline.reset("A", 0)
        pipeline.offer(model("A", 0))
        self.assertTrue(pipeline.pump(0).published)
        pipeline.offer(model("A", 0))
        def racing_raster(m):
            stale = rasterize(m)
            pipeline.reset("A", 1, retain_front=True)
            from dataclasses import replace
            fresh = model("A", 1)
            fresh = replace(fresh, key=replace(fresh.key, book_version=2, view_version=1))
            self.assertTrue(pipeline.offer(fresh))
            with patch("terminan.frame_pipeline.rasterize", side_effect=rasterize):
                self.assertTrue(pipeline.pump(1).published)
            return stale
        with patch("terminan.frame_pipeline.rasterize", side_effect=racing_raster):
            outcome = pipeline.pump(1)
        self.assertEqual(outcome.reason, "STALE_AFTER_RASTER")
        self.assertEqual(pipeline.snapshot().key.surface_generation, 1)
        self.assertEqual(pipeline.snapshot().key.book_version, 2)
        self.assertEqual(pipeline.snapshot().key.view_version, 1)

    def test_dpi_change_during_raster_rejects_old_frame(self):
        pipeline = DomFramePipeline()
        pipeline.reset("A", 0)
        pipeline.offer(model("A", 0))
        self.assertTrue(pipeline.pump(0).published)
        previous = pipeline.snapshot()
        pipeline.offer(model("A", 0))
        def racing_raster(m):
            old_frame = rasterize(m)
            pipeline.reset("A", 1, retain_front=True)
            from dataclasses import replace
            next_model = model("A", 1)
            next_model = replace(next_model, key=replace(next_model.key, dpi_version=1))
            pipeline.offer(next_model)
            with patch("terminan.frame_pipeline.rasterize", side_effect=rasterize):
                self.assertTrue(pipeline.pump(1).published)
            return old_frame
        with patch("terminan.frame_pipeline.rasterize", side_effect=racing_raster):
            result = pipeline.pump(1)
        self.assertEqual(result.reason, "STALE_AFTER_RASTER")
        self.assertEqual(pipeline.snapshot().key.surface_generation, 1)
        self.assertEqual(pipeline.snapshot().key.dpi_version, 1)
        self.assertIsNot(pipeline.snapshot(), previous)

    def test_resize_during_raster_keeps_last_good(self):
        pipeline = DomFramePipeline()
        pipeline.reset("old", 0)
        pipeline.offer(model("old", 0))
        self.assertTrue(pipeline.pump(0).published)
        original = pipeline.snapshot()
        pipeline.offer(model("old", 0))
        def racing_raster(m):
            result = rasterize(m)
            pipeline.reset("old", 1, retain_front=True)
            return result
        with patch("terminan.frame_pipeline.rasterize", side_effect=racing_raster):
            outcome = pipeline.pump(1)
        self.assertEqual(outcome.reason, "STALE_AFTER_RASTER")
        self.assertIs(pipeline.snapshot(), original)


if __name__ == "__main__":
    unittest.main()

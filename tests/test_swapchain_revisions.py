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

    def test_repeated_epoch_switch_discards_previous_front(self):
        chain = FrameSwapchain()
        for index in range(20):
            epoch = "a" if index % 2 == 0 else "b"
            previous_epoch = "b" if epoch == "a" else "a"
            chain.reset(epoch, 0, retain_front=True)
            self.assertIsNone(chain.snapshot())
            self.assertFalse(chain.publish(self.make_frame(999, epoch=previous_epoch)))
            current = self.make_frame(index + 1, epoch=epoch)
            self.assertTrue(chain.publish(current))
            self.assertIs(chain.snapshot(), current)

    def test_switch_epoch_rejects_old_frame_even_with_matching_generation(self):
        chain = FrameSwapchain()
        chain.reset("old", 3)
        previous = self.make_frame(50, epoch="old", generation=3)
        self.assertTrue(chain.publish(previous))
        chain.reset("new", 3, retain_front=True)
        self.assertIsNone(chain.snapshot())
        self.assertFalse(chain.publish(self.make_frame(999, epoch="old", generation=3)))
        current = self.make_frame(1, epoch="new", generation=3)
        self.assertTrue(chain.publish(current))
        self.assertIs(chain.snapshot(), current)
        self.assertFalse(chain.publish(previous))
        self.assertIs(chain.snapshot(), current)

    def test_concurrent_same_epoch_reset_cannot_roll_back_generation(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        for attempt in range(20):
            with self.subTest(attempt=attempt):
                chain = FrameSwapchain()
                chain.reset("a", 0)
                barrier = Barrier(2)
                def reset_to(generation):
                    barrier.wait(timeout=10)
                    try:
                        chain.reset("a", generation)
                    except ValueError:
                        pass  # Older generation must be rejected if newer won.
                with ThreadPoolExecutor(max_workers=2) as pool:
                    futures = [pool.submit(reset_to, n) for n in (1, 2)]
                    for future in futures:
                        future.result(timeout=10)
                self.assertEqual(chain.generation, 2)
                self.assertTrue(chain.publish(self.make_frame(1, generation=2)))
                self.assertFalse(chain.publish(self.make_frame(99, generation=1)))

    def test_same_epoch_generation_rollback_is_rejected_without_mutation(self):
        chain = FrameSwapchain()
        chain.reset("a", 2)
        latest = self.make_frame(1, generation=2)
        self.assertTrue(chain.publish(latest))
        with self.assertRaises(ValueError):
            chain.reset("a", 1, retain_front=True)
        self.assertEqual(chain.generation, 2)
        self.assertIs(chain.snapshot(), latest)
        self.assertFalse(chain.publish(self.make_frame(999, generation=1)))

    def test_new_epoch_can_start_at_generation_zero(self):
        chain = FrameSwapchain()
        chain.reset("a", 5)
        chain.reset("b", 0)
        self.assertEqual(chain.generation, 0)
        self.assertEqual(chain.epoch, "b")

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

    def test_repeated_reset_and_stale_publish_never_restore_old_surface(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        old = self.make_frame(99, epoch="a", generation=0)
        fresh = self.make_frame(1, epoch="a", generation=1)
        for attempt in range(20):
            with self.subTest(attempt=attempt):
                chain = FrameSwapchain()
                chain.reset("a", 0)
                chain.publish(old)
                barrier = Barrier(2)
                def resize():
                    barrier.wait(timeout=10)
                    chain.reset("a", 1, retain_front=True)
                def stale_publish():
                    barrier.wait(timeout=10)
                    for _ in range(20):
                        chain.publish(old)
                with ThreadPoolExecutor(max_workers=2) as pool:
                    futures = [pool.submit(resize), pool.submit(stale_publish)]
                    for future in futures:
                        future.result(timeout=10)
                self.assertEqual(chain.generation, 1)
                self.assertTrue(chain.publish(fresh))
                self.assertFalse(chain.publish(old))
                self.assertIs(chain.snapshot(), fresh)

    def test_repeated_concurrent_publish_and_dispose_never_reopens(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        old = self.make_frame(1)
        newer = self.make_frame(2)
        for attempt in range(20):
            with self.subTest(attempt=attempt):
                chain = FrameSwapchain()
                chain.reset("a", 0)
                barrier = Barrier(3)
                def publish_old():
                    barrier.wait(timeout=10)
                    for _ in range(10):
                        chain.publish(old)
                def publish_new():
                    barrier.wait(timeout=10)
                    for _ in range(10):
                        chain.publish(newer)
                def close():
                    barrier.wait(timeout=10)
                    chain.dispose()
                with ThreadPoolExecutor(max_workers=3) as pool:
                    futures = [pool.submit(fn) for fn in (publish_old, publish_new, close)]
                    for future in futures:
                        future.result(timeout=10)
                self.assertTrue(chain.closed)
                self.assertIsNone(chain.snapshot())
                self.assertFalse(chain.publish(newer))

    def test_concurrent_reset_publish_and_dispose_preserve_closed_tombstone(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        chain = FrameSwapchain()
        chain.reset("a", 0)
        old = self.make_frame(10, epoch="a", generation=0)
        fresh = self.make_frame(1, epoch="b", generation=1)
        barrier = Barrier(3)
        def reset():
            barrier.wait(timeout=10)
            try:
                chain.reset("b", 1)
            except RuntimeError:
                pass  # dispose may win
        def publish():
            barrier.wait(timeout=10)
            chain.publish(old)
            chain.publish(fresh)
        def dispose():
            barrier.wait(timeout=10)
            chain.dispose()
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(fn) for fn in (reset, publish, dispose)]
            for future in futures:
                future.result(timeout=10)
        self.assertTrue(chain.closed)
        self.assertIsNone(chain.snapshot())
        self.assertFalse(chain.publish(fresh))
        with self.assertRaises(RuntimeError):
            chain.reset("b", 2)

    def test_concurrent_publications_keep_newest_revision(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        chain = FrameSwapchain()
        chain.reset("a", 0)
        frames = [self.make_frame(version) for version in range(1, 33)]
        start = Barrier(len(frames))
        def publish(frame):
            start.wait(timeout=10)
            return chain.publish(frame)
        with ThreadPoolExecutor(max_workers=len(frames)) as pool:
            list(pool.map(publish, frames))
        self.assertEqual(chain.snapshot().key.book_version, 32)

    def test_retained_front_cannot_be_overwritten_by_old_generation(self):
        chain = FrameSwapchain()
        chain.reset("a", 0)
        previous = self.make_frame(100, generation=0)
        self.assertTrue(chain.publish(previous))
        chain.reset("a", 1, retain_front=True)
        self.assertIs(chain.snapshot(), previous)
        self.assertFalse(chain.publish(self.make_frame(101, generation=0)))
        self.assertIs(chain.snapshot(), previous)
        fresh = self.make_frame(1, generation=1)
        self.assertTrue(chain.publish(fresh))
        self.assertIs(chain.snapshot(), fresh)
        self.assertFalse(chain.publish(self.make_frame(999, generation=0)))
        self.assertIs(chain.snapshot(), fresh)

    def test_old_instrument_cannot_publish_after_epoch_switch(self):
        chain = FrameSwapchain()
        chain.reset("a", 0)
        self.assertTrue(chain.publish(self.make_frame(10, epoch="a")))
        chain.reset("b", 0, retain_front=True)
        self.assertIsNone(chain.snapshot())
        self.assertFalse(chain.publish(self.make_frame(11, epoch="a")))
        new_frame = self.make_frame(1, epoch="b")
        self.assertTrue(chain.publish(new_frame))
        self.assertIs(chain.snapshot(), new_frame)

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

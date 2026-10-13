import threading
import unittest

from terminan.render_jobs import RenderJobGate


class ConcurrentRenderJobTests(unittest.TestCase):
    def test_close_during_running_action_does_not_block_and_invalidates(self):
        gate = RenderJobGate()
        started = threading.Event()
        release = threading.Event()
        cleaned = []
        results = []
        def work():
            started.set()
            self.assertTrue(release.wait(3))
        job = gate.submit(work, lambda: cleaned.append("once"))
        worker = threading.Thread(target=lambda: results.append(gate.execute(job)))
        worker.start()
        try:
            self.assertTrue(started.wait(3))
            gate.close()
            self.assertTrue(gate.closed)
        finally:
            release.set()
            worker.join(3)
        self.assertFalse(worker.is_alive())
        self.assertEqual(results, [False])
        self.assertEqual(cleaned, ["once"])

    def test_completed_action_cleanup_does_not_hold_gate_lock(self):
        gate = RenderJobGate()
        seen = []
        def cleanup():
            thread = threading.Thread(target=lambda: (gate.dequeue(), seen.append("unblocked")))
            thread.start()
            thread.join(2)
            self.assertFalse(thread.is_alive(), "completed cleanup held gate lock")
        job = gate.submit(lambda: None, cleanup)
        self.assertTrue(gate.execute(job))
        self.assertEqual(seen, ["unblocked"])

    def test_rejected_execution_cleanup_does_not_hold_gate_lock(self):
        gate = RenderJobGate()
        seen = []
        def cleanup():
            thread = threading.Thread(target=lambda: (gate.dequeue(), seen.append("unblocked")))
            thread.start()
            thread.join(2)
            self.assertFalse(thread.is_alive(), "rejected cleanup held gate lock")
        job = gate.submit(lambda: None, cleanup)
        gate.dequeue()
        gate.invalidate()
        self.assertFalse(gate.execute(job))
        self.assertEqual(seen, ["unblocked"])

    def test_replacement_cleanup_does_not_hold_gate_lock(self):
        gate = RenderJobGate()
        seen = []
        def cleanup():
            thread = threading.Thread(target=lambda: (gate.dequeue(), seen.append("unblocked")))
            thread.start()
            thread.join(2)
            self.assertFalse(thread.is_alive(), "replacement cleanup held gate lock")
        gate.submit(lambda: None, cleanup)
        gate.submit(lambda: None)
        self.assertEqual(seen, ["unblocked"])

    def test_rejected_submission_cleanup_does_not_hold_gate_lock(self):
        gate = RenderJobGate()
        gate.close()
        seen = []
        def cleanup():
            thread = threading.Thread(target=lambda: (gate.dequeue(), seen.append("unblocked")))
            thread.start()
            thread.join(2)
            self.assertFalse(thread.is_alive(), "rejected cleanup held gate lock")
        self.assertIsNone(gate.submit(lambda: None, cleanup))
        self.assertEqual(seen, ["unblocked"])

    def test_cleanup_can_wait_for_other_thread_to_access_gate(self):
        gate = RenderJobGate()
        observed = []
        def cleanup():
            def reader():
                gate.dequeue()
                observed.append("reader")
            worker = threading.Thread(target=reader)
            worker.start()
            worker.join(2)
            self.assertFalse(worker.is_alive(), "cleanup ran under gate lock")
        gate.submit(lambda: None, cleanup)
        gate.close()
        self.assertEqual(observed, ["reader"])

    def test_cleanup_can_reenter_gate_on_invalidation(self):
        gate = RenderJobGate()
        observed = []
        gate.submit(lambda: None, lambda: (observed.append("cleanup"), gate.close()))
        gate.invalidate()
        self.assertEqual(observed, ["cleanup"])
        self.assertTrue(gate.closed)
        self.assertIsNone(gate.pending)

    def test_cleanup_exception_during_close_leaves_tombstone(self):
        gate = RenderJobGate()
        def broken_cleanup():
            raise RuntimeError("cleanup failed")
        gate.submit(lambda: None, broken_cleanup)
        with self.assertRaisesRegex(RuntimeError, "cleanup failed"):
            gate.close()
        self.assertTrue(gate.closed)
        self.assertIsNone(gate.submit(lambda: None))

    def test_repeated_close_and_invalidate_release_once(self):
        gate = RenderJobGate()
        cleaned = []
        pending = gate.submit(lambda: self.fail("must not execute"),
                              lambda: cleaned.append("once"))
        gate.invalidate()
        gate.invalidate()
        gate.close()
        gate.close()
        self.assertFalse(gate.execute(pending))
        self.assertEqual(cleaned, ["once"])

    def test_action_exception_still_cleans_once(self):
        gate = RenderJobGate()
        cleaned = []
        def fail():
            raise RuntimeError("raster failure")
        job = gate.submit(fail, lambda: cleaned.append("once"))
        with self.assertRaisesRegex(RuntimeError, "raster failure"):
            gate.execute(job)
        gate.close()
        self.assertFalse(gate.execute(job))
        self.assertEqual(cleaned, ["once"])

    def test_invalidate_during_running_action_rejects_result(self):
        gate = RenderJobGate()
        started = threading.Event()
        release = threading.Event()
        results = []
        cleanup = []
        def work():
            started.set()
            self.assertTrue(release.wait(3))
        job = gate.submit(work, lambda: cleanup.append("released"))
        worker = threading.Thread(target=lambda: results.append(gate.execute(job)))
        worker.start()
        try:
            self.assertTrue(started.wait(3))
            gate.invalidate()
            self.assertEqual(gate.generation, 1)
        finally:
            release.set()
            worker.join(3)
        self.assertFalse(worker.is_alive())
        self.assertEqual(results, [False])
        self.assertEqual(cleanup, ["released"])
        fresh = gate.submit(lambda: results.append("new"))
        self.assertTrue(gate.execute(fresh))
        self.assertEqual(results, [False, "new"])

    def test_concurrent_submissions_replace_and_cleanup_all_pending(self):
        gate = RenderJobGate()
        jobs = []
        lock = threading.Lock()
        cleaned = []
        def submit(i):
            job = gate.submit(lambda: None, lambda: cleaned.append(i))
            with lock:
                jobs.append(job)
        threads = [threading.Thread(target=submit, args=(i,)) for i in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(3)
            self.assertFalse(t.is_alive())
        gate.close()
        self.assertEqual(len(jobs), 30)
        self.assertEqual(len(cleaned), 30)
        self.assertEqual(len(set(cleaned)), 30)


if __name__ == "__main__":
    unittest.main()

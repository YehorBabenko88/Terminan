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

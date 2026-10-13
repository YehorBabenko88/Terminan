import unittest
from terminan.render_jobs import RenderJobGate, JobState


class RenderJobLifecycleTests(unittest.TestCase):
    def test_cancel_pending_blocks_execution_and_cleans_once(self):
        gate = RenderJobGate()
        called = []
        job = gate.submit(lambda: called.append("draw"),
                          lambda: called.append("cleanup"))
        job.cancel()
        job.cancel()
        self.assertFalse(gate.execute(gate.dequeue()))
        self.assertEqual(called, ["cleanup"])
        self.assertEqual(job.state, JobState.CANCELLED)

    def test_replacement_cleans_old_job_once(self):
        gate = RenderJobGate()
        events = []
        old = gate.submit(lambda: events.append("old"),
                          lambda: events.append("old-clean"))
        gate.submit(lambda: events.append("new"))
        self.assertTrue(old.cleaned)
        self.assertEqual(gate.replacements, 1)
        self.assertTrue(gate.execute(gate.dequeue()))
        self.assertEqual(events, ["old-clean", "new"])

    def test_close_tombstone_prevents_re_registration(self):
        gate = RenderJobGate()
        called = []
        job = gate.submit(lambda: called.append("old"))
        gate.close()
        self.assertFalse(gate.execute(job))
        self.assertIsNone(gate.submit(lambda: called.append("late")))
        self.assertEqual(called, [])

    def test_invalidate_blocks_dequeued_stale_job(self):
        gate = RenderJobGate()
        events = []
        old = gate.submit(lambda: events.append("old"))
        self.assertIs(gate.dequeue(), old)
        gate.invalidate()
        self.assertFalse(gate.execute(old))
        self.assertEqual(events, [])

    def test_close_during_action_does_not_claim_presentation(self):
        gate = RenderJobGate()
        events = []
        job = gate.submit(lambda: (events.append("started"), gate.close()),
                          lambda: events.append("cleanup"))
        self.assertFalse(gate.execute(gate.dequeue()))
        self.assertEqual(events, ["started", "cleanup"])
        self.assertTrue(job.cleaned)
        self.assertEqual(job.state, JobState.FINISHED)

    def test_rejected_late_submission_releases_resources(self):
        gate = RenderJobGate()
        events = []
        gate.close()
        self.assertIsNone(gate.submit(lambda: events.append("run"),
                                      lambda: events.append("cleanup")))
        self.assertEqual(events, ["cleanup"])

    def test_cleanup_even_if_action_raises(self):
        gate = RenderJobGate()
        events = []
        def bad():
            raise RuntimeError("draw failed")
        job = gate.submit(bad, lambda: events.append("cleanup"))
        with self.assertRaises(RuntimeError):
            gate.execute(gate.dequeue())
        self.assertEqual(events, ["cleanup"])
        self.assertEqual(job.state, JobState.FINISHED)


if __name__ == "__main__":
    unittest.main()

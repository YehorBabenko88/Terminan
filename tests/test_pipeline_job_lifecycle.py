import unittest
from terminan.frame_pipeline import DomFramePipeline


class PipelineJobLifecycleTests(unittest.TestCase):
    def test_reset_cancels_pending_job_and_cleans_once(self):
        pipeline = DomFramePipeline()
        pipeline.reset("first", 0)
        calls = []
        job = pipeline.jobs.submit(lambda: calls.append("executed"),
                                   lambda: calls.append("cleanup"))
        pipeline.reset("second", 1)
        self.assertFalse(pipeline.jobs.execute(job))
        self.assertEqual(calls, ["cleanup"])
        self.assertIsNone(pipeline.jobs.pending)

    def test_dispose_prevents_late_job_and_releases_lease(self):
        pipeline = DomFramePipeline()
        pipeline.reset("first", 0)
        calls = []
        job = pipeline.jobs.submit(lambda: calls.append("executed"),
                                   lambda: calls.append("cleanup"))
        pipeline.dispose()
        self.assertFalse(pipeline.jobs.execute(job))
        self.assertIsNone(pipeline.jobs.submit(lambda: calls.append("late")))
        self.assertEqual(calls, ["cleanup"])

    def test_reset_allows_new_job_after_invalidation(self):
        pipeline = DomFramePipeline()
        pipeline.reset("old", 0)
        old = pipeline.jobs.submit(lambda: None)
        pipeline.reset("new", 1)
        calls = []
        fresh = pipeline.jobs.submit(lambda: calls.append("fresh"))
        self.assertFalse(pipeline.jobs.execute(old))
        self.assertTrue(pipeline.jobs.execute(fresh))
        self.assertEqual(calls, ["fresh"])


if __name__ == "__main__":
    unittest.main()
